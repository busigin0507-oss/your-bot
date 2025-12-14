"""
TELEGRAM BOT FOR VERCEL - WORKING VERSION
Токен встроен в код: 8273781946:AAFsvhsMR8WtS4SzQEd22ofCx1X0kV7f7ZA
"""

from flask import Flask, request, jsonify
import requests
import re
import logging

# =========================================================================
# КОНФИГУРАЦИЯ
# =========================================================================

app = Flask(__name__)

# ВАШ ТОКЕН В КОДЕ
BOT_TOKEN = "8273781946:AAFsvhsMR8WtS4SzQEd22ofCx1X0kV7f7ZA"
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

# Логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# =========================================================================
# ПРОСТЫЕ ФУНКЦИИ ДЛЯ VERCEL
# =========================================================================

def get_youtube_direct_link(url):
    """Получаем прямую ссылку на YouTube видео через yt-dlp"""
    try:
        import yt_dlp
        
        ydl_opts = {
            'format': 'best[filesize<50M]',  # До 50MB для Vercel
            'quiet': True,
            'no_warnings': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            if 'url' in info:
                return {
                    'success': True,
                    'url': info['url'],
                    'title': info.get('title', 'YouTube Video'),
                    'duration': info.get('duration', 0)
                }
            
            # Ищем в форматах
            formats = info.get('formats', [])
            if formats:
                return {
                    'success': True,
                    'url': formats[-1]['url'],
                    'title': info.get('title', 'YouTube Video'),
                    'duration': info.get('duration', 0)
                }
                
    except Exception as e:
        logger.error(f"YouTube error: {e}")
    
    return {'success': False, 'error': 'Не удалось получить видео'}

def get_pinterest_media(url):
    """Получаем медиа с Pinterest"""
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=5)
        
        # Ищем изображение
        html = response.text
        img_match = re.search(r'src="(https://i\.pinimg\.com/[^"]+)"', html)
        
        if img_match:
            return {
                'success': True,
                'url': img_match.group(1),
                'title': 'Pinterest Image',
                'type': 'image'
            }
    
    except Exception as e:
        logger.error(f"Pinterest error: {e}")
    
    return {'success': False, 'error': 'Не удалось найти изображение'}

# =========================================================================
# TELEGRAM ФУНКЦИИ
# =========================================================================

def telegram_api(method, data):
    """Отправка запроса к Telegram API"""
    try:
        url = f"{TELEGRAM_API}/{method}"
        resp = requests.post(url, json=data, timeout=10)
        return resp.json()
    except:
        return {'ok': False}

def send_message(chat_id, text):
    """Отправка сообщения"""
    return telegram_api('sendMessage', {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': 'HTML',
        'disable_web_page_preview': True
    })

def send_video(chat_id, video_url, caption=""):
    """Отправка видео"""
    return telegram_api('sendVideo', {
        'chat_id': chat_id,
        'video': video_url,
        'caption': caption[:200],
        'supports_streaming': True
    })

def send_photo(chat_id, photo_url, caption=""):
    """Отправка фото"""
    return telegram_api('sendPhoto', {
        'chat_id': chat_id,
        'photo': photo_url,
        'caption': caption[:200]
    })

# =========================================================================
# API ENDPOINTS ДЛЯ VERCEL
# =========================================================================

@app.route('/', methods=['GET'])
def home():
    """Главная страница API"""
    return jsonify({
        'status': 'active',
        'bot': 'Telegram Downloader',
        'bot_username': '@your_bot_username',  # Замените на username вашего бота
        'endpoints': {
            'GET /': 'Эта страница',
            'POST /': 'Telegram webhook',
            'GET /health': 'Проверка работы'
        }
    })

@app.route('/health', methods=['GET'])
def health():
    """Проверка здоровья"""
    return jsonify({
        'status': 'ok',
        'bot_token_set': len(BOT_TOKEN) > 20,
        'service': 'running'
    })

# =========================================================================
# ОБРАБОТЧИК TELEGRAM WEBHOOK
# =========================================================================

@app.route('/', methods=['POST'])
def webhook():
    """Обработчик вебхука от Telegram"""
    try:
        data = request.json
        
        if 'message' in data:
            message = data['message']
            chat_id = message['chat']['id']
            text = message.get('text', '').strip()
            
            logger.info(f"Message: {chat_id} - {text}")
            
            # Команда /start
            if text == '/start':
                welcome = """
<b>🎬 YouTube & Pinterest Downloader</b>

Привет! Я могу скачать для вас:
• <b>Видео с YouTube</b> (до 5 минут)
• <b>Изображения с Pinterest</b>

Просто отправьте мне ссылку!

Примеры:
https://youtu.be/dQw4w9WgXcQ
https://pinterest.com/pin/123456/

<b>Бот работает на Vercel Serverless</b>
                """
                send_message(chat_id, welcome)
                return jsonify({'status': 'ok'})
            
            # YouTube
            elif 'youtube.com' in text or 'youtu.be' in text:
                send_message(chat_id, "🎬 <b>YouTube ссылка получена!</b>\nОбрабатываю...")
                
                result = get_youtube_direct_link(text)
                
                if result['success']:
                    send_message(chat_id, f"✅ <b>Найдено:</b> {result['title']}")
                    
                    # Пытаемся отправить видео
                    video_resp = send_video(chat_id, result['url'], result['title'])
                    
                    if not video_resp.get('ok'):
                        send_message(chat_id, f"📥 <b>Прямая ссылка:</b>\n<code>{result['url']}</code>")
                else:
                    send_message(chat_id, f"❌ <b>Ошибка:</b> {result['error']}")
            
            # Pinterest
            elif 'pinterest.com' in text or 'pin.it' in text:
                send_message(chat_id, "📌 <b>Pinterest ссылка получена!</b>\nИщу изображение...")
                
                result = get_pinterest_media(text)
                
                if result['success']:
                    send_photo(chat_id, result['url'], result['title'])
                    send_message(chat_id, "✅ <b>Изображение отправлено!</b>")
                else:
                    send_message(chat_id, f"❌ <b>Ошибка:</b> {result['error']}")
            
            # Любой другой текст
            elif text:
                send_message(chat_id, "📥 Отправьте мне ссылку на YouTube или Pinterest")
        
        return jsonify({'status': 'ok'})
    
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

# =========================================================================
# ВАЖНО: НИКАКОГО app.run()!
# =========================================================================
