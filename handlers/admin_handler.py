"""
Admin handler for the Auto-Poster Bot.
Handles admin messages, photo processing, and post publishing.
"""

import os
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from telegram import Update, Message, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
from telegram.ext import ContextTypes
from telegram.error import TelegramError

from config import ADMIN_USER_ID, MESSAGES
from utils.image_processor import ImageProcessor
from services.instagram_service import InstagramService
from services.telegram_service import TelegramService
from services.vk_service import VKService
from services.ai_service import AIService
from services.scheduler_service import SchedulerService, QueuedPost

logger = logging.getLogger("admin")

class AdminHandler:
    """Handles admin interactions and post processing."""
    
    def __init__(self):
        """Initialize the admin handler."""
        self.image_processor = ImageProcessor()
        self.instagram_service = InstagramService()
        self.telegram_service = TelegramService()
        self.vk_service = VKService()
        self.ai_service = AIService()
        self.scheduler_service = SchedulerService()
        
        # User state management: {user_id: {'photos': [], 'waiting_for_caption': bool, 'post_mode': 'auto'|'single'|'multi'|'reels', 'target_platform': 'both'|'instagram'|'telegram'|'vk'|'all', 'step': 'start'|'type_selected'|'platform_selected'|'article_check_selection'|'photos_uploaded'|'caption_entered'|'preview_shown'|'scheduled'|'reels_url_input'|'reels_download', 'cancelled': bool, 'check_articles': bool, 'reels_url': str, 'reels_video_path': str}}
        self.user_states: Dict[int, Dict] = {}
        # Pending posts waiting for approval: {user_id: {'photos': [], 'caption': str, 'message_id': int, 'target_platform': str, 'scheduled_time': datetime}}
        self.pending_posts: Dict[int, Dict] = {}
        # Scheduled posts: {user_id: {'task': asyncio.Task, 'post_data': dict}}
        self.scheduled_posts: Dict[int, Dict] = {}
        
        # Set up scheduler publish callback
        self.scheduler_service.set_publish_callback(self._publish_from_queue)

    def get_main_keyboard(self) -> ReplyKeyboardMarkup:
        """Return the main reply keyboard for quick actions."""
        keyboard = [
            [KeyboardButton("🚀 Начать публикацию")],
            [KeyboardButton("📋 Очередь постов"), KeyboardButton("➕ Добавить ссылку")],
            [KeyboardButton("✅ Status"), KeyboardButton("❌ Cancel")],
            [KeyboardButton("ℹ️ Help")],
        ]
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    def get_type_selection_keyboard(self) -> ReplyKeyboardMarkup:
        """Return keyboard for post type selection (deprecated - now auto-detect)."""
        keyboard = [
            [KeyboardButton("📷 Одиночный пост"), KeyboardButton("📸 Массовый пост")],
            [KeyboardButton("📹 Публикация рилс")],
            [KeyboardButton("❌ Отмена")],
        ]
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    def get_content_input_keyboard(self) -> ReplyKeyboardMarkup:
        """Return keyboard for content input step."""
        keyboard = [
            [KeyboardButton("❌ Отмена")],
        ]
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    def get_platform_selection_keyboard(self) -> ReplyKeyboardMarkup:
        """Return keyboard for platform selection."""
        keyboard = [
            [KeyboardButton("📷 Instagram"), KeyboardButton("💬 Telegram")],
            [KeyboardButton("🔵 VK"), KeyboardButton("🔀 Все платформы")],
            [KeyboardButton("❌ Отмена")],
        ]
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    def get_article_check_keyboard(self) -> ReplyKeyboardMarkup:
        """Return keyboard for article check selection."""
        keyboard = [
            [KeyboardButton("🔍 Да, искать артикулы"), KeyboardButton("⏭️ Нет, пропустить")],
            [KeyboardButton("❌ Отмена")],
        ]
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    def get_schedule_keyboard(self) -> ReplyKeyboardMarkup:
        """Return keyboard for scheduling options."""
        keyboard = [
            [KeyboardButton("⚡ Опубликовать сейчас"), KeyboardButton("⏰ Запланировать")],
            [KeyboardButton("🤖 Помощь ИИ"), KeyboardButton("❌ Отмена")],
        ]
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    def is_admin(self, user_id: int) -> bool:
        """
        Check if user is authorized admin.
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            bool: True if user is admin
        """
        return user_id == ADMIN_USER_ID
    
    def get_user_state(self, user_id: int) -> Dict:
        """
        Get user state or create new one.
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            dict: User state dictionary
        """
        if user_id not in self.user_states:
            self.user_states[user_id] = {
                'photos': [],
                'waiting_for_caption': False,
                'post_mode': 'auto',  # 'single' or 'multi' or 'reels'
                'target_platform': 'both',  # 'instagram' | 'telegram' | 'vk' | 'both' | 'all'
                'step': 'start',  # 'start' | 'type_selected' | 'platform_selected' | 'article_check_selection' | 'photos_uploaded' | 'caption_entered' | 'preview_shown' | 'scheduled' | 'reels_url_input' | 'reels_download' | 'reels_waiting_caption'
                'scheduled_time': None,
                'article_numbers': [],  # List of found article numbers
                'cancelled': False,  # Flag to indicate if operation was cancelled
                'check_articles': True,  # Flag to indicate if article check is needed
                'reels_url': None,  # Instagram reels URL
                'reels_video_path': None,  # Downloaded video path
            }
        return self.user_states[user_id]
    
    def clear_user_state(self, user_id: int):
        """
        Clear user state and cleanup files.
        
        Args:
            user_id: Telegram user ID
        """
        if user_id in self.user_states:
            state = self.user_states[user_id]
            # Cleanup photo files
            if state.get('photos'):
                self.image_processor.cleanup_files(state['photos'])
            # Clear state
            del self.user_states[user_id]
    
    async def handle_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle photo messages from admin with auto-detection.
        
        Args:
            update: Telegram update object
            context: Bot context
        """
        if not self.is_admin(update.effective_user.id):
            await update.message.reply_text(MESSAGES['unauthorized'])
            return
        
        try:
            # Get user state
            user_state = self.get_user_state(update.effective_user.id)
            
            # Check if we're in the right step, or allow direct photo upload
            if user_state['step'] not in ['content_input', 'photos_upload', 'caption_entered']:
                # Allow direct photo upload - set default values
                user_state['post_mode'] = 'auto'  # Auto-detect mode
                user_state['target_platform'] = 'both'  # Default to both platforms
                user_state['check_articles'] = True  # Default to article check
                user_state['step'] = 'content_input'
                await update.message.reply_text("📸 Прямая загрузка фото! Режим: авто, платформы: Instagram + Telegram, поиск артикулов: включен")
            
            # Auto-detect: photos = photo post mode
            user_state['post_mode'] = 'multi'  # Will handle single/multi automatically by count
            
            # Get the highest resolution photo
            photo = update.message.photo[-1]
            file = await context.bot.get_file(photo.file_id)
            
            # Download photo
            photo_path = os.path.join(self.image_processor.uploads_dir, f"temp_{photo.file_id}.jpg")
            await file.download_to_drive(photo_path)
            
            # Validate photo
            if not self.image_processor.validate_image(photo_path):
                os.remove(photo_path)
                await update.message.reply_text(MESSAGES['invalid_photo'])
                return
            
            # Add photo to state (auto mode allows multiple photos)
            user_state['photos'].append(photo_path)
            
            # Check photo count
            if len(user_state['photos']) > 10:
                self.clear_user_state(update.effective_user.id)
                await update.message.reply_text(MESSAGES['too_many_photos'])
                return
            
            # Update step
            user_state['step'] = 'photos_uploaded'
            user_state['waiting_for_caption'] = True
            
            # Search for article numbers in uploaded photos (if enabled)
            article_numbers = []
            if user_state.get('check_articles', True):
                processing_msg = await update.message.reply_text("🔍 Ищу артикулы на фотографиях...")
                
                # Update message to show progress
                await processing_msg.edit_text("🔍 Ищу артикулы на фотографиях...\n\n📸 Анализирую изображения...")
                
                # Check if cancelled before processing
                if user_state.get('cancelled', False):
                    await processing_msg.edit_text("❌ Операция отменена.")
                    return
                
                article_numbers = await self.image_processor.extract_article_numbers_async(user_state['photos'], self.ai_service)
                
                # Check if cancelled after processing
                if user_state.get('cancelled', False):
                    await processing_msg.edit_text("❌ Операция отменена.")
                    return
                
                # Store article numbers in user state
                user_state['article_numbers'] = article_numbers
            else:
                # Skip article check
                user_state['article_numbers'] = []
            
            # Reply based on photo count, mode, and found articles
            mode = user_state.get('post_mode', 'multi')
            
            # Create detailed article info
            if user_state.get('check_articles', True):
                if article_numbers:
                    articles_text = self.image_processor.format_articles_for_caption(article_numbers)
                    article_info = f"\n\n✅ <b>Найдены артикулы:</b>\n{articles_text}\n\n📝 Артикулы будут автоматически добавлены в описание поста"
                else:
                    article_info = "\n\n❌ <b>Артикулы не найдены</b>\n\n💡 Попробуйте загрузить фото с более четкими номерами товаров"
            else:
                article_info = "\n\n⏭️ <b>Поиск артикулов пропущен</b>\n\n📝 Артикулы не будут добавлены в пост"
            
            # Create response message
            if mode == 'single':
                response_text = f"📷 <b>Фото загружено!</b>{article_info}\n\n📝 Теперь отправьте подпись к посту."
            else:
                if len(user_state['photos']) == 1:
                    response_text = f"📸 <b>Фото загружено!</b>{article_info}\n\n📸 Можете отправить ещё фото (до 10) или сразу подпись к посту."
                else:
                    response_text = f"📸 <b>Фото {len(user_state['photos'])} загружено.</b>{article_info}\n\n📸 Можете отправить ещё фото (до 10) или подпись к посту."
            
            if user_state.get('check_articles', True):
                await processing_msg.edit_text(response_text, parse_mode='HTML')
            else:
                await update.message.reply_text(response_text, parse_mode='HTML')
            
        except Exception as e:
            logger.error(f"Error handling photo: {e}")
            await update.message.reply_text(f"Error processing photo: {str(e)}")
    
    async def handle_video(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle video messages from admin with auto-detection.
        
        Args:
            update: Telegram update object
            context: Bot context
        """
        if not self.is_admin(update.effective_user.id):
            await update.message.reply_text(MESSAGES['unauthorized'])
            return
        
        try:
            # Get user state
            user_state = self.get_user_state(update.effective_user.id)
            
            # Check if we're in the right step, or allow direct video upload
            if user_state['step'] not in ['content_input', 'photos_upload']:
                # Allow direct video upload - set default values
                user_state['post_mode'] = 'video'  # Video mode
                user_state['target_platform'] = 'all'  # Telegram + VK (Instagram doesn't support video upload via API)
                user_state['check_articles'] = False  # No article check for videos
                user_state['step'] = 'content_input'
                await update.message.reply_text("📹 Прямая загрузка видео! Режим: видео, платформы: Telegram + VK")
            
            # Auto-detect: video = video post mode
            user_state['post_mode'] = 'video'
            
            # Get video
            video = update.message.video
            file = await context.bot.get_file(video.file_id)
            
            # Download video
            video_path = os.path.join(self.image_processor.uploads_dir, f"temp_{video.file_id}.mp4")
            await file.download_to_drive(video_path)
            
            # Save video path
            user_state['reels_video_path'] = video_path
            user_state['step'] = 'reels_waiting_caption'
            user_state['waiting_for_caption'] = True
            
            # Send confirmation
            await update.message.reply_text(
                "✅ <b>Видео загружено!</b>\n\n"
                "📝 Теперь отправьте подпись к видео.",
                parse_mode='HTML'
            )
            
        except Exception as e:
            logger.error(f"Error handling video: {e}")
            await update.message.reply_text(f"❌ Ошибка обработки видео: {str(e)}")
    
    async def handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle text messages from admin with auto-detection (captions, Instagram URLs, queue links).
        
        Args:
            update: Telegram update object
            context: Bot context
        """
        if not self.is_admin(update.effective_user.id):
            await update.message.reply_text(MESSAGES['unauthorized'])
            return
        
        user_state = self.get_user_state(update.effective_user.id)
        text = update.message.text.strip()
        
        # Check if we're waiting for link for queue
        if user_state.get('step') == 'waiting_for_link':
            await self.handle_link_input(update, context)
            return
        
        # AUTO-DETECT: Check if this is an Instagram URL when waiting for content
        if user_state.get('step') == 'content_input':
            if 'instagram.com' in text or 'instagr.am' in text:
                # Auto-detect Instagram URL
                if '/reel/' in text:
                    # It's a reels URL
                    logger.info(f"Auto-detected Instagram reels URL: {text}")
                    user_state['post_mode'] = 'reels'
                    user_state['step'] = 'reels_url_input'
                    await self.handle_reels_url_input(update, context)
                    return
                elif '/p/' in text:
                    # It's a post URL
                    logger.info(f"Auto-detected Instagram post URL: {text}")
                    await update.message.reply_text(
                        "🔗 <b>Обнаружена ссылка на Instagram пост</b>\n\n"
                        "⚠️ Данная функция пока не реализована.\n"
                        "Пожалуйста, скачайте фото с поста вручную и отправьте их сюда.",
                        parse_mode='HTML'
                    )
                    return
                else:
                    await update.message.reply_text(
                        "❌ Неверный формат ссылки Instagram.\n\n"
                        "Поддерживаются:\n"
                        "• /reel/ - рилсы\n"
                        "• /p/ - посты"
                    )
                    return
        
        # Check if we're waiting for reels URL (legacy path)
        if user_state['step'] == 'reels_url_input':
            await self.handle_reels_url_input(update, context)
            return
        
        # Check if we're waiting for caption for reels
        if user_state['post_mode'] == 'reels' and user_state['step'] == 'reels_waiting_caption':
            caption = update.message.text
            if not caption.strip():
                await update.message.reply_text("Отправьте корректную подпись.")
                return
            
            # Save caption to user state
            user_state['caption'] = caption
            user_state['step'] = 'caption_entered'
            
            # Ask for scheduling
            platform_text = {
                'telegram': 'Telegram',
                'vk': 'VK',
                'both': 'Telegram и VK',
                'all': 'Telegram и VK'
            }.get(user_state['target_platform'], 'неизвестно')
            
            message = f"""📋 <b>Готово к публикации!</b>

<b>Платформа:</b> {platform_text}
<b>Тип:</b> рилс
<b>Подпись:</b> {caption}

<b>Шаг 4:</b> Выберите время публикации:"""
            
            await update.message.reply_text(message, parse_mode='HTML', reply_markup=self.get_schedule_keyboard())
            return
        
        # Check if we're waiting for caption
        if not user_state['waiting_for_caption']:
            await update.message.reply_text("Сначала отправьте фото.")
            return
        
        if not user_state['photos']:
            await update.message.reply_text(MESSAGES['no_photos'])
            return
        
        caption = update.message.text
        if not caption.strip():
            await update.message.reply_text("Отправьте корректную подпись.")
            return
        
        # Save caption to user state
        user_state['caption'] = caption
        
        # Update step
        user_state['step'] = 'caption_entered'
        
        # Prepare caption with articles for preview
        article_numbers = user_state.get('article_numbers', [])
        if article_numbers:
            articles_text = self.image_processor.format_articles_for_caption(article_numbers)
            preview_caption = f"{caption}\n\n{articles_text}"
        else:
            preview_caption = caption
        
        # Show preview and ask for scheduling
        try:
            if len(user_state['photos']) == 1:
                with open(user_state['photos'][0], 'rb') as f:
                    preview_msg = await update.message.reply_photo(
                        photo=f,
                        caption=f"<b>Предпросмотр поста:</b>\n\n{preview_caption}",
                        parse_mode='HTML'
                    )
            else:
                media = []
                for i, p in enumerate(user_state['photos']):
                    with open(p, 'rb') as f:
                        media.append(InputMediaPhoto(media=f, caption=f"<b>Предпросмотр поста:</b>\n\n{preview_caption}" if i == 0 else None, parse_mode='HTML'))
                preview_group = await update.message.reply_media_group(media=media)
                preview_msg = preview_group[0] if preview_group else None
            
            # Ask for scheduling
            platform_text = {
                'instagram': 'Instagram',
                'telegram': 'Telegram',
                'vk': 'VK',
                'both': 'Instagram и Telegram',
                'all': 'Instagram, Telegram и VK'
            }.get(user_state['target_platform'], 'неизвестно')
            
            # Add article information to preview message
            article_info = ""
            if article_numbers:
                article_info = f"\n<b>Найдено артикулов:</b> {len(article_numbers)} ({', '.join(article_numbers)})"
            else:
                article_info = "\n<b>Артикулы:</b> не найдены"
            
            message = f"""📋 <b>Предпросмотр готов!</b>

<b>Платформа:</b> {platform_text}
<b>Тип поста:</b> {'одиночный' if user_state['post_mode'] == 'single' else 'массовый'}
<b>Количество фото:</b> {len(user_state['photos'])}{article_info}

<b>Шаг 4:</b> Выберите время публикации:"""
            
            await update.message.reply_text(message, parse_mode='HTML', reply_markup=self.get_schedule_keyboard())
            
        except Exception as e:
            logger.error(f"Error sending preview: {e}")
            await update.message.reply_text(f"Ошибка предпросмотра: {e}")
            return

    async def handle_publish_now(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle immediate publishing."""
        if not self.is_admin(update.effective_user.id):
            await update.message.reply_text(MESSAGES['unauthorized'])
            return
        
        user_state = self.get_user_state(update.effective_user.id)
        if user_state['step'] != 'caption_entered':
            await update.message.reply_text("❌ Неверный шаг. Начните с /start")
            return
        
        # Process and publish immediately
        if user_state['post_mode'] == 'reels':
            await self._process_and_publish_reels(update, context, user_state, immediate=True)
        else:
            await self._process_and_publish(update, context, user_state, immediate=True)

    async def handle_ai_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle AI help for caption improvement."""
        if not self.is_admin(update.effective_user.id):
            await update.message.reply_text(MESSAGES['unauthorized'])
            return
        
        user_state = self.get_user_state(update.effective_user.id)
        if user_state['step'] != 'caption_entered':
            await update.message.reply_text("❌ Неверный шаг. Начните с /start")
            return
        
        # Check if AI service is available
        if not self.ai_service.enabled:
            await update.message.reply_text("❌ ИИ сервис недоступен. Проверьте настройки GOOGLE_API_KEY.")
            return
        
        # Check if this is reels mode
        is_reels = user_state.get('post_mode') == 'reels'
        
        # Show processing message
        if is_reels:
            processing_msg = await update.message.reply_text("🤖 ИИ адаптирует описание рилса из Instagram...")
        else:
            processing_msg = await update.message.reply_text("🤖 ИИ обрабатывает ваше описание...")
        
        # Check if cancelled before AI processing
        if user_state.get('cancelled', False):
            await processing_msg.edit_text("❌ Операция отменена.")
            return
        
        try:
            if is_reels:
                # For reels: get original caption from Instagram and adapt it
                reels_url = user_state.get('reels_url')
                if not reels_url:
                    await processing_msg.edit_text("❌ Ссылка на рилс не найдена!")
                    return
                
                # Get original caption from Instagram
                await processing_msg.edit_text("🔍 Получаю оригинальное описание из Instagram...")
                original_caption = self.instagram_service.get_reels_caption(reels_url)
                
                if not original_caption:
                    # If can't get original caption, use user's caption
                    original_caption = user_state.get('caption', '')
                    if not original_caption:
                        await processing_msg.edit_text("❌ Не удалось получить описание рилса. Попробуйте ввести описание вручную.")
                        return
                    await processing_msg.edit_text(f"ℹ️ Не удалось извлечь оригинальное описание из Instagram.\nИспользую ваше описание: {original_caption}")
                else:
                    await processing_msg.edit_text(f"✅ Получено оригинальное описание:\n\n{original_caption[:200]}...\n\n🤖 Адаптирую для публикации...")
                
                # Adapt caption with AI
                adapted_caption = await self.ai_service.adapt_reels_caption(
                    original_caption,
                    user_state['target_platform']
                )
                
                if adapted_caption:
                    # Update caption in user state
                    user_state['caption'] = adapted_caption
                    
                    # Show adapted caption
                    await processing_msg.edit_text(
                        f"🤖 <b>ИИ адаптировал описание рилса:</b>\n\n"
                        f"<b>Было (Instagram):</b>\n{original_caption[:150]}{'...' if len(original_caption) > 150 else ''}\n\n"
                        f"<b>Стало (для публикации):</b>\n{adapted_caption}",
                        parse_mode='HTML'
                    )
                    
                    # Ask for scheduling again
                    platform_text = {
                        'telegram': 'Telegram',
                        'vk': 'VK',
                        'both': 'Telegram и VK',
                        'all': 'Telegram и VK'
                    }.get(user_state['target_platform'], 'неизвестно')
                    
                    message = f"""📋 <b>Готово к публикации!</b>

<b>Платформа:</b> {platform_text}
<b>Тип:</b> рилс
<b>Адаптированное описание:</b> {adapted_caption}

<b>Выберите время публикации:</b>"""
                    
                    await update.message.reply_text(message, parse_mode='HTML', reply_markup=self.get_schedule_keyboard())
                else:
                    await processing_msg.edit_text("❌ Не удалось адаптировать описание. Попробуйте еще раз.")
            else:
                # For regular posts: improve user's caption
                if not user_state.get('caption'):
                    await update.message.reply_text("❌ Подпись не найдена!")
                    return
                
                # Get article numbers from user state
                article_numbers = user_state.get('article_numbers', [])
                
                # Prepare caption for AI improvement (only the description part, not articles)
                caption_for_ai = user_state['caption']
                
                # Get improved caption
                improved_caption = await self.ai_service.improve_caption(
                    caption_for_ai, 
                    user_state['target_platform']
                )
                
                # Check if cancelled after AI processing
                if user_state.get('cancelled', False):
                    await processing_msg.edit_text("❌ Операция отменена.")
                    return
                
                if improved_caption:
                    # Update caption in user state (only the description part)
                    user_state['caption'] = improved_caption
                    
                    # Show improved caption
                    await processing_msg.edit_text(
                        f"🤖 <b>ИИ улучшил ваше описание:</b>\n\n{improved_caption}",
                        parse_mode='HTML'
                    )
                    
                    # Show preview with improved caption (articles will be added automatically)
                    await self._show_preview_with_caption(update, context, user_state, improved_caption)
                else:
                    await processing_msg.edit_text("❌ Не удалось улучшить описание. Попробуйте еще раз.")
                
        except Exception as e:
            logger.error(f"Error in AI help: {e}")
            await processing_msg.edit_text(f"❌ Ошибка ИИ: {e}")

    async def handle_schedule_post(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle post scheduling."""
        if not self.is_admin(update.effective_user.id):
            await update.message.reply_text(MESSAGES['unauthorized'])
            return
        
        user_state = self.get_user_state(update.effective_user.id)
        if user_state['step'] != 'caption_entered':
            await update.message.reply_text("❌ Неверный шаг. Начните с /start")
            return
        
        # Ask for time input
        user_state['step'] = 'scheduling'
        await update.message.reply_text(
            "⏰ <b>Планирование публикации</b>\n\n"
            "Отправьте время в формате:\n"
            "• <code>HH:MM</code> - сегодня в указанное время\n"
            "• <code>DD.MM HH:MM</code> - в указанную дату и время\n"
            "• <code>+N</code> - через N минут\n\n"
            "Примеры:\n"
            "• <code>15:30</code> - сегодня в 15:30\n"
            "• <code>25.12 10:00</code> - 25 декабря в 10:00\n"
            "• <code>+30</code> - через 30 минут",
            parse_mode='HTML'
        )

    async def handle_time_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle time input for scheduling."""
        if not self.is_admin(update.effective_user.id):
            await update.message.reply_text(MESSAGES['unauthorized'])
            return
        
        user_state = self.get_user_state(update.effective_user.id)
        if user_state['step'] != 'scheduling':
            await update.message.reply_text("❌ Неверный шаг.")
            return
        
        time_input = update.message.text.strip()
        scheduled_time = None
        
        try:
            now = datetime.now()
            
            if time_input.startswith('+'):
                # Relative time (e.g., +30)
                minutes = int(time_input[1:])
                scheduled_time = now + timedelta(minutes=minutes)
            elif '.' in time_input:
                # Date and time (e.g., 25.12 10:00)
                date_part, time_part = time_input.split()
                day, month = map(int, date_part.split('.'))
                hour, minute = map(int, time_part.split(':'))
                scheduled_time = now.replace(month=month, day=day, hour=hour, minute=minute, second=0, microsecond=0)
            else:
                # Time only (e.g., 15:30)
                hour, minute = map(int, time_input.split(':'))
                scheduled_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                # If time has passed today, schedule for tomorrow
                if scheduled_time <= now:
                    scheduled_time += timedelta(days=1)
            
            if scheduled_time <= now:
                await update.message.reply_text("❌ Время должно быть в будущем!")
                return
            
            user_state['scheduled_time'] = scheduled_time
            user_state['step'] = 'scheduled'
            
            # Show confirmation with cancel button
            time_str = scheduled_time.strftime("%d.%m.%Y в %H:%M")
            keyboard = [
                [KeyboardButton("❌ Отмена")],
            ]
            cancel_keyboard = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            
            await update.message.reply_text(
                f"⏰ <b>Публикация запланирована на {time_str}</b>\n\n"
                f"Пост будет опубликован автоматически. "
                f"Вы можете отменить планирование кнопкой ниже или командой /cancel",
                parse_mode='HTML',
                reply_markup=cancel_keyboard
            )
            
            # Schedule the post
            await self._schedule_post(update, context, user_state, scheduled_time)
            
        except Exception as e:
            logger.error(f"Error parsing time: {e}")
            await update.message.reply_text(
                "❌ Неверный формат времени!\n\n"
                "Используйте:\n"
                "• <code>HH:MM</code> - сегодня в указанное время\n"
                "• <code>DD.MM HH:MM</code> - в указанную дату и время\n"
                "• <code>+N</code> - через N минут",
                parse_mode='HTML'
            )

    async def _schedule_post(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_state: Dict, scheduled_time: datetime) -> None:
        """Schedule a post for later publishing."""
        try:
            # Calculate delay
            delay = (scheduled_time - datetime.now()).total_seconds()
            
            if delay <= 0:
                await update.message.reply_text("❌ Время должно быть в будущем!")
                return
            
            # Create task
            task = asyncio.create_task(self._delayed_publish(update, context, user_state, delay))
            
            # Store scheduled post
            self.scheduled_posts[update.effective_user.id] = {
                'task': task,
                'post_data': {
                    'photos': list(user_state['photos']),
                    'caption': user_state.get('caption', ''),
                    'target_platform': user_state['target_platform'],
                    'scheduled_time': scheduled_time
                }
            }
            
            logger.info(f"Post scheduled for {scheduled_time} (delay: {delay}s)")
            
        except Exception as e:
            logger.error(f"Error scheduling post: {e}")
            await update.message.reply_text(f"❌ Ошибка планирования: {e}")

    async def _delayed_publish(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_state: Dict, delay: float) -> None:
        """Delayed publishing function."""
        try:
            # Wait for the scheduled time
            await asyncio.sleep(delay)
            
            # Check if cancelled before publishing
            if user_state.get('cancelled', False):
                logger.info("Scheduled post was cancelled before publishing")
                return
            
            # Process and publish
            await self._process_and_publish(update, context, user_state, immediate=False)
            
        except asyncio.CancelledError:
            logger.info("Scheduled post was cancelled")
        except Exception as e:
            logger.error(f"Error in delayed publish: {e}")
            # Try to notify user about the error
            try:
                await self.telegram_service.send_error_notification(
                    update.effective_user.id, 
                    f"Ошибка при публикации запланированного поста: {e}"
                )
            except Exception:
                pass

    async def _process_and_publish(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_state: Dict, immediate: bool = True) -> None:
        """Process photos and publish to selected platforms."""
        try:
            # Get caption from user state or pending posts
            caption = user_state.get('caption', '')
            if not caption and update.effective_user.id in self.pending_posts:
                caption = self.pending_posts[update.effective_user.id]['caption']
            
            if not caption:
                await update.message.reply_text("❌ Подпись не найдена!")
                return
            
            # Show processing message
            processing_msg = await update.message.reply_text("⏳ Обрабатываю и публикую пост...")
            
            # Check if cancelled before processing
            if user_state.get('cancelled', False):
                await processing_msg.edit_text("❌ Операция отменена.")
                return
            
            # Get article numbers from user state (already found during photo upload)
            article_numbers = user_state.get('article_numbers', [])
            
            # Process photos
            processing_msg = await processing_msg.edit_text("📸 Обрабатываю фотографии...")
            
            # Check if cancelled before photo processing
            if user_state.get('cancelled', False):
                await processing_msg.edit_text("❌ Операция отменена.")
                return
            
            processed_photos = self.image_processor.process_photos(user_state['photos'])
            target_size = self.image_processor.determine_image_format(processed_photos)
            final_photos = [self.image_processor.resize_image(p, target_size) for p in processed_photos]
            
            # Check if cancelled after photo processing
            if user_state.get('cancelled', False):
                await processing_msg.edit_text("❌ Операция отменена.")
                # Cleanup processed photos
                self.image_processor.cleanup_files(final_photos)
                return
            
            # Add article numbers to caption
            if article_numbers:
                articles_text = self.image_processor.format_articles_for_caption(article_numbers)
                enhanced_caption = f"{caption}\n\n{articles_text}"
                logger.info(f"Enhanced caption with articles: {enhanced_caption}")
            else:
                enhanced_caption = caption
                # Only warn if user expected articles (check_articles=True) but none were found
                if user_state.get('check_articles', False):
                    logger.warning("No article numbers found despite check_articles=True, using original caption")
                else:
                    logger.info("Using original caption without article numbers (check_articles=False)")
            
            # Check if cancelled before publishing
            if user_state.get('cancelled', False):
                await processing_msg.edit_text("❌ Операция отменена.")
                # Cleanup processed photos
                self.image_processor.cleanup_files(final_photos)
                return
            
            # Publish to selected platforms
            instagram_success = False
            telegram_success = False
            vk_success = False
            
            if user_state['target_platform'] in ['instagram', 'both', 'all']:
                # Check if cancelled before Instagram publishing
                if user_state.get('cancelled', False):
                    await processing_msg.edit_text("❌ Операция отменена.")
                    self.image_processor.cleanup_files(final_photos)
                    return
                instagram_success = self.instagram_service.create_draft_with_music_instructions(final_photos, enhanced_caption)
            
            if user_state['target_platform'] in ['telegram', 'both', 'all']:
                # Check if cancelled before Telegram publishing
                if user_state.get('cancelled', False):
                    await processing_msg.edit_text("❌ Операция отменена.")
                    self.image_processor.cleanup_files(final_photos)
                    return
                telegram_success = await self.telegram_service.post_to_telegram(final_photos, enhanced_caption)
            
            if user_state['target_platform'] in ['vk', 'all']:
                # Check if cancelled before VK publishing
                if user_state.get('cancelled', False):
                    await processing_msg.edit_text("❌ Операция отменена.")
                    self.image_processor.cleanup_files(final_photos)
                    return
                vk_success = await self.vk_service.post_to_vk(final_photos, enhanced_caption)
            
            # Send results
            if immediate:
                article_info = f"\n\n📋 Найдено артикулов: {len(article_numbers)}" if article_numbers else "\n\n📋 Артикулы не найдены"
                
                # Build success message based on which platforms succeeded
                success_platforms = []
                if instagram_success:
                    success_platforms.append('Instagram')
                if telegram_success:
                    success_platforms.append('Telegram')
                if vk_success:
                    success_platforms.append('VK')
                
                if success_platforms:
                    platforms_text = ', '.join(success_platforms)
                    message = f"✅ Пост опубликован в {platforms_text}!{article_info}"
                    if instagram_success:
                        message += "\n\n🎵 ВАЖНО: Зайдите в Instagram и добавьте новогоднюю музыку к посту!"
                    await processing_msg.edit_text(message)
                else:
                    await processing_msg.edit_text(f"❌ Не удалось опубликовать пост ни на одной платформе.{article_info}")
            else:
                # Scheduled post results
                success_platforms = []
                if instagram_success:
                    success_platforms.append('Instagram')
                if telegram_success:
                    success_platforms.append('Telegram')
                if vk_success:
                    success_platforms.append('VK')
                
                if success_platforms:
                    platforms_text = ', '.join(success_platforms)
                    message = f"✅ Запланированный пост опубликован в {platforms_text}!"
                    if instagram_success:
                        message += "\n\n🎵 ВАЖНО: Зайдите в Instagram и добавьте новогоднюю музыку к посту!"
                    await self.telegram_service.send_notification(update.effective_user.id, message)
                else:
                    await self.telegram_service.send_error_notification(update.effective_user.id, "Не удалось опубликовать запланированный пост")
            
            # Cleanup
            self.image_processor.cleanup_files(final_photos)
            self.clear_user_state(update.effective_user.id)
            
            # Remove from scheduled posts
            if update.effective_user.id in self.scheduled_posts:
                del self.scheduled_posts[update.effective_user.id]
            
        except Exception as e:
            logger.error(f"Error processing and publishing: {e}")
            await update.message.reply_text(f"❌ Ошибка публикации: {e}")
            self.clear_user_state(update.effective_user.id)

    async def _show_preview_with_caption(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_state: Dict, caption: str) -> None:
        """Show preview with given caption and ask for scheduling."""
        try:
            # Prepare full caption with articles for preview
            article_numbers = user_state.get('article_numbers', [])
            if article_numbers:
                articles_text = self.image_processor.format_articles_for_caption(article_numbers)
                full_caption = f"{caption}\n\n{articles_text}"
            else:
                full_caption = caption
            
            if len(user_state['photos']) == 1:
                with open(user_state['photos'][0], 'rb') as f:
                    preview_msg = await update.message.reply_photo(
                        photo=f,
                        caption=f"<b>Предпросмотр поста:</b>\n\n{full_caption}",
                        parse_mode='HTML'
                    )
            else:
                media = []
                for i, p in enumerate(user_state['photos']):
                    with open(p, 'rb') as f:
                        media.append(InputMediaPhoto(media=f, caption=f"<b>Предпросмотр поста:</b>\n\n{full_caption}" if i == 0 else None, parse_mode='HTML'))
                preview_group = await update.message.reply_media_group(media=media)
                preview_msg = preview_group[0] if preview_group else None
            
            # Ask for scheduling
            platform_text = {
                'instagram': 'Instagram',
                'telegram': 'Telegram',
                'vk': 'VK',
                'both': 'Instagram и Telegram',
                'all': 'Instagram, Telegram и VK'
            }.get(user_state['target_platform'], 'неизвестно')
            
            # Add article information to preview message
            article_numbers = user_state.get('article_numbers', [])
            article_info = ""
            if article_numbers:
                article_info = f"\n<b>Найдено артикулов:</b> {len(article_numbers)} ({', '.join(article_numbers)})"
            else:
                article_info = "\n<b>Артикулы:</b> не найдены"
            
            message = f"""📋 <b>Предпросмотр готов!</b>

<b>Платформа:</b> {platform_text}
<b>Тип поста:</b> {'одиночный' if user_state['post_mode'] == 'single' else 'массовый'}
<b>Количество фото:</b> {len(user_state['photos'])}{article_info}

<b>Шаг 4:</b> Выберите время публикации:"""
            
            await update.message.reply_text(message, parse_mode='HTML', reply_markup=self.get_schedule_keyboard())
            
        except Exception as e:
            logger.error(f"Error showing preview: {e}")
            await update.message.reply_text(f"Ошибка показа превью: {e}")

    async def on_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle approve/reject/cancel callbacks."""
        if not update.callback_query:
            return
        cq = update.callback_query
        await cq.answer()
        user_id = cq.from_user.id
        if not self.is_admin(user_id):
            await cq.edit_message_text(MESSAGES['unauthorized'])
            return
        
        # Handle cancel download callback
        if cq.data == 'cancel_download':
            await self.handle_cancel_download(update, context)
            return
        
        pending = self.pending_posts.get(user_id)
        if not pending:
            await cq.edit_message_text("Нет ожидающих публикаций.")
            return
        if cq.data == 'reject':
            # Cleanup
            self.image_processor.cleanup_files(pending['photos'])
            self.pending_posts.pop(user_id, None)
            self.clear_user_state(user_id)
            await cq.edit_message_text("❌ Публикация отменена.")
            return
        if cq.data == 'approve':
            # Proceed to processing and posting
            photos = pending['photos']
            caption = pending['caption']
            target_platform = pending.get('target_platform', 'both')
            try:
                processed_photos = self.image_processor.process_photos(photos)
                target_size = self.image_processor.determine_image_format(processed_photos)
                final_photos = [self.image_processor.resize_image(p, target_size) for p in processed_photos]
                ig_ok = False
                tg_ok = False
                vk_ok = False
                if target_platform in ('instagram', 'both', 'all'):
                    ig_ok = self.instagram_service.post_to_instagram(final_photos, caption)
                if target_platform in ('telegram', 'both', 'all'):
                    tg_ok = await self.telegram_service.post_to_telegram(final_photos, caption)
                if target_platform in ('vk', 'all'):
                    vk_ok = await self.vk_service.post_to_vk(final_photos, caption)
                
                # Build success message
                success_platforms = []
                if ig_ok:
                    success_platforms.append('Instagram')
                if tg_ok:
                    success_platforms.append('Telegram')
                if vk_ok:
                    success_platforms.append('VK')
                
                if success_platforms:
                    platforms_text = ', '.join(success_platforms)
                    await cq.edit_message_text(f"✅ Опубликовано в {platforms_text}!")
                else:
                    await cq.edit_message_text("❌ Не удалось опубликовать пост ни на одной платформе.")
            except Exception as e:
                logger.error(f"Error during approve flow: {e}")
                await cq.edit_message_text(f"Ошибка публикации: {e}")
            finally:
                try:
                    self.image_processor.cleanup_files(final_photos if 'final_photos' in locals() else photos)
                except Exception:
                    pass
                self.pending_posts.pop(user_id, None)
                self.clear_user_state(user_id)
    
    async def handle_cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle cancel command from admin.
        
        Args:
            update: Telegram update object
            context: Bot context
        """
        if not self.is_admin(update.effective_user.id):
            await update.message.reply_text(MESSAGES['unauthorized'])
            return
        
        user_id = update.effective_user.id
        
        # Cancel scheduled posts if any
        if user_id in self.scheduled_posts:
            try:
                self.scheduled_posts[user_id]['task'].cancel()
                del self.scheduled_posts[user_id]
                await update.message.reply_text(MESSAGES['cancelled_scheduled'])
            except Exception as e:
                logger.error(f"Error cancelling scheduled post: {e}")
        
        # Clear user state
        self.clear_user_state(user_id)
        await update.message.reply_text(MESSAGES['cancelled'], reply_markup=self.get_main_keyboard())
    
    async def handle_cancel_button(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle cancel button from any stage of the process.
        
        Args:
            update: Telegram update object
            context: Bot context
        """
        if not self.is_admin(update.effective_user.id):
            await update.message.reply_text(MESSAGES['unauthorized'])
            return
        
        user_id = update.effective_user.id
        user_state = self.get_user_state(user_id)
        
        # Get current step for logging
        current_step = user_state.get('step', 'start')
        logger.info(f"User {user_id} cancelled operation at step: {current_step}")
        
        # Cancel scheduled posts if any
        if user_id in self.scheduled_posts:
            try:
                self.scheduled_posts[user_id]['task'].cancel()
                del self.scheduled_posts[user_id]
                await update.message.reply_text(MESSAGES['cancelled_scheduled'])
            except Exception as e:
                logger.error(f"Error cancelling scheduled post: {e}")
        
        # Set cancelled flag before clearing state
        user_state['cancelled'] = True
        
        # Clear user state and cleanup files
        self.clear_user_state(user_id)
        
        # Send cancellation message based on current step
        step_messages = {
            'start': "❌ Операция отменена.",
            'type_selection': "❌ Выбор типа поста отменен.",
            'platform_selection': "❌ Выбор платформы отменен.",
            'article_check_selection': "❌ Выбор проверки артикулов отменен.",
            'photos_upload': "❌ Загрузка фото отменена.",
            'photos_uploaded': "❌ Обработка фото отменена.",
            'caption_entered': "❌ Публикация отменена.",
            'preview_shown': "❌ Превью отменено.",
            'scheduling': "❌ Планирование отменено.",
            'scheduled': "❌ Запланированная публикация отменена.",
        }
        
        # Get additional info for scheduled posts
        additional_info = ""
        if current_step == 'scheduled' and user_id in self.scheduled_posts:
            scheduled_time = self.scheduled_posts[user_id]['post_data']['scheduled_time']
            additional_info = f"\n\n⏰ Запланированное время: {scheduled_time.strftime('%d.%m.%Y в %H:%M')}"
        
        cancel_message = step_messages.get(current_step, "❌ Операция отменена.")
        await update.message.reply_text(
            f"{cancel_message}{additional_info}\n\n{MESSAGES['cancelled']}", 
            reply_markup=self.get_main_keyboard()
        )
    
    async def handle_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle status command from admin.
        
        Args:
            update: Telegram update object
            context: Bot context
        """
        if not self.is_admin(update.effective_user.id):
            await update.message.reply_text(MESSAGES['unauthorized'])
            return
        
        try:
            # Check Instagram status
            instagram_status = "✅ Подключено" if self.instagram_service.is_logged_in() else "❌ Нет подключения"
            
            # Check Telegram status
            telegram_status = "✅ Подключено" if await self.telegram_service.test_connection() else "❌ Нет подключения"
            
            # Check VK status
            vk_status = "✅ Подключено" if self.vk_service.test_connection() else "❌ Нет подключения"
            
            # Check AI service status
            ai_status = "✅ Подключено" if self.ai_service.enabled and await self.ai_service.test_connection() else "❌ Нет подключения"
            
            # Get user state
            user_state = self.get_user_state(update.effective_user.id)
            step_names = {
                'start': 'Начало',
                'type_selection': 'Выбор типа',
                'platform_selection': 'Выбор платформы',
                'article_check_selection': 'Выбор проверки артикулов',
                'photos_upload': 'Загрузка фото',
                'photos_uploaded': 'Фото загружены',
                'caption_entered': 'Подпись введена',
                'preview_shown': 'Превью показано',
                'scheduling': 'Планирование',
                'scheduled': 'Запланировано'
            }
            
            state_info = (
                f"Шаг: {step_names.get(user_state.get('step', 'start'), 'Неизвестно')}, "
                f"Фото: {len(user_state['photos'])}, "
                f"Режим: {user_state.get('post_mode','auto')}, "
                f"Цель: {user_state.get('target_platform','both')}, "
                f"Артикулы: {'включен' if user_state.get('check_articles', True) else 'отключен'}"
            )
            
            # Check for scheduled posts
            scheduled_info = ""
            if update.effective_user.id in self.scheduled_posts:
                scheduled_time = self.scheduled_posts[update.effective_user.id]['post_data']['scheduled_time']
                scheduled_info = f"\n⏰ <b>Запланированная публикация:</b> {scheduled_time.strftime('%d.%m.%Y в %H:%M')}"
            
            status_message = f"""🤖 <b>Статус бота</b>

📸 <b>Instagram:</b> {instagram_status}
💬 <b>Telegram:</b> {telegram_status}
🔵 <b>VK:</b> {vk_status}
🤖 <b>ИИ сервис:</b> {ai_status}

👤 <b>Ваше состояние:</b> {state_info}{scheduled_info}

<b>Команды:</b>
/cancel - очистить состояние
/reset - сбросить Instagram сессию"""
            
            # Create keyboard with reset button
            keyboard = [
                [KeyboardButton("🔄 Reset Instagram"), KeyboardButton("🚀 Начать публикацию")],
                [KeyboardButton("✅ Status"), KeyboardButton("❌ Cancel")],
                [KeyboardButton("ℹ️ Help")],
            ]
            status_keyboard = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            
            await update.message.reply_text(status_message, parse_mode='HTML', reply_markup=status_keyboard)
            
        except Exception as e:
            logger.error(f"Error getting status: {e}")
            await update.message.reply_text(f"Ошибка получения статуса: {str(e)}")
    
    async def handle_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle help command from admin.
        
        Args:
            update: Telegram update object
            context: Bot context
        """
        if not self.is_admin(update.effective_user.id):
            await update.message.reply_text(MESSAGES['unauthorized'])
            return
        
        help_message = """🤖 <b>Помощь - Автопостер с умным определением</b>

<b>📋 Автоматическая публикация:</b>
1. ➕ Нажмите "Добавить ссылку"
2. 📎 Отправьте ссылку на пост/рилс из Instagram
3. ✅ Пост добавится в очередь
4. ⏰ Будет опубликован автоматически в расписанное время

<b>🚀 Ручная публикация (УПРОЩЁННАЯ!):</b>
1. 🚀 Нажмите "Начать публикацию"
2. 📱 Выберите платформу (Instagram/Telegram/VK/Все)
3. 🔍 Выберите поиск артикулов (Да/Нет)
4. 📤 Отправьте ЛЮБОЙ контент:
   • 📷 Фото (одно или несколько)
   • 📹 Видео файл
   • 🔗 Ссылку на Instagram рилс
5. 📝 Отправьте подпись к посту
6. 🤖 Используйте "Помощь ИИ" для улучшения
7. ⏰ Выберите время (сейчас/запланировать)

<b>✨ Автоопределение типа:</b>
Бот сам определит что вы отправили:
• Фото → пост с фотографиями
• Видео → видео пост
• Ссылка /reel/ → скачает рилс
Больше не нужно выбирать тип!

<b>⏰ Расписание публикаций:</b>
Фиксированные часы: 8, 10, 12, 14, 16, 18, 20, 22
Раз в 2 часа публикуется один пост из очереди

<b>📋 Управление очередью:</b>
/add_link — добавить ссылку
/queue — посмотреть очередь
📋 Очередь постов — просмотр
🗑️ Очистить опубликованные
❌ Очистить все

<b>🛠️ Основные команды:</b>
/start — запуск
/help — помощь
/status — статус бота
/cancel — отмена
/reset — сброс Instagram сессии

<b>📝 Планирование разовых постов:</b>
• <code>HH:MM</code> - сегодня в указанное время
• <code>DD.MM HH:MM</code> - в указанную дату и время
• <code>+N</code> - через N минут

<b>🤖 ИИ помощь:</b>
• Улучшает описания постов
• Добавляет эмодзи и хештеги
• Адаптирует стиль под платформу
• Требует настройки GOOGLE_API_KEY

<b>📌 Примечания:</b>
• Автоопределение типа контента
• Очередь сохраняется при перезапуске
• Фото автоматически обрабатываются
• Поддержка фото, видео и рилсов
• Доступ только у администратора

📖 Подробнее: см. SCHEDULER_GUIDE.md"""
        
        await update.message.reply_text(help_message, parse_mode='HTML', reply_markup=self.get_main_keyboard())

    async def handle_type_single(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle single post type selection."""
        if not self.is_admin(update.effective_user.id):
            await update.message.reply_text(MESSAGES['unauthorized'])
            return
        
        user_state = self.get_user_state(update.effective_user.id)
        if user_state['step'] != 'type_selection':
            await update.message.reply_text("❌ Неверный шаг. Начните с /start")
            return
        
        user_state['post_mode'] = 'single'
        user_state['step'] = 'platform_selection'
        
        message = """📷 <b>Одиночный пост выбран</b>

<b>Шаг 2:</b> Выберите платформу для публикации:

📷 <b>Instagram</b> - только Instagram
💬 <b>Telegram</b> - только Telegram группа  
🔀 <b>Обе платформы</b> - Instagram + Telegram"""
        
        await update.message.reply_text(message, parse_mode='HTML', reply_markup=self.get_platform_selection_keyboard())

    async def handle_type_multi(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle multi post type selection."""
        if not self.is_admin(update.effective_user.id):
            await update.message.reply_text(MESSAGES['unauthorized'])
            return
        
        user_state = self.get_user_state(update.effective_user.id)
        if user_state['step'] != 'type_selection':
            await update.message.reply_text("❌ Неверный шаг. Начните с /start")
            return
        
        user_state['post_mode'] = 'multi'
        user_state['step'] = 'platform_selection'
        
        message = """📸 <b>Массовый пост выбран</b>

<b>Шаг 2:</b> Выберите платформу для публикации:

📷 <b>Instagram</b> - только Instagram
💬 <b>Telegram</b> - только Telegram группа  
🔀 <b>Обе платформы</b> - Instagram + Telegram"""
        
        await update.message.reply_text(message, parse_mode='HTML', reply_markup=self.get_platform_selection_keyboard())

    async def handle_mode_single(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Switch to single-post mode (only one photo)."""
        if not self.is_admin(update.effective_user.id):
            await update.message.reply_text(MESSAGES['unauthorized'])
            return
        state = self.get_user_state(update.effective_user.id)
        state['post_mode'] = 'single'
        # If there are more than one photo collected, keep only the last one
        if len(state['photos']) > 1:
            self.image_processor.cleanup_files(state['photos'][:-1])
            state['photos'] = state['photos'][-1:]
        await update.message.reply_text("Режим: одиночный пост. Будет использовано только одно фото.")

    async def handle_mode_multi(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Switch to multi-post mode (allow multiple photos)."""
        if not self.is_admin(update.effective_user.id):
            await update.message.reply_text(MESSAGES['unauthorized'])
            return
        state = self.get_user_state(update.effective_user.id)
        state['post_mode'] = 'multi'
        await update.message.reply_text("Режим: массовый пост. Можно отправить 2–10 фото перед подписью.")
    
    async def handle_start_publication(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle start publication process with auto-detection.
        
        Args:
            update: Telegram update object
            context: Bot context
        """
        if not self.is_admin(update.effective_user.id):
            await update.message.reply_text(MESSAGES['unauthorized'])
            return
        
        # Clear any existing state
        self.clear_user_state(update.effective_user.id)
        
        # Start the business process - go straight to platform selection
        user_state = self.get_user_state(update.effective_user.id)
        user_state['step'] = 'platform_selection'
        user_state['post_mode'] = 'auto'  # Auto-detect mode
        
        message = """🚀 <b>Начинаем процесс публикации</b>

<b>Шаг 1:</b> Выберите платформу для публикации:

📷 <b>Instagram</b> - только Instagram
💬 <b>Telegram</b> - только Telegram группа
🔵 <b>VK</b> - только VK группа
🔀 <b>Все платформы</b> - Instagram + Telegram + VK

<i>💡 После выбора платформы отправьте:</i>
• Фото (одно или несколько)
• Видео
• Ссылку на Instagram пост/рилс

<i>Бот автоматически определит тип контента!</i>"""
        
        await update.message.reply_text(message, parse_mode='HTML', reply_markup=self.get_platform_selection_keyboard())

    async def handle_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle start command from admin.
        
        Args:
            update: Telegram update object
            context: Bot context
        """
        if not self.is_admin(update.effective_user.id):
            await update.message.reply_text(MESSAGES['unauthorized'])
            return
        
        await update.message.reply_text(MESSAGES['welcome'], reply_markup=self.get_main_keyboard())

    # Button handlers (map buttons to existing commands)
    async def handle_btn_single(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await self.handle_mode_single(update, context)

    async def handle_btn_multi(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await self.handle_mode_multi(update, context)

    async def handle_btn_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await self.handle_status(update, context)

    async def handle_btn_cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await self.handle_cancel(update, context)

    async def handle_btn_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await self.handle_help(update, context)
    
    async def handle_reset_instagram(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle Instagram session reset.
        Removes old session and creates a new one.
        
        Args:
            update: Telegram update object
            context: Bot context
        """
        if not self.is_admin(update.effective_user.id):
            await update.message.reply_text(MESSAGES['unauthorized'])
            return
        
        try:
            processing_msg = await update.message.reply_text(
                "🔄 <b>Сбрасываю Instagram сессию...</b>\n\n"
                "Шаг 1/3: Удаление старой сессии...",
                parse_mode='HTML'
            )
            
            # Use the new reset_session method from InstagramService
            import asyncio
            
            # Update message
            await processing_msg.edit_text(
                "🔄 <b>Сбрасываю Instagram сессию...</b>\n\n"
                "✅ Шаг 1/3: Старая сессия удалена\n"
                "⏳ Шаг 2/3: Пересоздание клиента...",
                parse_mode='HTML'
            )
            
            # Small delay to show progress
            await asyncio.sleep(0.5)
            
            # Update message
            await processing_msg.edit_text(
                "🔄 <b>Сбрасываю Instagram сессию...</b>\n\n"
                "✅ Шаг 1/3: Старая сессия удалена\n"
                "✅ Шаг 2/3: Клиент пересоздан\n"
                "⏳ Шаг 3/3: Новая авторизация...",
                parse_mode='HTML'
            )
            
            # Reset session using the service method
            reset_success = self.instagram_service.reset_session()
            
            if reset_success:
                # Verify login
                if self.instagram_service.is_logged_in():
                    await processing_msg.edit_text(
                        "✅ <b>Instagram сессия успешно обновлена!</b>\n\n"
                        "✅ Шаг 1/3: Старая сессия удалена\n"
                        "✅ Шаг 2/3: Клиент пересоздан\n"
                        "✅ Шаг 3/3: Новая авторизация выполнена\n\n"
                        "📸 <b>Статус:</b> Подключено\n"
                        "🔐 <b>Сессия:</b> Создана заново\n"
                        "📁 <b>Файл:</b> session.json обновлен\n\n"
                        "Теперь можете использовать бота для публикации! 🎉",
                        parse_mode='HTML'
                    )
                    logger.info("Instagram session reset successful")
                else:
                    await processing_msg.edit_text(
                        "⚠️ <b>Вход выполнен, но сессия не валидна</b>\n\n"
                        "Возможные причины:\n"
                        "• Instagram требует подтверждение\n"
                        "• Аккаунт временно заблокирован\n"
                        "• Проблемы с учетными данными\n\n"
                        "<b>Что делать:</b>\n"
                        "1. Проверьте настройки в .env файле\n"
                        "2. Войдите в Instagram вручную и пройдите подтверждение\n"
                        "3. Попробуйте /reset еще раз",
                        parse_mode='HTML'
                    )
            else:
                await processing_msg.edit_text(
                    "❌ <b>Не удалось создать новую сессию</b>\n\n"
                    "Возможные причины:\n"
                    "• Неверные учетные данные (USERNAME/PASSWORD)\n"
                    "• Instagram требует подтверждение (SMS/Email)\n"
                    "• Аккаунт заблокирован или ограничен\n"
                    "• Instagram API временно недоступен\n\n"
                    "<b>Решения:</b>\n"
                    "1. Проверьте INSTAGRAM_USERNAME и INSTAGRAM_PASSWORD в .env\n"
                    "2. Используйте INSTAGRAM_SESSIONID вместо пароля\n"
                    "3. Войдите в Instagram вручную и пройдите проверку\n"
                    "4. Подождите 30 минут и попробуйте снова\n\n"
                    "📚 Подробнее: см. INSTAGRAM_403_FIX.md",
                    parse_mode='HTML'
                )
                logger.error("Instagram session reset failed - login unsuccessful")
                
        except Exception as e:
            logger.error(f"Error resetting Instagram session: {e}")
            await update.message.reply_text(
                f"❌ <b>Критическая ошибка при сбросе сессии:</b>\n\n"
                f"<code>{str(e)}</code>\n\n"
                "<b>Решение:</b>\n"
                "1. Перезапустите бота вручную (Ctrl+C → python main.py)\n"
                "2. Проверьте логи для подробностей\n"
                "3. Убедитесь, что файл sessions/session.json доступен для записи",
                parse_mode='HTML'
            )

    async def handle_platform_instagram(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle Instagram platform selection."""
        if not self.is_admin(update.effective_user.id):
            await update.message.reply_text(MESSAGES['unauthorized'])
            return
        
        user_state = self.get_user_state(update.effective_user.id)
        if user_state['step'] != 'platform_selection':
            await update.message.reply_text("❌ Неверный шаг. Начните с /start")
            return
        
        user_state['target_platform'] = 'instagram'
        user_state['step'] = 'article_check_selection'
        
        message = """📷 <b>Instagram выбран</b>

<b>Шаг 2:</b> Нужно ли искать артикулы на фотографиях?

🔍 <b>Да, искать артикулы</b> - бот автоматически найдет номера товаров и добавит их в пост
⏭️ <b>Нет, пропустить</b> - загрузить без поиска артикулов

<i>💡 На следующем шаге отправьте:</i>
• Фото (одно или несколько до 10)
• Видео файл
• Ссылку на Instagram пост/рилс"""
        
        await update.message.reply_text(message, parse_mode='HTML', reply_markup=self.get_article_check_keyboard())

    async def handle_platform_telegram(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle Telegram platform selection."""
        if not self.is_admin(update.effective_user.id):
            await update.message.reply_text(MESSAGES['unauthorized'])
            return
        
        user_state = self.get_user_state(update.effective_user.id)
        if user_state['step'] != 'platform_selection':
            await update.message.reply_text("❌ Неверный шаг. Начните с /start")
            return
        
        user_state['target_platform'] = 'telegram'
        user_state['step'] = 'article_check_selection'
        
        message = """💬 <b>Telegram выбран</b>

<b>Шаг 2:</b> Нужно ли искать артикулы на фотографиях?

🔍 <b>Да, искать артикулы</b> - бот автоматически найдет номера товаров и добавит их в пост
⏭️ <b>Нет, пропустить</b> - загрузить без поиска артикулов

<i>💡 На следующем шаге отправьте:</i>
• Фото (одно или несколько до 10)
• Видео файл
• Ссылку на Instagram пост/рилс"""
        
        await update.message.reply_text(message, parse_mode='HTML', reply_markup=self.get_article_check_keyboard())

    async def handle_platform_vk(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle VK platform selection."""
        if not self.is_admin(update.effective_user.id):
            await update.message.reply_text(MESSAGES['unauthorized'])
            return
        
        user_state = self.get_user_state(update.effective_user.id)
        if user_state['step'] != 'platform_selection':
            await update.message.reply_text("❌ Неверный шаг. Начните с /start")
            return
        
        user_state['target_platform'] = 'vk'
        user_state['step'] = 'article_check_selection'
        
        message = """🔵 <b>VK выбран</b>

<b>Шаг 2:</b> Нужно ли искать артикулы на фотографиях?

🔍 <b>Да, искать артикулы</b> - бот автоматически найдет номера товаров и добавит их в пост
⏭️ <b>Нет, пропустить</b> - загрузить без поиска артикулов

<i>💡 На следующем шаге отправьте:</i>
• Фото (одно или несколько до 10)
• Видео файл
• Ссылку на Instagram пост/рилс"""
        
        await update.message.reply_text(message, parse_mode='HTML', reply_markup=self.get_article_check_keyboard())

    async def handle_platform_both(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle all platforms selection."""
        if not self.is_admin(update.effective_user.id):
            await update.message.reply_text(MESSAGES['unauthorized'])
            return
        
        user_state = self.get_user_state(update.effective_user.id)
        if user_state['step'] != 'platform_selection':
            await update.message.reply_text("❌ Неверный шаг. Начните с /start")
            return
        
        user_state['target_platform'] = 'all'
        user_state['step'] = 'article_check_selection'
        
        message = """🔀 <b>Все платформы выбраны</b>

<b>Шаг 2:</b> Нужно ли искать артикулы на фотографиях?

🔍 <b>Да, искать артикулы</b> - бот автоматически найдет номера товаров и добавит их в пост
⏭️ <b>Нет, пропустить</b> - загрузить без поиска артикулов

<i>💡 На следующем шаге отправьте:</i>
• Фото (одно или несколько до 10)
• Видео файл
• Ссылку на Instagram пост/рилс"""
        
        await update.message.reply_text(message, parse_mode='HTML', reply_markup=self.get_article_check_keyboard())

    async def handle_article_check_yes(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle article check selection - yes."""
        if not self.is_admin(update.effective_user.id):
            await update.message.reply_text(MESSAGES['unauthorized'])
            return
        
        user_state = self.get_user_state(update.effective_user.id)
        if user_state['step'] != 'article_check_selection':
            await update.message.reply_text("❌ Неверный шаг. Начните с /start")
            return
        
        user_state['check_articles'] = True
        user_state['step'] = 'content_input'
        
        platform_text = {
            'instagram': 'Instagram',
            'telegram': 'Telegram',
            'vk': 'VK',
            'both': 'Instagram и Telegram',
            'all': 'Instagram, Telegram и VK'
        }.get(user_state['target_platform'], 'неизвестно')
        
        message = f"""🔍 <b>Поиск артикулов включен</b>

<b>Шаг 3:</b> Отправьте контент для публикации

📱 <b>Платформа:</b> {platform_text}
🔍 <b>Поиск артикулов:</b> включен

📤 <b>Отправьте:</b>
• 📷 Фото (одно или несколько до 10)
• 📹 Видео файл
• 🔗 Ссылку на Instagram пост/рилс

<i>Бот автоматически определит тип контента!</i>"""
        
        await update.message.reply_text(message, parse_mode='HTML', reply_markup=self.get_content_input_keyboard())

    async def handle_article_check_no(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle article check selection - no."""
        if not self.is_admin(update.effective_user.id):
            await update.message.reply_text(MESSAGES['unauthorized'])
            return
        
        user_state = self.get_user_state(update.effective_user.id)
        if user_state['step'] != 'article_check_selection':
            await update.message.reply_text("❌ Неверный шаг. Начните с /start")
            return
        
        user_state['check_articles'] = False
        user_state['step'] = 'content_input'
        
        platform_text = {
            'instagram': 'Instagram',
            'telegram': 'Telegram',
            'vk': 'VK',
            'both': 'Instagram и Telegram',
            'all': 'Instagram, Telegram и VK'
        }.get(user_state['target_platform'], 'неизвестно')
        
        message = f"""⏭️ <b>Поиск артикулов пропущен</b>

<b>Шаг 3:</b> Отправьте контент для публикации

📱 <b>Платформа:</b> {platform_text}
🔍 <b>Поиск артикулов:</b> отключен

📤 <b>Отправьте:</b>
• 📷 Фото (одно или несколько до 10)
• 📹 Видео файл
• 🔗 Ссылку на Instagram пост/рилс

<i>Бот автоматически определит тип контента!</i>"""
        
        await update.message.reply_text(message, parse_mode='HTML', reply_markup=self.get_content_input_keyboard())
    
    async def handle_type_reels(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle reels type selection."""
        if not self.is_admin(update.effective_user.id):
            await update.message.reply_text(MESSAGES['unauthorized'])
            return
        
        user_state = self.get_user_state(update.effective_user.id)
        if user_state['step'] != 'type_selection':
            await update.message.reply_text("❌ Неверный шаг. Начните с /start")
            return
        
        user_state['post_mode'] = 'reels'
        user_state['step'] = 'platform_selection'
        
        message = """📹 <b>Публикация рилс выбрана</b>

<b>Шаг 2:</b> Выберите платформу для публикации:

📷 <b>Instagram</b> - публикация как обычный видео-пост
💬 <b>Telegram</b> - только Telegram группа  
🔵 <b>VK</b> - только VK группа
🔀 <b>Все платформы</b> - Instagram + Telegram + VK

<i>Примечание: В Instagram видео будет опубликовано как обычный пост, не как reels</i>"""
        
        # Use standard platform keyboard with Instagram option
        await update.message.reply_text(message, parse_mode='HTML', reply_markup=self.get_platform_selection_keyboard())
    
    async def handle_cancel_download(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle download cancellation via callback button."""
        query = update.callback_query
        await query.answer()
        
        user_id = update.effective_user.id
        user_state = self.get_user_state(user_id)
        
        # Set cancellation flag
        user_state['cancel_download'] = True
        
        await query.edit_message_text(
            "⏹️ <b>Отмена скачивания...</b>\n\n"
            "Ожидайте завершения текущего блока данных.",
            parse_mode='HTML'
        )
    
    async def handle_reels_url_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle reels URL input with progress tracking and cancellation."""
        user_id = update.effective_user.id
        
        if not self.is_admin(user_id):
            await update.message.reply_text(MESSAGES['unauthorized'])
            return
        
        user_state = self.get_user_state(user_id)
        
        # Check if we're waiting for URL
        if user_state['step'] != 'reels_url_input':
            return  # Not waiting for URL, ignore
        
        # Get URL from message
        reels_url = update.message.text.strip()
        
        # Validate URL
        if not ('instagram.com' in reels_url or 'instagr.am' in reels_url):
            await update.message.reply_text("❌ Неверная ссылка! Отправьте корректную ссылку на рилс из Instagram.")
            return
        
        user_state['reels_url'] = reels_url
        user_state['step'] = 'reels_download'
        user_state['cancel_download'] = False  # Reset cancel flag
        
        # Show processing message with cancel button
        cancel_keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("⏹️ Отменить", callback_data="cancel_download")
        ]])
        
        processing_msg = await update.message.reply_text(
            "⏳ <b>Скачиваю рилс из Instagram...</b>\n\n"
            "📊 Подготовка к скачиванию...",
            parse_mode='HTML',
            reply_markup=cancel_keyboard
        )
        
        last_update_time = [asyncio.get_event_loop().time()]  # Use list to allow modification in nested function
        
        # Progress callback
        async def progress_callback(downloaded: int, total: int):
            """Update progress message."""
            try:
                current_time = asyncio.get_event_loop().time()
                # Update only every 2 seconds to avoid rate limiting
                if current_time - last_update_time[0] >= 2:
                    downloaded_mb = downloaded / (1024 * 1024)
                    
                    if total > 0:
                        percent = (downloaded / total) * 100
                        total_mb = total / (1024 * 1024)
                        progress_bar = "█" * int(percent / 5) + "░" * (20 - int(percent / 5))
                        
                        logger.info(f"Progress update: {percent:.1f}% ({downloaded_mb:.2f}/{total_mb:.2f} MB)")
                        
                        await processing_msg.edit_text(
                            f"⏳ <b>Скачиваю рилс из Instagram...</b>\n\n"
                            f"📊 Прогресс: {percent:.1f}%\n"
                            f"[{progress_bar}]\n\n"
                            f"💾 Скачано: {downloaded_mb:.2f} МБ / {total_mb:.2f} МБ",
                            parse_mode='HTML',
                            reply_markup=cancel_keyboard
                        )
                    else:
                        # Total size unknown - show only downloaded
                        logger.info(f"Progress update: {downloaded_mb:.2f} MB downloaded (total size unknown)")
                        
                        await processing_msg.edit_text(
                            f"⏳ <b>Скачиваю рилс из Instagram...</b>\n\n"
                            f"📊 Скачивание...\n"
                            f"💾 Скачано: {downloaded_mb:.2f} МБ",
                            parse_mode='HTML',
                            reply_markup=cancel_keyboard
                        )
                    
                    last_update_time[0] = current_time
            except Exception as e:
                logger.error(f"Error updating progress UI: {e}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
        
        # Cancel check callback
        def cancel_check():
            """Check if download should be cancelled."""
            return user_state.get('cancel_download', False)
        
        # Download video
        video_path = None
        try:
            # Get event loop reference before entering executor
            main_loop = asyncio.get_event_loop()
            
            # Sync wrapper for progress callback (non-blocking)
            def sync_progress_callback(downloaded: int, total: int):
                """Non-blocking wrapper for async progress callback."""
                try:
                    # Use main loop reference (not get_event_loop() which won't work in thread)
                    asyncio.run_coroutine_threadsafe(
                        progress_callback(downloaded, total),
                        main_loop
                    )
                except Exception as e:
                    logger.error(f"Error in sync progress callback wrapper: {e}")
                    import traceback
                    logger.error(f"Traceback: {traceback.format_exc()}")
            
            logger.info(f"Starting reels download from: {reels_url}")
            
            # Download reels with progress and cancel callbacks
            video_path = await main_loop.run_in_executor(
                None,
                lambda: self.instagram_service.download_reels(
                    reels_url,
                    progress_callback=sync_progress_callback,
                    cancel_check=cancel_check
                )
            )
            
            logger.info(f"Download completed, video_path: {video_path}")
            
        except Exception as e:
            logger.error(f"Error downloading reels: {e}")
            await processing_msg.edit_text(
                f"❌ <b>Ошибка при скачивании рилса</b>\n\n"
                f"<code>{str(e)}</code>",
                parse_mode='HTML'
            )
            user_state['step'] = 'reels_url_input'
            return
        
        # Check if cancelled
        if user_state.get('cancel_download', False):
            await processing_msg.edit_text(
                "❌ <b>Скачивание отменено</b>\n\n"
                "Вы можете начать новую публикацию.",
                parse_mode='HTML'
            )
            user_state['step'] = 'start'
            user_state['cancel_download'] = False
            return
        
        if not video_path:
            await processing_msg.edit_text(
                "❌ <b>Не удалось скачать рилс</b>\n\n"
                "Проверьте ссылку и попробуйте снова.",
                parse_mode='HTML'
            )
            user_state['step'] = 'reels_url_input'
            return
        
        # Video downloaded successfully - update state FIRST
        user_state['reels_video_path'] = video_path
        user_state['step'] = 'reels_waiting_caption'
        
        # Show success message
        await processing_msg.edit_text(
            "✅ <b>Рилс успешно скачан!</b>\n\n"
            "Отправляю предпросмотр...",
            parse_mode='HTML'
        )
        
        # Send video preview (in separate try-catch to preserve state if this fails)
        try:
            # Check file size (Telegram has 50MB limit for videos)
            file_size = os.path.getsize(video_path)
            file_size_mb = file_size / (1024 * 1024)
            logger.info(f"Video file size: {file_size_mb:.2f} MB")
            
            if file_size_mb > 50:
                logger.warning(f"Video too large for Telegram preview: {file_size_mb:.2f} MB > 50 MB")
                await update.message.reply_text(
                    f"⚠️ <b>Видео слишком большое для предпросмотра</b> ({file_size_mb:.1f} MB)\n\n"
                    "Но видео скачано успешно! 📝 Теперь отправьте подпись к посту:",
                    parse_mode='HTML'
                )
            else:
                logger.info(f"Sending video preview to user {user_id}")
                # Use asyncio.wait_for to add overall timeout
                async def send_video():
                    with open(video_path, 'rb') as video:
                        await update.message.reply_video(
                            video=video,
                            caption="<b>✅ Предпросмотр рилса</b>\n\n📝 Теперь отправьте подпись к посту:",
                            parse_mode='HTML',
                            read_timeout=180,
                            write_timeout=180,
                            connect_timeout=60
                        )
                
                # Set overall timeout to 5 minutes
                await asyncio.wait_for(send_video(), timeout=300)
                logger.info(f"Video preview sent successfully to user {user_id}")
        except asyncio.TimeoutError:
            logger.error(f"Timeout sending video preview (5 minutes exceeded)")
            await update.message.reply_text(
                "⚠️ <b>Превышен лимит времени отправки предпросмотра</b>\n\n"
                "Но видео скачано успешно! 📝 Теперь отправьте подпись к посту:",
                parse_mode='HTML'
            )
        except Exception as e:
            logger.error(f"Error sending video preview: {e}", exc_info=True)
            # Video is downloaded, state is set, just notify user without preview
            await update.message.reply_text(
                "⚠️ <b>Не удалось отправить предпросмотр</b>\n\n"
                "Но видео скачано успешно! 📝 Теперь отправьте подпись к посту:",
                parse_mode='HTML'
            )
    
    async def _process_and_publish_reels(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_state: Dict, immediate: bool = True) -> None:
        """Process and publish reels to selected platforms."""
        try:
            # Get caption from user state
            caption = user_state.get('caption', '')
            if not caption:
                await update.message.reply_text("❌ Подпись не найдена!")
                return
            
            video_path = user_state.get('reels_video_path')
            if not video_path:
                await update.message.reply_text("❌ Видео не найдено!")
                return
            
            # Show processing message
            processing_msg = await update.message.reply_text("⏳ Публикую рилс...")
            
            # Check if cancelled before publishing
            if user_state.get('cancelled', False):
                await processing_msg.edit_text("❌ Операция отменена.")
                return
            
            # Publish to selected platforms
            instagram_success = False
            telegram_success = False
            vk_success = False
            
            if user_state['target_platform'] in ['instagram', 'both', 'all']:
                # Check if cancelled before Instagram publishing
                if user_state.get('cancelled', False):
                    await processing_msg.edit_text("❌ Операция отменена.")
                    return
                logger.info("Publishing to Instagram...")
                # Instagram post_video is synchronous, run in executor
                import asyncio
                loop = asyncio.get_event_loop()
                instagram_success = await loop.run_in_executor(
                    None,
                    self.instagram_service.post_video,
                    video_path,
                    caption
                )
                logger.info(f"Instagram publishing result: {instagram_success}")
            
            if user_state['target_platform'] in ['telegram', 'both', 'all']:
                # Check if cancelled before Telegram publishing
                if user_state.get('cancelled', False):
                    await processing_msg.edit_text("❌ Операция отменена.")
                    return
                logger.info("Publishing to Telegram...")
                telegram_success = await self.telegram_service.post_video(video_path, caption)
                logger.info(f"Telegram publishing result: {telegram_success}")
            
            if user_state['target_platform'] in ['vk', 'all']:
                # Check if cancelled before VK publishing
                if user_state.get('cancelled', False):
                    await processing_msg.edit_text("❌ Операция отменена.")
                    return
                logger.info("Publishing to VK...")
                vk_success = await self.vk_service.post_video(video_path, caption)
                logger.info(f"VK publishing result: {vk_success}")
            
            # Send results
            if immediate:
                # Build success message based on which platforms succeeded
                success_platforms = []
                if instagram_success:
                    success_platforms.append('Instagram')
                if telegram_success:
                    success_platforms.append('Telegram')
                if vk_success:
                    success_platforms.append('VK')
                
                if success_platforms:
                    platforms_text = ', '.join(success_platforms)
                    message = f"✅ Рилс опубликован в {platforms_text}!"
                    await processing_msg.edit_text(message)
                else:
                    await processing_msg.edit_text("❌ Не удалось опубликовать рилс ни на одной платформе.")
            else:
                # Scheduled post results
                success_platforms = []
                if instagram_success:
                    success_platforms.append('Instagram')
                if telegram_success:
                    success_platforms.append('Telegram')
                if vk_success:
                    success_platforms.append('VK')
                
                if success_platforms:
                    platforms_text = ', '.join(success_platforms)
                    message = f"✅ Запланированный рилс опубликован в {platforms_text}!"
                    await self.telegram_service.send_notification(update.effective_user.id, message)
                else:
                    await self.telegram_service.send_error_notification(update.effective_user.id, "Не удалось опубликовать запланированный рилс")
            
            # Cleanup
            if video_path and os.path.exists(video_path):
                os.remove(video_path)
            self.clear_user_state(update.effective_user.id)
            
            # Remove from scheduled posts
            if update.effective_user.id in self.scheduled_posts:
                del self.scheduled_posts[update.effective_user.id]
            
        except Exception as e:
            logger.error(f"Error processing and publishing reels: {e}")
            await update.message.reply_text(f"❌ Ошибка публикации рилса: {e}")
            self.clear_user_state(update.effective_user.id)
    
    async def handle_add_link(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle adding a link to the queue.
        
        Args:
            update: Telegram update object
            context: Bot context
        """
        if not self.is_admin(update.effective_user.id):
            await update.message.reply_text(MESSAGES['unauthorized'])
            return
        
        user_state = self.get_user_state(update.effective_user.id)
        
        # Set state to waiting for link
        user_state['step'] = 'waiting_for_link'
        
        message = """➕ <b>Добавление ссылки в очередь</b>

📝 Отправьте ссылку на пост или рилс из Instagram

<b>Поддерживаемые форматы:</b>
• https://www.instagram.com/p/ABC123/
• https://www.instagram.com/reel/ABC123/

Пост будет автоматически опубликован в следующее запланированное время."""
        
        await update.message.reply_text(message, parse_mode='HTML')
    
    async def handle_link_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle link input for queue.
        
        Args:
            update: Telegram update object
            context: Bot context
        """
        if not self.is_admin(update.effective_user.id):
            await update.message.reply_text(MESSAGES['unauthorized'])
            return
        
        user_state = self.get_user_state(update.effective_user.id)
        
        # Check if we're waiting for link
        if user_state.get('step') != 'waiting_for_link':
            return
        
        url = update.message.text.strip()
        
        # Validate URL
        if not ('instagram.com' in url or 'instagr.am' in url):
            await update.message.reply_text("❌ Неверная ссылка! Отправьте корректную ссылку на пост/рилс из Instagram.")
            return
        
        # Add to queue
        try:
            post = self.scheduler_service.add_to_queue(url, platform='all')
            
            # Get schedule info
            schedule_info = self.scheduler_service.get_schedule_info()
            
            message = f"""✅ <b>Ссылка добавлена в очередь!</b>

📎 <b>URL:</b> {url[:50]}...
🆔 <b>ID:</b> {post.id}
📅 <b>Добавлено:</b> {datetime.fromisoformat(post.added_at).strftime('%d.%m.%Y %H:%M')}

{schedule_info}"""
            
            await update.message.reply_text(message, parse_mode='HTML', reply_markup=self.get_main_keyboard())
            
            # Clear state
            user_state['step'] = 'start'
            
        except Exception as e:
            logger.error(f"Error adding link to queue: {e}")
            await update.message.reply_text(f"❌ Ошибка добавления ссылки: {e}")
    
    async def handle_view_queue(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle viewing the post queue.
        
        Args:
            update: Telegram update object
            context: Bot context
        """
        if not self.is_admin(update.effective_user.id):
            await update.message.reply_text(MESSAGES['unauthorized'])
            return
        
        try:
            # Get all posts from queue
            all_posts = self.scheduler_service.get_queue()
            pending_posts = self.scheduler_service.get_pending_posts()
            
            if not all_posts:
                message = """📋 <b>Очередь постов пуста</b>

Используйте кнопку "➕ Добавить ссылку" для добавления постов в очередь."""
                await update.message.reply_text(message, parse_mode='HTML', reply_markup=self.get_main_keyboard())
                return
            
            # Get schedule info
            schedule_info = self.scheduler_service.get_schedule_info()
            
            # Build message with queue details
            message = f"""📋 <b>Очередь постов</b>

{schedule_info}

━━━━━━━━━━━━━━━━

<b>Посты в очереди:</b>

"""
            
            # Group posts by status
            statuses = {
                'pending': '⏳ В ожидании',
                'processing': '🔄 Обрабатывается',
                'published': '✅ Опубликован',
                'failed': '❌ Ошибка'
            }
            
            for status, status_text in statuses.items():
                posts_with_status = [p for p in all_posts if p.status == status]
                if posts_with_status:
                    message += f"\n<b>{status_text}:</b> {len(posts_with_status)}\n"
                    for post in posts_with_status[:5]:  # Show max 5 per status
                        url_short = post.url[:40] + '...' if len(post.url) > 40 else post.url
                        added = datetime.fromisoformat(post.added_at).strftime('%d.%m %H:%M')
                        message += f"  • {url_short}\n    ID: {post.id} | {added}\n"
                    
                    if len(posts_with_status) > 5:
                        message += f"  ... и ещё {len(posts_with_status) - 5}\n"
            
            # Add management buttons
            keyboard = [
                [KeyboardButton("🗑️ Очистить опубликованные"), KeyboardButton("❌ Очистить все")],
                [KeyboardButton("🚀 Начать публикацию"), KeyboardButton("➕ Добавить ссылку")],
                [KeyboardButton("✅ Status"), KeyboardButton("ℹ️ Help")],
            ]
            queue_keyboard = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            
            await update.message.reply_text(message, parse_mode='HTML', reply_markup=queue_keyboard)
            
        except Exception as e:
            logger.error(f"Error viewing queue: {e}")
            await update.message.reply_text(f"❌ Ошибка просмотра очереди: {e}")
    
    async def handle_clear_published(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Clear published posts from queue."""
        if not self.is_admin(update.effective_user.id):
            await update.message.reply_text(MESSAGES['unauthorized'])
            return
        
        try:
            published_count = len(self.scheduler_service.get_queue(status='published'))
            self.scheduler_service.clear_queue(status='published')
            
            message = f"✅ Очищено опубликованных постов: {published_count}"
            await update.message.reply_text(message, reply_markup=self.get_main_keyboard())
            
        except Exception as e:
            logger.error(f"Error clearing published posts: {e}")
            await update.message.reply_text(f"❌ Ошибка: {e}")
    
    async def handle_clear_all_queue(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Clear entire queue."""
        if not self.is_admin(update.effective_user.id):
            await update.message.reply_text(MESSAGES['unauthorized'])
            return
        
        try:
            total_count = len(self.scheduler_service.get_queue())
            self.scheduler_service.clear_queue()
            
            message = f"✅ Очередь полностью очищена. Удалено постов: {total_count}"
            await update.message.reply_text(message, reply_markup=self.get_main_keyboard())
            
        except Exception as e:
            logger.error(f"Error clearing queue: {e}")
            await update.message.reply_text(f"❌ Ошибка: {e}")
    
    async def _publish_from_queue(self, post: QueuedPost) -> bool:
        """
        Publish a post from the queue.
        
        Args:
            post: The queued post to publish
            
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Publishing from queue: {post.id} - {post.url}")
            
            # Detect if it's a reels or regular post
            is_reels = '/reel/' in post.url
            
            if is_reels:
                # Download and publish reels
                logger.info("Detected reels URL, downloading...")
                video_path = self.instagram_service.download_reels(post.url)
                
                if not video_path:
                    logger.error("Failed to download reels")
                    return False
                
                # Get caption from reels
                caption = self.instagram_service.get_reels_caption(post.url)
                if not caption:
                    caption = "📹 Новый рилс"
                
                # Publish to platforms
                success = False
                if post.platform in ['instagram', 'all']:
                    success = self.instagram_service.post_video(video_path, caption) or success
                
                if post.platform in ['telegram', 'all']:
                    success = await self.telegram_service.post_video(video_path, caption) or success
                
                if post.platform in ['vk', 'all']:
                    success = await self.vk_service.post_video(video_path, caption) or success
                
                # Cleanup
                if os.path.exists(video_path):
                    os.remove(video_path)
                
                return success
            else:
                # Regular post - download photos and publish
                logger.info("Detected regular post URL, downloading photos...")
                
                # Try to download post media
                try:
                    if not self.instagram_service.is_logged_in():
                        if not self.instagram_service.login():
                            logger.error("Failed to login to Instagram")
                            return False
                    
                    media_pk = self.instagram_service.client.media_pk_from_url(post.url)
                    media_info = self.instagram_service.client.media_info(media_pk)
                    
                    # Download photos
                    from config import UPLOADS_DIR
                    photo_paths = []
                    
                    if media_info.media_type == 1:  # Single photo
                        photo_path = self.instagram_service.client.photo_download(media_pk, folder=UPLOADS_DIR)
                        photo_paths = [str(photo_path)]
                    elif media_info.media_type == 8:  # Album
                        album_path = self.instagram_service.client.album_download(media_pk, folder=UPLOADS_DIR)
                        # album_download returns a list of paths
                        photo_paths = [str(p) for p in album_path] if isinstance(album_path, list) else [str(album_path)]
                    
                    if not photo_paths:
                        logger.error("No photos downloaded")
                        return False
                    
                    # Get caption
                    caption = media_info.caption_text if media_info.caption_text else "📸 Новый пост"
                    
                    # Process photos
                    processed_photos = self.image_processor.process_photos(photo_paths)
                    target_size = self.image_processor.determine_image_format(processed_photos)
                    final_photos = [self.image_processor.resize_image(p, target_size) for p in processed_photos]
                    
                    # Publish to platforms
                    success = False
                    if post.platform in ['instagram', 'all']:
                        success = self.instagram_service.post_to_instagram(final_photos, caption) or success
                    
                    if post.platform in ['telegram', 'all']:
                        success = await self.telegram_service.post_to_telegram(final_photos, caption) or success
                    
                    if post.platform in ['vk', 'all']:
                        success = await self.vk_service.post_to_vk(final_photos, caption) or success
                    
                    # Cleanup
                    self.image_processor.cleanup_files(photo_paths)
                    self.image_processor.cleanup_files(final_photos)
                    
                    return success
                    
                except Exception as e:
                    logger.error(f"Error downloading/publishing post: {e}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error in _publish_from_queue: {e}")
            return False
