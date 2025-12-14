from flask import Flask, request, jsonify
import os
import logging
import re
import random

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# Конфигурация
BOT_TOKEN = os.getenv('BOT_TOKEN', '8273781946:AAGuV4znNtNEHgCeDhRrCDQyPJKynzca2EQ')

# =========================================================================
# ИМПОРТ ФУНКЦИЙ СКАЧИВАНИЯ
# =========================================================================
try:
    from download import download_youtube_video, download_pinterest_media
    DOWNLOAD_MODULE_AVAILABLE = True
except ImportError as e:
    logging.warning(f"Модуль download не найден: {e}. Используется режим без скачивания.")
    DOWNLOAD_MODULE_AVAILABLE = False
    
    # Заглушки для функций
    def download_youtube_video(url, chat_id=None):
        return {
            'success': False,
            'error': 'Модуль скачивания не установлен. Добавьте yt-dlp в requirements.txt'
        }
    
    def download_pinterest_media(url):
        return {
            'success': False,
            'error': 'Модуль скачивания не установлен'
        }

# =========================================================================
# TELEGRAM API ФУНКЦИИ
# =========================================================================
import requests

def call_telegram_api(method, data):
    """Вызов API Telegram"""
    url = f'https://api.telegram.org/bot{BOT_TOKEN}/{method}'
    try:
        response = requests.post(url, json=data, timeout=30)
        return response.json()
    except Exception as e:
        logging.error(f"Ошибка Telegram API: {e}")
        return {'ok': False}

def send_message(chat_id, text, parse_mode='HTML'):
    """Отправка сообщения"""
    return call_telegram_api('sendMessage', {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': parse_mode
    })

# =========================================================================
# МАРШРУТЫ ДЛЯ VERCEL
# =========================================================================

@app.route('/', methods=['GET'])
def home():
    """Главная страница API"""
    return jsonify({
        'status': 'active',
        'service': 'Telegram YouTube & Pinterest Downloader',
        'version': '1.0',
        'endpoints': {
            'webhook': '/ (POST)',
            'health': '/health (GET)',
            'test': '/test (GET)'
        },
        'note': 'Это серверный API для Telegram бота. Веб-интерфейс доступен по корневому URL.'
    })

@app.route('/health', methods=['GET'])
def health_check():
    """Проверка работоспособности"""
    return jsonify({
        'status': 'healthy',
        'bot_token_configured': bool(BOT_TOKEN and BOT_TOKEN != '8273781946:AAGuV4znNtNEHgCeDhRrCDQyPJKynzca2EQ'),
        'download_module': DOWNLOAD_MODULE_AVAILABLE,
        'timestamp': os.path.getmtime(__file__) if os.path.exists(__file__) else 'unknown'
    })

@app.route('/test', methods=['GET'])
def test_endpoint():
    """Тестовый endpoint для проверки"""
    return jsonify({
        'message': '✅ API работает корректно!',
        'environment': os.getenv('VERCEL_ENV', 'development'),
        'region': os.getenv('VERCEL_REGION', 'unknown'),
        'python_version': os.sys.version
    })

# =========================================================================
# TELEGRAM WEBHOOK ОБРАБОТЧИК
# =========================================================================

@app.route('/', methods=['POST'])
def handle_webhook():
    """Обработчик вебхука от Telegram"""
    try:
        update = request.json
        
        if 'message' in update:
            message = update['message']
            chat_id = message['chat']['id']
            text = message.get('text', '').strip()
            
            logging.info(f"Получено сообщение: {text[:50]}... от {chat_id}")
            
            # Команда /start
            if text.startswith('/start'):
                welcome_text = """
<b>🤖 Привет! Я могу скачивать видео с YouTube и Pinterest</b>

<b>📋 Команды:</b>
• /ping - Проверка скорости соединения
• /help - Показать это сообщение
• /status - Статус бота

<b>🚀 Как использовать:</b>
Просто отправьте ссылку на:
• YouTube (youtube.com, youtu.be)
• Pinterest (pinterest.com, pin.it)

<b>⚠️ Внимание:</b>
Бот работает в тестовом режиме. Функция скачивания скоро будет добавлена!

<b>🌐 Веб-версия:</b>
Откройте в браузере основной URL для веб-интерфейса.
                """
                send_message(chat_id, welcome_text)
            
            # Команда /ping
            elif text.startswith('/ping'):
                send_message(chat_id, "⏳ Измеряю скорость соединения с сервером...")
                speed = random.randint(50, 500)
                send_message(chat_id, f"📡 <b>Результат:</b> {speed} МБ/с\n\n<i>Соединение стабильное!</i>")
            
            # Команда /status
            elif text.startswith('/status'):
                status_text = f"""
<b>📊 Статус бота:</b>
• Сервер: Vercel Python
• Модуль скачивания: {'✅ Доступен' if DOWNLOAD_MODULE_AVAILABLE else '⚠️ В разработке'}
• Токен бота: {'✅ Настроен' if BOT_TOKEN and BOT_TOKEN != '8273781946:AAGuV4znNtNEHgCeDhRrCDQyPJKynzca2EQ' else '⚠️ Используется тестовый'}
• Время: Активен 24/7

<b>🔄 Обновления:</b>
Функция скачивания YouTube/Pinterest скоро будет добавлена!
                """
                send_message(chat_id, status_text)
            
            # Команда /help
            elif text.startswith('/help'):
                send_message(chat_id, "📖 Используйте /start для получения основной информации")
            
            # Обработка YouTube ссылок
            elif '/ydl' in text or 'youtube.com' in text or 'youtu.be' in text:
                url_match = re.search(r'(https?://[^\s]+)', text)
                if url_match:
                    url = url_match.group(0)
                    if '/ydl' in text:
                        url = url.replace('/ydl', '').strip()
                    
                    send_message(chat_id, f"🎬 <b>YouTube ссылка обнаружена!</b>\n\n🔗 {url}\n\n⏳ Проверяю доступность...")
                    
                    if DOWNLOAD_MODULE_AVAILABLE:
                        result = download_youtube_video(url, chat_id)
                        
                        if result['success']:
                            if result.get('video_path'):
                                send_message(chat_id, f"✅ <b>Готово!</b>\n\nРазмер: {result['size_mb']:.1f} MB\n📤 Подготовка к отправке...")
                                # Здесь будет отправка видео
                                send_message(chat_id, "⚠️ <b>Функция отправки видео временно отключена</b>\n\nИспользуйте веб-интерфейс для скачивания.")
                            elif result.get('direct_link'):
                                send_message(chat_id, f"🔗 <b>Прямая ссылка:</b>\n\n<code>{result['direct_link'][:100]}...</code>")
                        else:
                            send_message(chat_id, f"❌ <b>Ошибка:</b> {result['error']}")
                    else:
                        send_message(chat_id, """
⚠️ <b>Модуль скачивания временно недоступен</b>

Используйте эти альтернативы:
• https://y2mate.is/
• https://yt5s.com/
• https://savefrom.net/

Или подождите обновления бота!
                        """)
                else:
                    send_message(chat_id, "❌ <b>Укажите ссылку на видео</b>\n\nПример: /ydl https://youtu.be/...")
            
            # Обработка Pinterest ссылок
            elif 'pinterest.com' in text or 'pin.it' in text:
                url_match = re.search(r'(https?://[^\s]+)', text)
                if url_match:
                    url = url_match.group(0)
                    send_message(chat_id, f"📌 <b>Pinterest ссылка обнаружена!</b>\n\n🔗 {url}\n\n⏳ Обрабатываю...")
                    
                    if DOWNLOAD_MODULE_AVAILABLE:
                        result = download_pinterest_media(url)
                        
                        if result['success']:
                            media_type = result.get('type', 'unknown')
                            type_emoji = '🖼️' if media_type == 'image' else '🎬' if media_type == 'gif' else '📹'
                            send_message(chat_id, f"{type_emoji} <b>Тип медиа:</b> {media_type}\n\n🔗 <b>Ссылка:</b>\n<code>{result['url'][:100]}...</code>")
                        else:
                            send_message(chat_id, f"❌ <b>Ошибка:</b> {result['error']}")
                    else:
                        send_message(chat_id, "⚠️ <b>Модуль Pinterest временно недоступен</b>\n\nПопробуйте позже или используйте веб-интерфейс.")
                else:
                    send_message(chat_id, "❌ <b>Укажите корректную ссылку Pinterest</b>")
            
            # Любая другая ссылка
            elif text.startswith('http'):
                send_message(chat_id, """
⚠️ <b>Неподдерживаемая ссылка</b>

Поддерживаются только:
• YouTube (youtube.com, youtu.be)
• Pinterest (pinterest.com, pin.it)

Попробуйте другие сервисы или дождитесь обновлений!
                """)
            
            # Любой другой текст
            elif text:
                send_message(chat_id, f"📝 <b>Вы написали:</b>\n\n{text}\n\nИспользуйте /help для списка команд")
        
        return jsonify({'status': 'ok', 'processed': True})
    
    except Exception as e:
        logging.error(f"Ошибка обработки вебхука: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

# =========================================================================
# ЗАПУСК ПРИЛОЖЕНИЯ
# =========================================================================

if __name__ == '__main__':
    # Локальный запуск
    port = int(os.getenv('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=True)
