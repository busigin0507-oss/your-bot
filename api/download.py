import yt_dlp
import os
import tempfile
import re
import requests
from urllib.parse import urlparse

def download_youtube_video(url, chat_id=None):
    """
    Скачивает видео с YouTube используя yt-dlp
    Возвращает путь к файлу или прямую ссылку
    """
    try:
        # Опции для yt-dlp
        ydl_opts = {
            'format': 'best[height<=720]/best',  # Максимум 720p для экономии места
            'outtmpl': os.path.join(tempfile.gettempdir(), '%(title)s.%(ext)s'),
            'quiet': False,
            'no_warnings': False,
            'extract_flat': False,
            'merge_output_format': 'mp4',
            'max_filesize': 200 * 1024 * 1024,  # Максимум 200MB (для бесплатных аккаунтов)
            'progress_hooks': [lambda d: print_progress(d, chat_id)] if chat_id else [],
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Получаем информацию о видео
            info = ydl.extract_info(url, download=False)
            title = info.get('title', 'YouTube Video')
            duration = info.get('duration', 0)
            
            # Проверяем длительность (максимум 30 минут для бесплатного)
            if duration > 1800:  # 30 минут
                return {
                    'success': False,
                    'error': 'Видео слишком длинное (>30 мин). Используйте /ydl для попытки скачать короткий фрагмент'
                }
            
            # Скачиваем видео
            send_progress(chat_id, f"📥 Скачиваю: {title[:50]}...")
            result = ydl.download([url])
            
            # Ищем скачанный файл
            filename = ydl.prepare_filename(info)
            if not os.path.exists(filename):
                # Ищем с другим расширением
                base = os.path.splitext(filename)[0]
                for ext in ['.mp4', '.webm', '.mkv']:
                    if os.path.exists(base + ext):
                        filename = base + ext
                        break
            
            if os.path.exists(filename):
                size_mb = os.path.getsize(filename) / (1024 * 1024)
                return {
                    'success': True,
                    'video_path': filename,
                    'title': title,
                    'size_mb': size_mb,
                    'duration': duration
                }
            else:
                return {
                    'success': False,
                    'error': 'Не удалось найти скачанный файл'
                }
    
    except yt_dlp.utils.DownloadError as e:
        return {
            'success': False,
            'error': f'Ошибка скачивания: {str(e)}'
        }
    except Exception as e:
        return {
            'success': False,
            'error': f'Неизвестная ошибка: {str(e)}'
        }

def download_pinterest_media(url):
    """
    Получает медиа с Pinterest
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            return {
                'success': False,
                'error': f'Ошибка HTTP {response.status_code}'
            }
        
        html = response.text
        
        # Ищем Open Graph изображение
        og_image_match = re.search(r'<meta[^>]*property="og:image"[^>]*content="([^"]+)"', html)
        og_video_match = re.search(r'<meta[^>]*property="og:video"[^>]*content="([^"]+)"', html)
        
        media_url = None
        media_type = 'image'
        
        if og_video_match:
            media_url = og_video_match.group(1)
            media_type = 'video'
        elif og_image_match:
            media_url = og_image_match.group(1)
            # Проверяем тип по расширению
            if media_url.lower().endswith('.gif'):
                media_type = 'gif'
            elif media_url.lower().endswith(('.mp4', '.webm', '.mov')):
                media_type = 'video'
        
        if media_url:
            return {
                'success': True,
                'url': media_url,
                'type': media_type,
                'source': 'pinterest'
            }
        else:
            return {
                'success': False,
                'error': 'Не удалось найти медиа на странице'
            }
    
    except Exception as e:
        return {
            'success': False,
            'error': f'Ошибка: {str(e)}'
        }

def print_progress(d, chat_id):
    """Вывод прогресса скачивания"""
    if d['status'] == 'downloading':
        percent = d.get('_percent_str', '0%').strip()
        speed = d.get('_speed_str', 'N/A')
        eta = d.get('_eta_str', 'N/A')
        
        message = f"📥 Скачиваю: {percent}\n⚡ Скорость: {speed}\n⏱️ Осталось: {eta}"
        send_progress(chat_id, message)
    elif d['status'] == 'finished':
        send_progress(chat_id, "✅ Скачивание завершено!\n🎬 Конвертирую в MP4...")

def send_progress(chat_id, message):
    """Отправка сообщения о прогрессе"""
    if not chat_id:
        return
    
    try:
        import requests
        BOT_TOKEN = os.getenv('BOT_TOKEN')
        url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage'
        data = {
            'chat_id': chat_id,
            'text': message,
            'parse_mode': 'HTML'
        }
        requests.post(url, json=data, timeout=5)
    except:
        pass  # Игнорируем ошибки отправки прогресса
