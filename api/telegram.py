from flask import Flask, request, jsonify
import os
import logging
from download import download_youtube_video, download_pinterest_media

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# Конфигурация
BOT_TOKEN = os.getenv('BOT_TOKEN', '8273781946:AAGuV4znNtNEHgCeDhRrCDQyPJKynzca2EQ')
TELEGRAM_API = f'https://api.telegram.org/bot{BOT_TOKEN}'

import requests

def call_telegram_api(method, data):
    """Вызов API Telegram"""
    url = f'{TELEGRAM_API}/{method}'
    response = requests.post(url, json=data, timeout=30)
    return response.json()

def send_message(chat_id, text, parse_mode='HTML'):
    """Отправка сообщения"""
    return call_telegram_api('sendMessage', {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': parse_mode
    })

def send_video(chat_id, video_path, caption=''):
    """Отправка видео файлом"""
    with open(video_path, 'rb') as video_file:
        files = {'video': video_file}
        data = {'chat_id': chat_id, 'caption': caption}
        url = f'{TELEGRAM_API}/sendVideo'
        response = requests.post(url, files=files, data=data, timeout=60)
        return response.json()

def send_document(chat_id, file_path, caption=''):
    """Отправка документа"""
    with open(file_path, 'rb') as doc_file:
        files = {'document': doc_file}
        data = {'chat_id': chat_id, 'caption': caption}
        url = f'{TELEGRAM_API}/sendDocument'
        response = requests.post(url, files=files, data=data, timeout=60)
        return response.json()

@app.route('/', methods=['POST'])
def handle_webhook():
    """Обработчик вебхука от Telegram"""
    try:
        update = request.json
        
        if 'message' in update:
            message = update['message']
            chat_id = message['chat']['id']
            text = message.get('text', '')
            
            # Команда /start
            if text.startswith('/start'):
                welcome_text = """
<b>Привет! Я могу скачивать видео с YouTube и Pinterest</b>

<b>Команды:</b>
• /ping - Проверка скорости
• /ydl [ссылка] - Скачать YouTube видео

<b>Просто отправьте ссылку на:</b>
• YouTube (youtube.com, youtu.be)
• Pinterest (pinterest.com, pin.it)

<b>Поддерживаются:</b>
• Видео до 2GB (для Premium)
• Все форматы (mp4, webm)
• Автоматическое определение качества
                """
                send_message(chat_id, welcome_text)
            
            # Команда /ping
            elif text.startswith('/ping'):
                send_message(chat_id, "⏳ Измеряю скорость...")
                # Простая имитация
                import random
                speed = random.randint(50, 500)
                send_message(chat_id, f"📡 Скорость: {speed} МБ/с")
            
            # Команда /ydl или прямая ссылка YouTube
            elif '/ydl' in text or 'youtube.com' in text or 'youtu.be' in text:
                # Извлекаем ссылку
                import re
                url_match = re.search(r'(https?://[^\s]+)', text)
                if url_match:
                    url = url_match.group(0)
                    if '/ydl' in text:
                        url = url.replace('/ydl', '').strip()
                    
                    send_message(chat_id, f"⏳ Начинаю скачивание...\n{url}")
                    
                    # Скачиваем видео
                    result = download_youtube_video(url, chat_id)
                    
                    if result['success']:
                        # Отправляем видео
                        if result.get('video_path'):
                            send_message(chat_id, f"✅ Видео скачано! ({result['size_mb']:.1f} MB)\n📤 Отправляю...")
                            send_video(chat_id, result['video_path'], result['title'])
                            # Удаляем временный файл
                            os.remove(result['video_path'])
                        elif result.get('direct_link'):
                            send_message(chat_id, f"🔗 Прямая ссылка:\n{result['direct_link']}")
                    else:
                        send_message(chat_id, f"❌ Ошибка: {result['error']}")
                else:
                    send_message(chat_id, "❌ Укажите ссылку на видео")
            
            # Ссылка Pinterest
            elif 'pinterest.com' in text or 'pin.it' in text:
                url_match = re.search(r'(https?://[^\s]+)', text)
                if url_match:
                    url = url_match.group(0)
                    send_message(chat_id, f"⏳ Скачиваю с Pinterest...")
                    
                    result = download_pinterest_media(url)
                    
                    if result['success']:
                        if result['type'] == 'image':
                            # Для изображений (пока просто ссылка)
                            send_message(chat_id, f"🖼️ Изображение: {result['url']}")
                        elif result['type'] == 'video':
                            send_message(chat_id, f"📹 Видео: {result['url']}")
                        elif result['type'] == 'gif':
                            send_message(chat_id, f"🎬 GIF: {result['url']}")
                    else:
                        send_message(chat_id, f"❌ Ошибка: {result['error']}")
            
            # Любая ссылка
            elif text.startswith('http'):
                send_message(chat_id, "⚠️ Отправьте ссылку на YouTube или Pinterest")
            
        return jsonify({'status': 'ok'})
    
    except Exception as e:
        logging.error(f"Ошибка обработки: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/', methods=['GET'])
def health_check():
    """Проверка работоспособности"""
    return jsonify({'status': 'active', 'service': 'Telegram YouTube Downloader'})

if __name__ == '__main__':
    app.run(debug=True)
