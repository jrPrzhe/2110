"""
Telegram service for the Auto-Poster Bot.
Handles posting to Telegram groups and sending notifications.
"""

import logging
from typing import List, Optional
from telegram import Bot, InputMediaPhoto
from telegram.error import TelegramError

from config import TELEGRAM_BOT_TOKEN, TELEGRAM_GROUP_ID

logger = logging.getLogger("tg")

class TelegramService:
    """Handles Telegram operations."""
    
    def __init__(self):
        """Initialize the Telegram service."""
        self.bot = Bot(token=TELEGRAM_BOT_TOKEN)
        self.group_id = TELEGRAM_GROUP_ID
    
    async def post_photo(self, photo_path: str, caption: str) -> bool:
        """
        Post a single photo to the Telegram group.
        
        Args:
            photo_path: Path to the photo file
            caption: Caption for the post
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            logger.info(f"Posting single photo to Telegram group: {photo_path}")
            
            with open(photo_path, 'rb') as photo_file:
                await self.bot.send_photo(
                    chat_id=self.group_id,
                    photo=photo_file,
                    caption=caption,
                    parse_mode='HTML'
                )
            
            logger.info("Photo posted successfully to Telegram group")
            return True
            
        except TelegramError as e:
            logger.error(f"Telegram error posting photo: {e}")
            return False
        except Exception as e:
            logger.error(f"Error posting photo to Telegram: {e}")
            return False
    
    async def post_album(self, photo_paths: List[str], caption: str) -> bool:
        """
        Post an album (media group) to the Telegram group.
        
        Args:
            photo_paths: List of paths to photo files
            caption: Caption for the post
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if len(photo_paths) < 2:
                logger.warning("Album requires at least 2 photos, posting as single photo instead")
                return await self.post_photo(photo_paths[0], caption)
            
            if len(photo_paths) > 10:
                logger.warning("Telegram supports max 10 photos in media group, truncating...")
                photo_paths = photo_paths[:10]
            
            logger.info(f"Posting album to Telegram group with {len(photo_paths)} photos")
            
            # Prepare media group
            media_group = []
            for i, photo_path in enumerate(photo_paths):
                with open(photo_path, 'rb') as photo_file:
                    media = InputMediaPhoto(
                        media=photo_file,
                        caption=caption if i == 0 else None,  # Only first photo gets caption
                        parse_mode='HTML'
                    )
                    media_group.append(media)
            
            # Send media group
            await self.bot.send_media_group(
                chat_id=self.group_id,
                media=media_group
            )
            
            logger.info("Album posted successfully to Telegram group")
            return True
            
        except TelegramError as e:
            logger.error(f"Telegram error posting album: {e}")
            return False
        except Exception as e:
            logger.error(f"Error posting album to Telegram: {e}")
            return False
    
    async def post_to_telegram(self, photo_paths: List[str], caption: str) -> bool:
        """
        Post photos to Telegram group (single or album based on count).
        
        Args:
            photo_paths: List of paths to photo files
            caption: Caption for the post
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not photo_paths:
            logger.error("No photos provided for Telegram post")
            return False
        
        if len(photo_paths) == 1:
            return await self.post_photo(photo_paths[0], caption)
        else:
            return await self.post_album(photo_paths, caption)
    
    async def send_message(self, chat_id: int, text: str, parse_mode: str = 'HTML') -> bool:
        """
        Send a text message to a specific chat.
        
        Args:
            chat_id: ID of the chat to send message to
            text: Message text
            parse_mode: Parse mode for the message
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            await self.bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode=parse_mode
            )
            return True
            
        except TelegramError as e:
            logger.error(f"Telegram error sending message: {e}")
            return False
        except Exception as e:
            logger.error(f"Error sending message to Telegram: {e}")
            return False
    
    async def send_notification(self, admin_id: int, message: str) -> bool:
        """
        Send a notification message to the admin.
        
        Args:
            admin_id: Admin's user ID
            message: Notification message
            
        Returns:
            bool: True if successful, False otherwise
        """
        return await self.send_message(admin_id, message)
    
    async def send_success_notification(self, admin_id: int, platform: str = "both", additional_message: str = "") -> bool:
        """
        Send success notification to admin.
        
        Args:
            admin_id: Admin's user ID
            platform: Platform where post was successful ("instagram", "telegram", or "both")
            additional_message: Additional message to include
            
        Returns:
            bool: True if successful, False otherwise
        """
        if platform == "both":
            message = "✅ Post published successfully to Instagram and Telegram!"
        elif platform == "instagram":
            message = "✅ Post published successfully to Instagram!"
        elif platform == "telegram":
            message = "✅ Post published successfully to Telegram!"
        else:
            message = "✅ Post published successfully!"
        
        if additional_message:
            message += f"\n\n{additional_message}"
        
        return await self.send_notification(admin_id, message)
    
    async def send_error_notification(self, admin_id: int, error: str, platform: str = "unknown") -> bool:
        """
        Send error notification to admin.
        
        Args:
            admin_id: Admin's user ID
            error: Error message
            platform: Platform where error occurred
            
        Returns:
            bool: True if successful, False otherwise
        """
        if platform == "instagram":
            message = f"❌ Instagram error: {error}"
        elif platform == "telegram":
            message = f"❌ Telegram error: {error}"
        else:
            message = f"❌ Error publishing post: {error}"
        
        return await self.send_notification(admin_id, message)
    
    async def post_video(self, video_path: str, caption: str) -> bool:
        """
        Post a video to the Telegram group.
        
        Args:
            video_path: Path to the video file
            caption: Caption for the post
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            logger.info(f"Posting video to Telegram group: {video_path}")
            
            # Check file size
            import os
            file_size_mb = os.path.getsize(video_path) / (1024 * 1024)
            logger.info(f"Video file size: {file_size_mb:.2f} MB")
            
            with open(video_path, 'rb') as video_file:
                await self.bot.send_video(
                    chat_id=self.group_id,
                    video=video_file,
                    caption=caption,
                    parse_mode='HTML',
                    supports_streaming=True,
                    read_timeout=300,  # 5 минут на чтение
                    write_timeout=300,  # 5 минут на отправку
                    connect_timeout=60  # 1 минута на подключение
                )
            
            logger.info("Video posted successfully to Telegram group")
            return True
            
        except TelegramError as e:
            logger.error(f"Telegram error posting video: {e}")
            return False
        except Exception as e:
            logger.error(f"Error posting video to Telegram: {e}")
            return False
    
    async def test_connection(self) -> bool:
        """
        Test the Telegram bot connection.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            me = await self.bot.get_me()
            logger.info(f"Telegram bot connected: @{me.username}")
            return True
        except Exception as e:
            logger.error(f"Telegram connection test failed: {e}")
            return False
