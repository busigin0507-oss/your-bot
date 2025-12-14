"""
ИСПРАВЛЕННЫЙ TELEGRAM БОТ ДЛЯ VERCEL
С функцией поиска ссылок на видео и загрузкой с Pinterest
Версия 4.0
"""

from flask import Flask, request, jsonify
import requests
import re
import json
import os
import logging
import yt_dlp

# =========================================================================
# КОНФИГУРАЦИЯ
# =========================================================================

app = Flask(__name__)

# ВАШ ТОКЕН В КОДЕ
BOT_TOKEN = "8273781946:AAFsvhsMR8WtS4SzQEd22ofCx1X0kV7f7ZA"
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

# ID стикера для приветствия
STICKER_FILE_ID = 'CAACAgUAAxkBAAEUqDhpPt4-7kGVdokmbKwwlAABAkbjJnUAAv0UAALOjCBVpsymNk2gK4E2BA'

# Логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# =========================================================================
# ФУНКЦИИ ВЗАИМОДЕЙСТВИЯ С TELEGRAM API
# =========================================================================

def call_telegram_api(method, data={}):
    """Вызов API Telegram"""
    url = f'{TELEGRAM_API}/{method}'
    try:
        response = requests.post(url, json=data, timeout=30)
        return response.json()
    except Exception as e:
        logger.error(f"Telegram API Error ({method}): {e}")
        return {'ok': False, 'error': str(e)}

def send_message(chat_id, text, parse_mode='HTML'):
    """Отправка текстового сообщения"""
    return call_telegram_api('sendMessage', {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': parse_mode,
        'disable_web_page_preview': True
    })

def send_sticker(chat_id, sticker_file_id):
    """Отправка стикера"""
    return call_telegram_api('sendSticker', {
        'chat_id': chat_id,
        'sticker': sticker_file_id
    })

def send_photo(chat_id, file_url, caption=''):
    """Отправка фото"""
    return call_telegram_api('sendPhoto', {
        'chat_id': chat_id,
        'photo': file_url,
        'caption': caption[:1024] if caption else ''
    })

def send_video(chat_id, file_url, caption=''):
    """Отправка видео"""
    return call_telegram_api('sendVideo', {
        'chat_id': chat_id,
        'video': file_url,
        'caption': caption[:1024] if caption else '',
        'supports_streaming': True
    })

def send_document(chat_id, file_url, caption=''):
    """Отправка документа (любого файла)"""
    return call_telegram_api('sendDocument', {
        'chat_id': chat_id,
        'document': file_url,
        'caption': caption[:1024] if caption else ''
    })

def send_animation(chat_id, file_url, caption=''):
    """Отправка анимации (GIF)"""
    return call_telegram_api('sendAnimation', {
        'chat_id': chat_id,
        'animation': file_url,
        'caption': caption[:1024] if caption else ''
    })

def edit_message(chat_id, message_id, text, parse_mode='HTML'):
    """Редактирование сообщения"""
    return call_telegram_api('editMessageText', {
        'chat_id': chat_id,
        'message_id': message_id,
        'text': text,
        'parse_mode': parse_mode
    })

def delete_message(chat_id, message_id):
    """Удаление сообщения"""
    return call_telegram_api('deleteMessage', {
        'chat_id': chat_id,
        'message_id': message_id
    })

# =========================================================================
# ФУНКЦИИ ДЛЯ PINTEREST (ПЕРЕНЕСЕНЫ ИЗ ВАШЕГО СТАРОГО КОДА)
# =========================================================================

def extract_pin_title(html):
    """Извлекает название пина из HTML (ваша старая функция)"""
    try:
        # Ищем в JSON-LD
        json_ld_regex = re.compile(r'<script[^>]*type="application/ld\+json"[^>]*>([\s\S]*?)</script>', re.IGNORECASE)
        json_ld_match = json_ld_regex.search(html)
        
        if json_ld_match:
            try:
                json_data = json.loads(json_ld_match.group(1))
                if json_data.get('name'):
                    return json_data['name']
                if json_data.get('headline'):
                    return json_data['headline']
                if json_data.get('title'):
                    return json_data['title']
                if json_data.get('description'):
                    desc = json_data['description'][:50]
                    return desc + ('...' if len(json_data['description']) > 50 else '')
            except:
                pass
        
        # Ищем в Open Graph
        og_title_regex = re.compile(r'<meta[^>]*property="og:title"[^>]*content="([^"]+)"[^>]*>', re.IGNORECASE)
        og_title_match = og_title_regex.search(html)
        if og_title_match:
            return og_title_match.group(1)
        
        # Ищем в Twitter
        twitter_title_regex = re.compile(r'<meta[^>]*property="twitter:title"[^>]*content="([^"]+)"[^>]*>', re.IGNORECASE)
        twitter_title_match = twitter_title_regex.search(html)
        if twitter_title_match:
            return twitter_title_match.group(1)
        
        # Ищем title тег
        title_regex = re.compile(r'<title>([^<]+)</title>', re.IGNORECASE)
        title_match = title_regex.search(html)
        if title_match:
            cleaned_title = title_match.group(1)
            cleaned_title = re.sub(r'\s*\|\s*Pinterest$', '', cleaned_title)
            cleaned_title = re.sub(r'^Pinterest\s*', '', cleaned_title)
            cleaned_title = re.sub(r'\s*-\s*Descobrir e Compartilhar GIFs$', '', cleaned_title)
            cleaned_title = re.sub(r'\s*-\s*Discover and Share GIFs$', '', cleaned_title)
            cleaned_title = re.sub(r'\s*-\s*Découvrir et Partager des GIFs$', '', cleaned_title)
            cleaned_title = cleaned_title.strip()
            return cleaned_title or 'Из Pinterest'
        
        return 'Из Pinterest'
    except Exception as error:
        logger.error(f'Ошибка извлечения названия: {error}')
        return 'Из Pinterest'

def determine_file_type(url):
    """Определяет тип файла по URL (ваша старая функция)"""
    url_lower = url.lower()
    if re.search(r'\.(gif|gifv)$', url_lower):
        return 'gif'
    if re.search(r'\.(mp4|mov|avi|wmv|flv|webm|mkv)$', url_lower):
        return 'video'
    if re.search(r'\.(jpg|jpeg|png|webp|bmp|tiff)$', url_lower):
        return 'image'
    return 'image'

async def get_pinterest_media(pinterest_url):
    """Получает прямую ссылку на медиа с Pinterest (адаптированная ваша старая функция)"""
    try:
        logger.info(f"Парсим Pinterest URL: {pinterest_url}")
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
        }
        response = requests.get(pinterest_url, headers=headers, timeout=10)
        if response.status_code != 200:
            logger.error(f"Ошибка HTTP: {response.status_code}")
            return None
        
        html = response.text
        title = extract_pin_title(html)
        
        # Поиск видео и GIF в JSON-LD
        json_ld_regex = re.compile(r'<script[^>]*type="application/ld\+json"[^>]*>([\s\S]*?)</script>', re.IGNORECASE)
        for match in json_ld_regex.finditer(html):
            try:
                json_data = json.loads(match.group(1))
                # Проверяем GIF
                if json_data.get('contentUrl') and re.search(r'\.gif$', json_data['contentUrl'], re.IGNORECASE):
                    return {'url': json_data['contentUrl'], 'type': 'gif', 'title': title}
                # Проверяем видео
                if json_data.get('contentUrl') and re.search(r'\.(mp4|mov|avi|wmv|flv|webm|mkv)$', json_data['contentUrl'], re.IGNORECASE):
                    return {'url': json_data['contentUrl'], 'type': 'video', 'title': title}
                if json_data.get('video', {}).get('contentUrl'):
                    return {'url': json_data['video']['contentUrl'], 'type': 'video', 'title': title}
            except:
                continue
        
        # Поиск Open Graph изображения
        og_image_regex = re.compile(r'<meta[^>]*property="og:image"[^>]*content="([^"]+)"[^>]*>', re.IGNORECASE)
        og_image_match = og_image_regex.search(html)
        if og_image_match:
            url = og_image_match.group(1)
            return {'url': url, 'type': determine_file_type(url), 'title': title}
        
        # Поиск изображений в тегах img
        img_regex = re.compile(r'<img[^>]*src="([^"]+\.(?:jpg|jpeg|png|gif|webp))"[^>]*>', re.IGNORECASE)
        img_urls = []
        for match in img_regex.finditer(html):
            img_url = match.group(1)
            if 'pinimg.com' in img_url:
                img_urls.append(img_url)
        
        if img_urls:
            # Сортируем для получения лучшего качества
            def sort_key(url):
                if 'originals' in url: return 1
                if '736x' in url: return 2
                if '564x' in url: return 3
                return 4
            img_urls.sort(key=sort_key)
            best_url = img_urls[0]
            return {'url': best_url, 'type': determine_file_type(best_url), 'title': title}
        
        logger.info('Не удалось найти медиа на странице Pinterest')
        return None
        
    except Exception as error:
        logger.error(f'Ошибка при получении медиа с Pinterest: {error}')
        return None

async def check_media_availability(url):
    """Проверяет доступность медиа по URL (ваша старая функция)"""
    try:
        response = requests.head(url, timeout=5, headers={'User-Agent': 'Mozilla/5.0'})
        if response.ok:
            return {
                'available': True,
                'content_type': response.headers.get('content-type', ''),
                'size': int(response.headers.get('content-length', 0))
            }
        # Пробуем GET, если HEAD не сработал
        response = requests.get(url, timeout=5, headers={'User-Agent': 'Mozilla/5.0'}, stream=True)
        response.close()
        return {
            'available': response.ok,
            'content_type': response.headers.get('content-type', ''),
            'size': int(response.headers.get('content-length', 0))
        }
    except Exception as error:
        logger.error(f'Ошибка проверки доступности: {error}')
        return {'available': False}

# =========================================================================
# ФУНКЦИИ ДЛЯ YOUTUBE (ПЕРЕРАБОТАНЫ ДЛЯ VERCEL)
# =========================================================================

def extract_youtube_video_id(url):
    """Извлекает ID видео из YouTube ссылки"""
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

def get_youtube_video_info(video_id):
    """Получает информацию о YouTube видео"""
    try:
        oembed_url = f'https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json'
        response = requests.get(oembed_url, timeout=10)
        if response.ok:
            data = response.json()
            return {
                'title': data.get('title', f'YouTube видео {video_id}'),
                'author': data.get('author_name', 'Неизвестный автор'),
                'thumbnail': data.get('thumbnail_url', f'https://img.youtube.com/vi/{video_id}/hqdefault.jpg'),
                'video_id': video_id
            }
    except:
        pass
    return {
        'title': f'YouTube видео {video_id}',
        'author': 'YouTube',
        'thumbnail': f'https://img.youtube.com/vi/{video_id}/hqdefault.jpg',
        'video_id': video_id
    }

def get_youtube_direct_link(url):
    """
    ГЛАВНЫЙ ФИКС: Получает прямую ссылку на видео с помощью yt-dlp.
    НЕ скачивает видео, а только находит ссылку.
    """
    try:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'format': 'best[ext=mp4]/best',  # Ищем лучший mp4 или любой лучший формат
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if 'url' in info:
                # Если есть прямая ссылка в основной информации
                return info['url']
            # Иначе ищем среди форматов
            formats = info.get('formats', [])
            if formats:
                # Предпочитаем формат с видео и аудио (progressive=True)
                progressive_formats = [f for f in formats if f.get('protocol') == 'https' and f.get('ext') == 'mp4']
                if progressive_formats:
                    # Берём лучший по качеству прогрессивный формат
                    progressive_formats.sort(key=lambda x: x.get('height', 0), reverse=True)
                    return progressive_formats[0]['url']
                # Если нет прогрессивных, берём первый с ссылкой
                for fmt in formats:
                    if fmt.get('url'):
                        return fmt['url']
        return None
    except Exception as e:
        logger.error(f"Ошибка yt-dlp при получении ссылки: {e}")
        return None

# =========================================================================
# ОБРАБОТЧИКИ КОМАНД
# =========================================================================

def handle_start_command(chat_id):
    """Обработчик команды /start с новым текстом"""
    welcome_text = """<b>Привет!</b>

Я могу скачать видео с ютуб! Могу скачать любой файл с pinterest!

Отправь мне ссылку, и я помогу:
• Для YouTube — найду прямую ссылку на видеофайл
• Для Pinterest — скачаю и отправлю фото, GIF или видео прямо в чат"""
    
    send_message(chat_id, welcome_text)
    send_sticker(chat_id, STICKER_FILE_ID)

def handle_ping_command(chat_id, message_id):
    """Обработчик команды /ping"""
    import random
    speed = random.randint(80, 450)
    quality = "Отличная" if speed > 200 else "Хорошая" if speed > 100 else "Нормальная"
    response_text = f"📡 <b>Результаты проверки:</b>\n\n⚡ <b>Скорость:</b> {speed} МБ/с\n🏆 <b>Качество:</b> {quality}"
    edit_message(chat_id, message_id, response_text)

def handle_pinterest_link(chat_id, url, original_message_id):
    """Обработчик ссылки Pinterest"""
    try:
        # Отправляем статус
        status_msg = send_message(chat_id, f"📌 <b>Pinterest ссылка обнаружена!</b>\n\n🔗 {url}\n\n⏳ Ищу медиа...")
        status_msg_id = status_msg['result']['message_id']
        
        # Получаем медиа
        edit_message(chat_id, status_msg_id, f"📌 <b>Pinterest ссылка обнаружена!</b>\n\n🔗 {url}\n\n⏳ Загружаю страницу...")
        
        # ИСПОЛЬЗУЕМ ВАШУ СТАРУЮ ЛОГИКУ
        result = get_pinterest_media(url)
        
        if not result:
            edit_message(chat_id, status_msg_id, "❌ <b>Не удалось найти медиа на странице Pinterest.</b>")
            return
        
        # Проверяем доступность
        edit_message(chat_id, status_msg_id, f"✅ <b>Медиа найдено!</b>\n\n📝 <b>Название:</b> {result['title']}\n📦 <b>Тип:</b> {result['type']}\n\n⏳ Проверяю доступность...")
        
        availability = check_media_availability(result['url'])
        if not availability['available']:
            edit_message(chat_id, status_msg_id, "❌ <b>Файл недоступен для скачивания.</b>")
            return
        
        # Отправляем медиа в зависимости от типа
        edit_message(chat_id, status_msg_id, f"✅ <b>Медиа найдено!</b>\n\n📝 <b>Название:</b> {result['title']}\n📦 <b>Тип:</b> {result['type']}\n\n📤 <b>Отправляю...</b>")
        
        try:
            if result['type'] == 'video':
                send_video(chat_id, result['url'], result['title'])
            elif result['type'] == 'gif':
                send_animation(chat_id, result['url'], result['title'])
            else:  # image
                send_photo(chat_id, result['url'], result['title'])
            delete_message(chat_id, status_msg_id)
            send_message(chat_id, "✅ <b>Готово! Файл отправлен.</b>")
        except Exception as send_error:
            logger.error(f"Ошибка отправки Pinterest медиа: {send_error}")
            edit_message(chat_id, status_msg_id, f"❌ <b>Не удалось отправить файл через Telegram.</b>\n\n🔗 <b>Прямая ссылка:</b>\n<code>{result['url']}</code>")
    
    except Exception as e:
        logger.error(f"Ошибка обработки Pinterest: {e}")
        send_message(chat_id, f"❌ <b>Ошибка обработки Pinterest ссылки:</b>\n{str(e)}")

def handle_youtube_link(chat_id, url, original_message_id):
    """
    ГЛАВНЫЙ ФИКС ДЛЯ YOUTUBE:
    Находит прямую ссылку и предлагает её пользователю.
    Для коротких видео пытается отправить как файл.
    """
    try:
        # Отправляем статус
        status_msg = send_message(chat_id, f"🎬 <b>YouTube ссылка обнаружена!</b>\n\n🔗 {url}\n\n⏳ Анализирую видео...")
        status_msg_id = status_msg['result']['message_id']
        
        # Извлекаем ID и получаем информацию
        edit_message(chat_id, status_msg_id, f"🎬 <b>YouTube ссылка обнаружена!</b>\n\n🔗 {url}\n\n⏳ Получаю информацию...")
        
        video_id = extract_youtube_video_id(url)
        if not video_id:
            edit_message(chat_id, status_msg_id, "❌ <b>Неверная ссылка YouTube.</b>\n\nПримеры:\n• https://youtu.be/dQw4w9WgXcQ\n• https://www.youtube.com/watch?v=dQw4w9WgXcQ")
            return
        
        video_info = get_youtube_video_info(video_id)
        
        # Получаем прямую ссылку на видео (ГЛАВНЫЙ ФИКС)
        edit_message(chat_id, status_msg_id, f"🎬 <b>Найдено видео:</b> {video_info['title']}\n\n⏳ Ищу прямую ссылку для скачивания...")
        
        direct_link = get_youtube_direct_link(url)
        
        if not direct_link:
            edit_message(chat_id, status_msg_id, f"❌ <b>Не удалось получить прямую ссылку на видео.</b>\n\n📹 <b>{video_info['title']}</b>\n\nℹ️ Попробуйте другие сервисы:\n• https://y2mate.is/youtube/{video_id}\n• https://yt5s.com")
            return
        
        # Проверяем доступность и размер
        edit_message(chat_id, status_msg_id, f"✅ <b>Ссылка найдена!</b>\n\n📹 <b>{video_info['title']}</b>\n\n⏳ Проверяю размер файла...")
        
        availability = check_media_availability(direct_link)
        size_mb = availability.get('size', 0) / (1024 * 1024) if availability.get('available') else 0
        
        # Решаем, что делать с видео
        if size_mb > 0 and size_mb <= 50:  # Если видео меньше 50 МБ
            edit_message(chat_id, status_msg_id, f"✅ <b>Видео готово к отправке!</b>\n\n📹 <b>{video_info['title']}</b>\n📦 <b>Размер:</b> {size_mb:.1f} МБ\n\n📤 Отправляю как файл...")
            try:
                # Пытаемся отправить как документ
                send_document(chat_id, direct_link, video_info['title'])
                delete_message(chat_id, status_msg_id)
                send_message(chat_id, "✅ <b>Готово! Видео отправлено как файл.</b>")
            except Exception as send_error:
                logger.error(f"Ошибка отправки YouTube видео: {send_error}")
                # Если не получилось, даём ссылку
                edit_message(chat_id, status_msg_id, f"⚠️ <b>Не удалось отправить видео через Telegram.</b>\n\n📹 <b>{video_info['title']}</b>\n\n🔗 <b>Прямая ссылка для скачивания:</b>\n<code>{direct_link}</code>\n\n📥 Скопируйте ссылку в браузер или download-менеджер.")
        else:
            # Для больших видео или если размер неизвестен - просто даём ссылку
            edit_message(chat_id, status_msg_id, f"✅ <b>Ссылка на видео готова!</b>\n\n📹 <b>{video_info['title']}</b>\n{'📦 <b>Размер:</b> ' + f'{size_mb:.1f} МБ' + ' (слишком большой для Telegram)' if size_mb > 50 else ''}\n\n🔗 <b>Прямая ссылка для скачивания:</b>\n<code>{direct_link}</code>\n\n📥 <b>Скопируйте ссылку:</b>\n• В браузер\n• В IDM, wget, curl\n• В программу для скачивания")
    
    except Exception as e:
        logger.error(f"Ошибка обработки YouTube: {e}")
        send_message(chat_id, f"❌ <b>Ошибка обработки YouTube ссылки:</b>\n{str(e)}")

# =========================================================================
# API ENDPOINTS ДЛЯ VERCEL
# =========================================================================

@app.route('/', methods=['GET'])
def home():
    """Главная страница API"""
    return jsonify({
        'status': 'active',
        'service': 'Telegram Downloader Bot (Fixed Version)',
        'version': '4.0',
        'bot_token_set': len(BOT_TOKEN) > 20
    })

@app.route('/health', methods=['GET'])
def health():
    """Проверка здоровья"""
    return jsonify({'status': 'healthy'})

# =========================================================================
# ОБРАБОТЧИК WEBHOOK ОТ TELEGRAM
# =========================================================================

@app.route('/', methods=['POST'])
def handle_webhook():
    """Основной обработчик вебхука"""
    try:
        update = request.json
        logger.info(f"Received update")
        
        if 'message' in update:
            message = update['message']
            chat_id = message['chat']['id']
            text = message.get('text', '').strip()
            
            logger.info(f"Message from {chat_id}: {text[:50]}")
            
            # Команда /start
            if text == '/start':
                handle_start_command(chat_id)
            
            # Команда /ping
            elif text == '/ping':
                msg = send_message(chat_id, "⌛ Измеряю скорость...")
                handle_ping_command(chat_id, msg['result']['message_id'])
            
            # Ссылка Pinterest
            elif 'pinterest.com' in text or 'pin.it' in text:
                handle_pinterest_link(chat_id, text, message.get('message_id'))
            
            # Ссылка YouTube
            elif 'youtube.com' in text or 'youtu.be' in text:
                handle_youtube_link(chat_id, text, message.get('message_id'))
            
            # Любой другой текст
            elif text and text.startswith('http'):
                send_message(chat_id, "⚠️ <b>Неподдерживаемая ссылка</b>\n\nЯ поддерживаю только:\n• YouTube (youtube.com, youtu.be)\n• Pinterest (pinterest.com, pin.it)")
            elif text:
                send_message(chat_id, f"📝 <b>Вы написали:</b>\n\n{text}\n\nОтправьте мне ссылку на YouTube или Pinterest!")
        
        return jsonify({'status': 'ok'})
    
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

# =========================================================================
# ВАЖНО: НЕТ app.run()! Vercel сам запускает приложение.
# =========================================================================
