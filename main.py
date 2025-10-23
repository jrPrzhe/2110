"""
Main entry point for the Auto-Poster Bot.
A Telegram bot that posts photos to Instagram and Telegram groups.
"""

import logging
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from telegram.request import HTTPXRequest

from config import validate_config, TELEGRAM_BOT_TOKEN, MESSAGES, LOG_LEVEL
from handlers.admin_handler import AdminHandler

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=getattr(logging, LOG_LEVEL, logging.INFO)
)
logger = logging.getLogger(__name__)

class AutoPosterBot:
    """Main bot class."""
    
    def __init__(self):
        """Initialize the bot."""
        self.admin_handler = AdminHandler()
        self.application = None
    
    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle errors that occur during bot operation.
        
        Args:
            update: Telegram update object
            context: Bot context
        """
        logger.error(f"Update {update} caused error {context.error}")
        
        # Try to send error message to admin if possible
        if update and update.effective_user:
            try:
                await context.bot.send_message(
                    chat_id=update.effective_user.id,
                    text=f"❌ An error occurred: {str(context.error)}"
                )
            except Exception:
                pass  # Ignore if we can't send error message
    
    def setup_handlers(self):
        """Set up all bot handlers."""
        # Command handlers
        self.application.add_handler(CommandHandler("start", self.admin_handler.handle_start))
        self.application.add_handler(CommandHandler("help", self.admin_handler.handle_help))
        self.application.add_handler(CommandHandler("status", self.admin_handler.handle_status))
        self.application.add_handler(CommandHandler("cancel", self.admin_handler.handle_cancel))
        self.application.add_handler(CommandHandler("reset", self.admin_handler.handle_reset_instagram))
        self.application.add_handler(CommandHandler("single", self.admin_handler.handle_mode_single))
        self.application.add_handler(CommandHandler("multi", self.admin_handler.handle_mode_multi))
        
        # Queue management commands
        self.application.add_handler(CommandHandler("add_link", self.admin_handler.handle_add_link))
        self.application.add_handler(CommandHandler("queue", self.admin_handler.handle_view_queue))
        
        # Message handlers
        self.application.add_handler(MessageHandler(filters.PHOTO, self.admin_handler.handle_photo))
        self.application.add_handler(MessageHandler(filters.VIDEO, self.admin_handler.handle_video))
        
        # Queue management button handlers
        self.application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"^➕ Добавить ссылку$"), self.admin_handler.handle_add_link))
        self.application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"^📋 Очередь постов$"), self.admin_handler.handle_view_queue))
        self.application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"^🗑️ Очистить опубликованные$"), self.admin_handler.handle_clear_published))
        self.application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"^❌ Очистить все$"), self.admin_handler.handle_clear_all_queue))
        
        # New business process handlers
        self.application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"^🚀 Начать публикацию$"), self.admin_handler.handle_start_publication))
        self.application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"^📷 Одиночный пост$"), self.admin_handler.handle_type_single))
        self.application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"^📸 Массовый пост$"), self.admin_handler.handle_type_multi))
        self.application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"^📹 Публикация рилс$"), self.admin_handler.handle_type_reels))
        self.application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"^📷 Instagram$"), self.admin_handler.handle_platform_instagram))
        self.application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"^💬 Telegram$"), self.admin_handler.handle_platform_telegram))
        self.application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"^🔵 VK$"), self.admin_handler.handle_platform_vk))
        self.application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"^🔀 Все платформы$"), self.admin_handler.handle_platform_both))
        self.application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"^⚡ Опубликовать сейчас$"), self.admin_handler.handle_publish_now))
        self.application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"^⏰ Запланировать$"), self.admin_handler.handle_schedule_post))
        self.application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"^🤖 Помощь ИИ$"), self.admin_handler.handle_ai_help))
        
        # Cancel button handlers
        self.application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"^❌ Отмена$"), self.admin_handler.handle_cancel_button))
        
        # Article check handlers
        self.application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"^🔍 Да, искать артикулы$"), self.admin_handler.handle_article_check_yes))
        self.application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"^⏭️ Нет, пропустить$"), self.admin_handler.handle_article_check_no))
        
        # Legacy button handlers
        self.application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"^🖼️ Single$"), self.admin_handler.handle_btn_single))
        self.application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"^🖼️ Multi$"), self.admin_handler.handle_btn_multi))
        self.application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"^✅ Status$"), self.admin_handler.handle_btn_status))
        self.application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"^❌ Cancel$"), self.admin_handler.handle_btn_cancel))
        self.application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"^ℹ️ Help$"), self.admin_handler.handle_btn_help))
        self.application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"^🔄 Reset Instagram$"), self.admin_handler.handle_reset_instagram))
        
        # Time input handler (for scheduling)
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.admin_handler.handle_text))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.admin_handler.handle_time_input))
        # Callbacks
        self.application.add_handler(CallbackQueryHandler(self.admin_handler.on_callback))
        
        # Error handler
        self.application.add_error_handler(self.error_handler)
    
    async def startup(self, application: Application):
        """Initialize services on startup."""
        logger.info("Starting Auto-Poster Bot...")
        
        # Validate configuration
        try:
            validate_config()
            logger.info("Configuration validated successfully")
        except ValueError as e:
            logger.error(f"Configuration error: {e}")
            raise
        
        # Start scheduler service
        try:
            await self.admin_handler.scheduler_service.start()
            logger.info("Scheduler service started successfully")
        except Exception as e:
            logger.error(f"Failed to start scheduler: {e}")
        
        # Test Instagram connection
        try:
            if self.admin_handler.instagram_service.login():
                logger.info("Instagram service initialized successfully")
            else:
                logger.warning("Instagram login failed - bot will continue but Instagram posting may not work")
        except Exception as e:
            logger.warning(f"Instagram initialization failed: {e}")
        
        # Test Telegram connection
        try:
            if await self.admin_handler.telegram_service.test_connection():
                logger.info("Telegram service initialized successfully")
            else:
                logger.error("Telegram connection failed")
                raise Exception("Telegram connection failed")
        except Exception as e:
            logger.error(f"Telegram initialization failed: {e}")
            raise
        
        # Test VK connection
        try:
            if self.admin_handler.vk_service.test_connection():
                logger.info("VK service initialized successfully")
            else:
                logger.warning("VK connection failed - bot will continue but VK posting may not work")
        except Exception as e:
            logger.warning(f"VK initialization failed: {e}")
        
        # Test AI service connection
        try:
            if await self.admin_handler.ai_service.test_connection():
                logger.info("AI service initialized successfully")
            else:
                logger.warning("AI service connection failed - AI assistance will be disabled")
        except Exception as e:
            logger.warning(f"AI service initialization failed: {e}")
        
        logger.info("Auto-Poster Bot started successfully!")
    
    async def shutdown(self, application: Application):
        """Cleanup on shutdown."""
        logger.info("Shutting down Auto-Poster Bot...")
        
        # Stop scheduler service
        try:
            await self.admin_handler.scheduler_service.stop()
            logger.info("Scheduler service stopped")
        except Exception as e:
            logger.error(f"Error stopping scheduler: {e}")
        
        # Logout from Instagram
        try:
            self.admin_handler.instagram_service.logout()
        except Exception as e:
            logger.error(f"Error during Instagram logout: {e}")
        
        # Cleanup uploads directory
        try:
            self.admin_handler.image_processor.cleanup_uploads_dir()
        except Exception as e:
            logger.error(f"Error cleaning up uploads: {e}")
        
        logger.info("Auto-Poster Bot shutdown complete")
    
    def run(self):
        """Run the bot."""
        try:
            # Create application with increased network timeouts to avoid timeouts on file downloads
            request = HTTPXRequest(
                read_timeout=60.0,
                write_timeout=60.0,
                connect_timeout=20.0,
                pool_timeout=20.0,
            )
            self.application = Application.builder().token(TELEGRAM_BOT_TOKEN).request(request).build()
            
            # Setup handlers
            self.setup_handlers()
            
            # Setup startup and shutdown
            self.application.post_init = self.startup
            self.application.post_shutdown = self.shutdown
            
            # Run the bot
            logger.info("Starting bot polling...")
            self.application.run_polling(
                allowed_updates=Update.ALL_TYPES,
                drop_pending_updates=True
            )
            
        except Exception as e:
            logger.error(f"Failed to start bot: {e}")
            raise

def main():
    """Main function."""
    try:
        bot = AutoPosterBot()
        bot.run()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot crashed: {e}")
        raise

if __name__ == "__main__":
    main()
