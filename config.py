"""
Configuration module for the Auto-Poster Bot.
Loads environment variables and provides configuration constants.
"""

import os
import logging
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

# Telegram Configuration
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
ADMIN_USER_ID = int(os.getenv('ADMIN_USER_ID', '0'))
TELEGRAM_GROUP_ID = os.getenv('TELEGRAM_GROUP_ID')

# Instagram Configuration
INSTAGRAM_USERNAME = os.getenv('INSTAGRAM_USERNAME')
INSTAGRAM_PASSWORD = os.getenv('INSTAGRAM_PASSWORD')
INSTAGRAM_SESSIONID = os.getenv('INSTAGRAM_SESSIONID')  # Optional: session cookie fallback

# VK Configuration
VK_ACCESS_TOKEN = os.getenv('VK_ACCESS_TOKEN')
VK_GROUP_ID = os.getenv('VK_GROUP_ID')

# Google AI Configuration
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')

# Image Processing Configuration
MAX_IMAGE_SIZE = (1080, 1080)  # Square format
STORY_IMAGE_SIZE = (1080, 1350)  # Story format
MAX_FILE_SIZE = 8 * 1024 * 1024  # 8MB in bytes
SUPPORTED_FORMATS = ['JPEG', 'PNG', 'WEBP']

# Paths
SESSIONS_DIR = 'sessions'
UPLOADS_DIR = 'uploads'

# Logging
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()  # DEBUG, INFO, WARNING, ERROR, CRITICAL

# Validation
def validate_config():
    """Validate that all required configuration is present."""
    required_vars = {
        'TELEGRAM_BOT_TOKEN': TELEGRAM_BOT_TOKEN,
        'ADMIN_USER_ID': ADMIN_USER_ID,
        'TELEGRAM_GROUP_ID': TELEGRAM_GROUP_ID,
        # Allow auth via USERNAME+PASSWORD or SESSIONID
        # We'll validate at runtime: at least one method must be provided
    }
    
    missing_vars = [var for var, value in required_vars.items() if not value]
    
    if missing_vars:
        raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
    
    if ADMIN_USER_ID == 0:
        raise ValueError("ADMIN_USER_ID must be a valid integer")
    
    # Instagram auth validation: require either creds or sessionid
    if not ((INSTAGRAM_USERNAME and INSTAGRAM_PASSWORD) or INSTAGRAM_SESSIONID):
        raise ValueError("Provide INSTAGRAM_USERNAME+INSTAGRAM_PASSWORD or INSTAGRAM_SESSIONID in .env")
    
    # VK validation (optional)
    if not (VK_ACCESS_TOKEN and VK_GROUP_ID):
        logger.warning("VK_ACCESS_TOKEN or VK_GROUP_ID not provided - VK posting will be disabled")
    
    # Google AI validation (optional)
    if not GOOGLE_API_KEY:
        logger.warning("GOOGLE_API_KEY not provided - AI assistance will be disabled")
    
    return True

# Bot Messages
MESSAGES = {
    'welcome': "🤖 Бот авто‑постинга запущен!\n\nПришлите фото(а), затем подпись — опубликую в Instagram и Telegram.",
    'send_caption': "📝 Пришлите подпись к этому посту.",
    'processing': "⏳ Обрабатываю и публикую пост...",
    'success': "✅ Пост опубликован в Instagram и Telegram!",
    'error': "❌ Ошибка публикации: {error}",
    'unauthorized': "🚫 У вас нет доступа к этому боту.",
    'invalid_photo': "📷 Отправьте корректное фото.",
    'too_many_photos': "📸 Слишком много фото! Допустимо 1–10 штук.",
    'no_photos': "📷 Сначала отправьте фото, потом подпись.",
    'instagram_error': "📸 Ошибка Instagram: {error}",
    'telegram_error': "💬 Ошибка Telegram: {error}",
    'cancelled': "❌ Операция отменена. Можете начать заново с кнопки '🚀 Начать публикацию'.",
    'cancelled_scheduled': "⏰ Запланированная публикация отменена.",
    'cancelled_cleanup': "🧹 Очистка данных завершена.",
}
