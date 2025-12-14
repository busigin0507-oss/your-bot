"""
РАБОЧИЕ ФУНКЦИИ ДЛЯ СКАЧИВАНИЯ С YOUTUBE И PINTEREST
Работает на Vercel Python 3.12
"""

import yt_dlp
import requests
import re
import os
import tempfile
import logging
from urllib.parse import urlparse

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
    """
    СКАЧИВАНИЕ ВИДЕО С YOUTUBE
    Возвращает: {success, url, title, size_mb, error}
    """
    try:
        video_id = extract_youtube_id(url)
        if not video_id:
            return {
                'success': False,
                'error': 'Неверная ссылка YouTube',
                'type': 'youtube'
            }
        
        logger.info(f"Скачиваю YouTube видео: {video_id}")
        
        # Настройки yt-dlp для Vercel
        ydl_opts = {
            'format': 'best[height<=720]/best',
            'quiet': True,
            'no_warnings': False,
            'extract_flat': False,
            'outtmpl': f'%(title)s.%(ext)s',
            'max_filesize': 100 * 1024 * 1024,  # 100MB максимум
            'noprogress': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Получаем информацию о видео
            info = ydl.extract_info(url, download=False)
            title = info.get('title', 'YouTube Video')
            duration = info.get('duration', 0)
            
            # Проверяем длительность
            if duration > 600:  # 10 минут максимум
                return {
                    'success': False,
                    'error': 'Видео слишком длинное (>10 мин)',
                    'video_id': video_id,
                    'type': 'youtube'
                }
            
            # Получаем прямую ссылку на видео
            formats = info.get('formats', [])
            
            # Ищем подходящий формат
            best_format = None
            for fmt in formats:
                if fmt.get('ext') == 'mp4' and fmt.get('acodec') != 'none':
                    if quality == '720p' and fmt.get('height', 0) <= 720:
                        best_format = fmt
                        break
                    elif quality == '480p' and fmt.get('height', 0) <= 480:
                        best_format = fmt
                        break
                    elif quality == '360p' and fmt.get('height', 0) <= 360:
                        best_format = fmt
                        break
            
            if not best_format and formats:
                best_format = formats[0]
            
            if best_format and best_format.get('url'):
                video_url = best_format['url']
                filesize = best_format.get('filesize', 0) or best_format.get('filesize_approx', 0)
                size_mb = filesize / (1024 * 1024) if filesize else 0
                
                return {
                    'success': True,
                    'url': video_url,
                    'title': title,
                    'video_id': video_id,
                    'size_mb': round(size_mb, 1),
                    'duration': duration,
                    'quality': quality,
                    'type': 'youtube'
                }
            else:
                return {
                    'success': False,
                    'error': 'Не удалось получить ссылку на видео',
                    'video_id': video_id,
                    'type': 'youtube'
                }
    
    except yt_dlp.utils.DownloadError as e:
        logger.error(f"YouTube DownloadError: {e}")
        return {
            'success': False,
            'error': f'Ошибка YouTube: {str(e)}',
            'type': 'youtube'
        }
    except Exception as e:
        logger.error(f"YouTube Exception: {e}")
        return {
            'success': False,
            'error': f'Ошибка: {str(e)}',
            'type': 'youtube'
        }

def download_pinterest_media(url):
    """
    СКАЧИВАНИЕ МЕДИА С PINTEREST
    Возвращает: {success, url, type, title, error}
    """
    try:
        logger.info(f"Получаю Pinterest: {url}")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            return {
                'success': False,
                'error': f'Ошибка доступа: {response.status_code}',
                'type': 'pinterest'
            }
        
        html = response.text
        
        # Ищем Open Graph мета-теги
        og_image_match = re.search(r'<meta[^>]*property="og:image"[^>]*content="([^"]+)"', html, re.IGNORECASE)
        og_video_match = re.search(r'<meta[^>]*property="og:video"[^>]*content="([^"]+)"', html, re.IGNORECASE)
        og_title_match = re.search(r'<meta[^>]*property="og:title"[^>]*content="([^"]+)"', html, re.IGNORECASE)
        
        media_url = None
        media_type = 'image'
        title = 'Pinterest Media'
        
        if og_title_match:
            title = og_title_match.group(1)
        
        # Приоритет: видео → изображение
        if og_video_match:
            media_url = og_video_match.group(1)
            media_type = 'video'
        elif og_image_match:
            media_url = og_image_match.group(1)
            # Определяем тип по расширению
            if media_url.lower().endswith('.gif'):
                media_type = 'gif'
            elif media_url.lower().endswith(('.mp4', '.webm', '.mov')):
                media_type = 'video'
        
        # Если не нашли в OG, ищем в JSON-LD
        if not media_url:
            json_ld_match = re.search(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', html, re.DOTALL | re.IGNORECASE)
            if json_ld_match:
                try:
                    import json
                    json_data = json.loads(json_ld_match.group(1))
                    if json_data.get('image') and json_data['image'].get('url'):
                        media_url = json_data['image']['url']
                        if json_data.get('name'):
                            title = json_data['name']
                except:
                    pass
        
        if media_url:
            # Очищаем URL
            media_url = media_url.replace('\\/', '/')
            
            return {
                'success': True,
                'url': media_url,
                'type': media_type,
                'title': title,
                'source': 'pinterest'
            }
        else:
            return {
                'success': False,
                'error': 'Не удалось найти медиа на странице',
                'type': 'pinterest',
                'html_preview': html[:200] + '...'
            }
    
    except requests.RequestException as e:
        logger.error(f"Pinterest RequestError: {e}")
        return {
            'success': False,
            'error': f'Ошибка сети: {str(e)}',
            'type': 'pinterest'
        }
    except Exception as e:
        logger.error(f"Pinterest Exception: {e}")
        return {
            'success': False,
            'error': f'Ошибка: {str(e)}',
            'type': 'pinterest'
        }

def get_file_size(url):
    """Получение размера файла по URL"""
    try:
        response = requests.head(url, timeout=5, allow_redirects=True)
        if response.status_code == 200:
            size = int(response.headers.get('content-length', 0))
            return size / (1024 * 1024)  # в MB
    except:
        pass
    return 0

# Тестирование функций
if __name__ == '__main__':
    # Тест YouTube
    print("Testing YouTube download...")
    yt_result = download_youtube_video("https://youtu.be/YANkns00hUU")
    print(f"YouTube Result: {yt_result}")
    
    # Тест Pinterest
    print("\nTesting Pinterest download...")
    pin_result = download_pinterest_media("https://ru.pinterest.com/pin/492792384248890150/")
    print(f"Pinterest Result: {pin_result}")
