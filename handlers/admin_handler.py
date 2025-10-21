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
        
        # User state management: {user_id: {'photos': [], 'waiting_for_caption': bool, 'post_mode': 'auto'|'single'|'multi'|'reels', 'target_platform': 'both'|'instagram'|'telegram'|'vk'|'all', 'step': 'start'|'type_selected'|'platform_selected'|'article_check_selection'|'photos_uploaded'|'caption_entered'|'preview_shown'|'scheduled'|'reels_url_input'|'reels_download', 'cancelled': bool, 'check_articles': bool, 'reels_url': str, 'reels_video_path': str}}
        self.user_states: Dict[int, Dict] = {}
        # Pending posts waiting for approval: {user_id: {'photos': [], 'caption': str, 'message_id': int, 'target_platform': str, 'scheduled_time': datetime}}
        self.pending_posts: Dict[int, Dict] = {}
        # Scheduled posts: {user_id: {'task': asyncio.Task, 'post_data': dict}}
        self.scheduled_posts: Dict[int, Dict] = {}

    def get_main_keyboard(self) -> ReplyKeyboardMarkup:
        """Return the main reply keyboard for quick actions."""
        keyboard = [
            [KeyboardButton("🚀 Начать публикацию")],
            [KeyboardButton("✅ Status"), KeyboardButton("❌ Cancel")],
            [KeyboardButton("ℹ️ Help")],
        ]
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    def get_type_selection_keyboard(self) -> ReplyKeyboardMarkup:
        """Return keyboard for post type selection."""
        keyboard = [
            [KeyboardButton("📷 Одиночный пост"), KeyboardButton("📸 Массовый пост")],
            [KeyboardButton("📹 Публикация рилс")],
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
        Handle photo messages from admin.
        
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
            if user_state['step'] not in ['photos_upload', 'caption_entered']:
                # Allow direct photo upload - set default values
                user_state['post_mode'] = 'multi'  # Default to multi for batch upload
                user_state['target_platform'] = 'both'  # Default to both platforms
                user_state['check_articles'] = True  # Default to article check
                user_state['step'] = 'photos_upload'
                await update.message.reply_text("📸 Прямая загрузка фото! Режим: массовый пост, платформы: Instagram + Telegram, поиск артикулов: включен")
            
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
            
            # Add photo to state
            # If mode is 'single' and there is already a photo, replace it
            if user_state.get('post_mode') == 'single' and user_state['photos']:
                # Remove previous photo file
                self.image_processor.cleanup_files(user_state['photos'])
                user_state['photos'] = [photo_path]
            else:
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
    
    async def handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle text messages from admin (captions or reels URL).
        
        Args:
            update: Telegram update object
            context: Bot context
        """
        if not self.is_admin(update.effective_user.id):
            await update.message.reply_text(MESSAGES['unauthorized'])
            return
        
        user_state = self.get_user_state(update.effective_user.id)
        
        # Check if we're waiting for reels URL
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
                logger.warning("No article numbers found, using original caption")
            
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
        
        help_message = """🤖 <b>Помощь - Новый бизнес-процесс</b>

<b>Как использовать:</b>
1. 🚀 Нажмите "Начать публикацию"
2. 📷 Выберите тип поста (одиночный/массовый)
3. 📱 Выберите платформу (Instagram/Telegram/Обе)
4. 📸 Отправьте фото (1–10)
5. 📝 Отправьте подпись к посту
6. 🤖 Используйте "Помощь ИИ" для улучшения описания
7. ⏰ Выберите время публикации (сейчас/запланировать)

<b>Команды:</b>
/start — запуск
/help — помощь
/status — статус бота
/cancel — отмена

<b>Планирование:</b>
• <code>HH:MM</code> - сегодня в указанное время
• <code>DD.MM HH:MM</code> - в указанную дату и время
• <code>+N</code> - через N минут

<b>ИИ помощь:</b>
• Улучшает описания постов
• Добавляет эмодзи и хештеги
• Адаптирует стиль под платформу
• Требует настройки GOOGLE_API_KEY

<b>Примечания:</b>
• Фото автоматически приводятся к 1080×1080 или 1080×1350
• 1 фото = одиночный пост, 2–10 фото = карусель/альбом
• Доступ только у администратора
• Временные файлы очищаются автоматически
• Запланированные посты можно отменить командой /cancel"""
        
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
        Handle start publication process.
        
        Args:
            update: Telegram update object
            context: Bot context
        """
        if not self.is_admin(update.effective_user.id):
            await update.message.reply_text(MESSAGES['unauthorized'])
            return
        
        # Clear any existing state
        self.clear_user_state(update.effective_user.id)
        
        # Start the business process
        user_state = self.get_user_state(update.effective_user.id)
        user_state['step'] = 'type_selection'
        
        message = """🚀 <b>Начинаем процесс публикации</b>

<b>Шаг 1:</b> Выберите тип загрузки:

📷 <b>Одиночный пост</b> - одно фото
📸 <b>Массовый пост</b> - несколько фото (до 10)"""
        
        await update.message.reply_text(message, parse_mode='HTML', reply_markup=self.get_type_selection_keyboard())

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
        
        post_type = "одиночный" if user_state['post_mode'] == 'single' else "массовый"
        message = f"""📷 <b>Instagram выбран</b>

<b>Шаг 3:</b> Нужно ли искать артикулы на фотографиях?

🔍 <b>Да, искать артикулы</b> - бот автоматически найдет номера товаров и добавит их в пост
⏭️ <b>Нет, пропустить</b> - загрузить фото без поиска артикулов

{'📷 Отправьте одно фото' if user_state['post_mode'] == 'single' else '📸 Отправьте фото (до 10 штук)'}"""
        
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
        
        # Check if reels mode
        if user_state['post_mode'] == 'reels':
            user_state['step'] = 'reels_url_input'
            message = """💬 <b>Telegram выбран</b>

<b>Шаг 3:</b> Отправьте ссылку на рилс из Instagram

Пример: https://www.instagram.com/reel/ABC123/"""
            
            await update.message.reply_text(message, parse_mode='HTML')
        else:
            user_state['step'] = 'article_check_selection'
            
            post_type = "одиночный" if user_state['post_mode'] == 'single' else "массовый"
            message = f"""💬 <b>Telegram выбран</b>

<b>Шаг 3:</b> Нужно ли искать артикулы на фотографиях?

🔍 <b>Да, искать артикулы</b> - бот автоматически найдет номера товаров и добавит их в пост
⏭️ <b>Нет, пропустить</b> - загрузить фото без поиска артикулов

{'📷 Отправьте одно фото' if user_state['post_mode'] == 'single' else '📸 Отправьте фото (до 10 штук)'}"""
            
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
        
        # Check if reels mode
        if user_state['post_mode'] == 'reels':
            user_state['step'] = 'reels_url_input'
            message = """🔵 <b>VK выбран</b>

<b>Шаг 3:</b> Отправьте ссылку на рилс из Instagram

Пример: https://www.instagram.com/reel/ABC123/"""
            
            await update.message.reply_text(message, parse_mode='HTML')
        else:
            user_state['step'] = 'article_check_selection'
            
            post_type = "одиночный" if user_state['post_mode'] == 'single' else "массовый"
            message = f"""🔵 <b>VK выбран</b>

<b>Шаг 3:</b> Нужно ли искать артикулы на фотографиях?

🔍 <b>Да, искать артикулы</b> - бот автоматически найдет номера товаров и добавит их в пост
⏭️ <b>Нет, пропустить</b> - загрузить фото без поиска артикулов

{'📷 Отправьте одно фото' if user_state['post_mode'] == 'single' else '📸 Отправьте фото (до 10 штук)'}"""
            
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
        
        # Check if reels mode
        if user_state['post_mode'] == 'reels':
            user_state['step'] = 'reels_url_input'
            message = """🔀 <b>Все платформы выбраны (Telegram + VK)</b>

<b>Шаг 3:</b> Отправьте ссылку на рилс из Instagram

Пример: https://www.instagram.com/reel/ABC123/"""
            
            await update.message.reply_text(message, parse_mode='HTML')
        else:
            user_state['step'] = 'article_check_selection'
            
            post_type = "одиночный" if user_state['post_mode'] == 'single' else "массовый"
            message = f"""🔀 <b>Все платформы выбраны</b>

<b>Шаг 3:</b> Нужно ли искать артикулы на фотографиях?

🔍 <b>Да, искать артикулы</b> - бот автоматически найдет номера товаров и добавит их в пост
⏭️ <b>Нет, пропустить</b> - загрузить фото без поиска артикулов

{'📷 Отправьте одно фото' if user_state['post_mode'] == 'single' else '📸 Отправьте фото (до 10 штук)'}"""
            
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
        user_state['step'] = 'photos_upload'
        
        post_type = "одиночный" if user_state['post_mode'] == 'single' else "массовый"
        platform_text = {
            'instagram': 'Instagram',
            'telegram': 'Telegram',
            'vk': 'VK',
            'both': 'Instagram и Telegram',
            'all': 'Instagram, Telegram и VK'
        }.get(user_state['target_platform'], 'неизвестно')
        
        message = f"""🔍 <b>Поиск артикулов включен</b>

<b>Шаг 4:</b> Отправьте фото для {post_type} поста

📱 <b>Платформа:</b> {platform_text}
🔍 <b>Поиск артикулов:</b> включен

{'📷 Отправьте одно фото' if user_state['post_mode'] == 'single' else '📸 Отправьте фото (до 10 штук)'}"""
        
        await update.message.reply_text(message, parse_mode='HTML')

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
        user_state['step'] = 'photos_upload'
        
        post_type = "одиночный" if user_state['post_mode'] == 'single' else "массовый"
        platform_text = {
            'instagram': 'Instagram',
            'telegram': 'Telegram',
            'vk': 'VK',
            'both': 'Instagram и Telegram',
            'all': 'Instagram, Telegram и VK'
        }.get(user_state['target_platform'], 'неизвестно')
        
        message = f"""⏭️ <b>Поиск артикулов пропущен</b>

<b>Шаг 4:</b> Отправьте фото для {post_type} поста

📱 <b>Платформа:</b> {platform_text}
🔍 <b>Поиск артикулов:</b> отключен

{'📷 Отправьте одно фото' if user_state['post_mode'] == 'single' else '📸 Отправьте фото (до 10 штук)'}"""
        
        await update.message.reply_text(message, parse_mode='HTML')
    
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

💬 <b>Telegram</b> - только Telegram группа  
🔵 <b>VK</b> - только VK группа
🔀 <b>Все платформы</b> - Telegram + VK

<i>Примечание: Instagram не поддерживает публикацию рилсов через API</i>"""
        
        # Create custom keyboard without Instagram option
        keyboard = [
            [KeyboardButton("💬 Telegram"), KeyboardButton("🔵 VK")],
            [KeyboardButton("🔀 Все платформы")],
            [KeyboardButton("❌ Отмена")],
        ]
        reels_platform_keyboard = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        await update.message.reply_text(message, parse_mode='HTML', reply_markup=reels_platform_keyboard)
    
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
        if not self.is_admin(update.effective_user.id):
            await update.message.reply_text(MESSAGES['unauthorized'])
            return
        
        user_state = self.get_user_state(update.effective_user.id)
        
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
            with open(video_path, 'rb') as video:
                await update.message.reply_video(
                    video=video,
                    caption="<b>✅ Предпросмотр рилса</b>\n\n📝 Теперь отправьте подпись к посту:",
                    parse_mode='HTML',
                    read_timeout=300,
                    write_timeout=300,
                    connect_timeout=60
                )
        except Exception as e:
            logger.error(f"Error sending video preview: {e}")
            # Video is downloaded, state is set, just notify user without preview
            await update.message.reply_text(
                "⚠️ <b>Не удалось отправить предпросмотр</b> (видео слишком большое)\n\n"
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
            telegram_success = False
            vk_success = False
            
            if user_state['target_platform'] in ['telegram', 'both', 'all']:
                # Check if cancelled before Telegram publishing
                if user_state.get('cancelled', False):
                    await processing_msg.edit_text("❌ Операция отменена.")
                    return
                telegram_success = await self.telegram_service.post_video(video_path, caption)
            
            if user_state['target_platform'] in ['vk', 'all']:
                # Check if cancelled before VK publishing
                if user_state.get('cancelled', False):
                    await processing_msg.edit_text("❌ Операция отменена.")
                    return
                vk_success = await self.vk_service.post_video(video_path, caption)
            
            # Send results
            if immediate:
                # Build success message based on which platforms succeeded
                success_platforms = []
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
