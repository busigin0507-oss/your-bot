"""
ТЕЛЕГРАМ БОТ ДЛЯ VERCEL SERVERLESS
Версия 3.0 - оптимизирована для Vercel
"""

from flask import Flask, request, jsonify
import os
import logging
import re
import random
import requests
import yt_dlp
import tempfile
from urllib.parse import urlparse

# =========================================================================
# НАСТРОЙКА ПРИЛОЖЕНИЯ
# =========================================================================

app = Flask(__name__)

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Токен бота из переменных окружения Vercel
BOT_TOKEN = os.getenv('BOT_TOKEN', '8273781946:AAGuV4znNtNEHgCeDhRrCDQyPJKynzca2EQ')
TELEGRAM_API = f'https://api.telegram.org/bot{BOT_TOKEN}'

# =========================================================================
# ФУНКЦИИ ДЛЯ СКАЧИВАНИЯ (встроены в один файл для Vercel)
# =========================================================================

def extract_youtube_id(url):
    """Извлечение ID видео из YouTube ссылки"""
    patterns = [
        r'youtu\.be/([^&\n?#]+)',
        r'youtube\.com/watch\?.*v=([^&\n?#]+)',
        r'youtube\.com/embed/([^&\n?#]+)',
        r'youtube\.com/shorts/([^&\n?#]+)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url, re.IGNORECASE)
        if match:
            video_id = match.group(1).split('?')[0].split('&')[0]
            return video_id
    
    return None

def download_youtube_video(url, quality='720p'):
    """Скачивание видео с YouTube (упрощенная версия для Vercel)"""
    try:
        video_id = extract_youtube_id(url)
        if not video_id:
            return {'success': False, 'error': 'Неверная ссылка YouTube', 'type': 'youtube'}
        
        logger.info(f"Обработка YouTube: {video_id}")
        
        # Упрощенные настройки для Vercel
        ydl_opts = {
            'format': 'best[height<=720]',
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,
            'max_filesize': 50 * 1024 * 1024,  # 50MB максимум для Vercel
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            if not info:
                return {'success': False, 'error': 'Не удалось получить информацию', 'type': 'youtube'}
            
            title = info.get('title', 'YouTube Video')
            duration = info.get('duration', 0)
            
            # Проверка длительности
            if duration > 300:  # 5 минут максимум для Vercel
                return {
                    'success': False,
                    'error': 'Видео слишком длинное (>5 мин) для Vercel',
                    'type': 'youtube'
                }
            
            # Получаем лучшую доступную ссылку
            formats = info.get('formats', [{}])
            best_format = formats[-1]  # Последний формат обычно лучший
            
            video_url = best_format.get('url')
            if not video_url:
                # Пробуем получить URL из info
                video_url = info.get('url')
            
            if video_url:
                return {
                    'success': True,
                    'url': video_url,
                    'title': title,
                    'video_id': video_id,
                    'duration': duration,
                    'quality': quality,
                    'type': 'youtube'
                }
            
            return {'success': False, 'error': 'Не удалось получить ссылку', 'type': 'youtube'}
    
    except Exception as e:
        logger.error(f"YouTube error: {e}")
        return {'success': False, 'error': str(e), 'type': 'youtube'}

def download_pinterest_media(url):
    """Скачивание медиа с Pinterest (упрощенная версия)"""
    try:
        logger.info(f"Обработка Pinterest: {url}")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            return {'success': False, 'error': f'Ошибка {response.status_code}', 'type': 'pinterest'}
        
        html = response.text
        
        # Простой поиск медиа
        patterns = [
            r'"url":"(https://i\.pinimg\.com/[^"]+)"',
            r'src="(https://i\.pinimg\.com/[^"]+)"',
            r'content="(https://i\.pinimg\.com/[^"]+)"'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, html)
            if match:
                media_url = match.group(1).replace('\\/', '/')
                return {
                    'success': True,
                    'url': media_url,
                    'title': 'Pinterest Media',
                    'type': 'image',
                    'source': 'pinterest'
                }
        
        return {'success': False, 'error': 'Медиа не найдено', 'type': 'pinterest'}
    
    except Exception as e:
        logger.error(f"Pinterest error: {e}")
        return {'success': False, 'error': str(e), 'type': 'pinterest'}

# =========================================================================
# TELEGRAM API ФУНКЦИИ
# =========================================================================

def call_telegram_api(method, data):
    """Вызов API Telegram"""
    url = f'{TELEGRAM_API}/{method}'
    try:
        response = requests.post(url, json=data, timeout=10)
        return response.json()
    except Exception as e:
        logger.error(f"Telegram API Error: {e}")
        return {'ok': False}

def send_message(chat_id, text, parse_mode='HTML'):
    """Отправка сообщения"""
    return call_telegram_api('sendMessage', {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': parse_mode,
        'disable_web_page_preview': True
    })

def send_video(chat_id, video_url, caption=''):
    """Отправка видео"""
    return call_telegram_api('sendVideo', {
        'chat_id': chat_id,
        'video': video_url,
        'caption': caption[:1024],
        'supports_streaming': True
    })

def send_photo(chat_id, photo_url, caption=''):
    """Отправка фото"""
    return call_telegram_api('sendPhoto', {
        'chat_id': chat_id,
        'photo': photo_url,
        'caption': caption[:1024]
    })

# =========================================================================
# API ENDPOINTS ДЛЯ VERCEL
# =========================================================================

@app.route('/', methods=['GET'])
def home():
    """Главная страница API"""
    return jsonify({
        'status': 'active',
        'service': 'Telegram Downloader Bot',
        'version': '3.0',
        'endpoints': {
            'GET /': 'Эта страница',
            'POST /': 'Telegram webhook',
            'GET /health': 'Проверка работы'
        }
    })

@app.route('/health', methods=['GET'])
def health_check():
    """Проверка работоспособности"""
    return jsonify({
        'status': 'healthy',
        'bot': 'ready' if BOT_TOKEN else 'no_token',
        'environment': os.getenv('VERCEL_ENV', 'development')
    })

# =========================================================================
# ОБРАБОТЧИК WEBHOOK ОТ TELEGRAM
# =========================================================================

@app.route('/', methods=['POST'])
def handle_webhook():
    """Основной обработчик вебхука"""
    try:
        update = request.json
        
        if 'message' in update:
            message = update['message']
            chat_id = message['chat']['id']
            text = message.get('text', '').strip()
            
            logger.info(f"Message from {chat_id}: {text}")
            
            # Команда /start
            if text == '/start':
                welcome = """
<b>🤖 YouTube & Pinterest Downloader</b>

Отправьте мне ссылку на:
• YouTube (youtube.com, youtu.be)
• Pinterest (pinterest.com)

Бот работает на Vercel Serverless
                """
                send_message(chat_id, welcome)
            
            # YouTube ссылки
            elif 'youtube.com' in text or 'youtu.be' in text:
                process_youtube(chat_id, text)
            
            # Pinterest ссылки
            elif 'pinterest.com' in text:
                process_pinterest(chat_id, text)
            
            # Любой другой текст
            elif text:
                send_message(chat_id, f"📥 Отправьте ссылку на YouTube или Pinterest")
        
        return jsonify({'status': 'ok'})
    
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

def process_youtube(chat_id, url):
    """Обработка YouTube"""
    msg = send_message(chat_id, f"🎬 Обрабатываю YouTube ссылку...\n{url}")
    
    result = download_youtube_video(url)
    
    if result['success']:
        edit_message(chat_id, msg['result']['message_id'], 
                    f"✅ <b>Найдено:</b> {result['title']}\n"
                    f"⏱️ Длительность: {result['duration']}с\n"
                    f"📤 Отправляю...")
        
        # Пытаемся отправить видео
        video_response = send_video(chat_id, result['url'], result['title'])
        
        if not video_response.get('ok'):
            send_message(chat_id, 
                        f"⚠️ <b>Ссылка для скачивания:</b>\n"
                        f"<code>{result['url']}</code>")
    else:
        edit_message(chat_id, msg['result']['message_id'],
                    f"❌ <b>Ошибка:</b> {result['error']}")

def process_pinterest(chat_id, url):
    """Обработка Pinterest"""
    msg = send_message(chat_id, f"📌 Обрабатываю Pinterest...\n{url}")
    
    result = download_pinterest_media(url)
    
    if result['success']:
        edit_message(chat_id, msg['result']['message_id'], "✅ Медиа найдено! Отправляю...")
        
        if result['type'] == 'image':
            send_photo(chat_id, result['url'], result['title'])
        else:
            send_video(chat_id, result['url'], result['title'])
    else:
        edit_message(chat_id, msg['result']['message_id'],
                    f"❌ <b>Ошибка:</b> {result['error']}")

def edit_message(chat_id, message_id, text):
    """Редактирование сообщения"""
    return call_telegram_api('editMessageText', {
        'chat_id': chat_id,
        'message_id': message_id,
        'text': text,
        'parse_mode': 'HTML'
    })

# =========================================================================
# ВАЖНО: НЕТ app.run()! Vercel сам запускает приложение
# =========================================================================
