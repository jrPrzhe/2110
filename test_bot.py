import os
import asyncio
import logging
from typing import Optional

from config import (
    TELEGRAM_BOT_TOKEN,
    ADMIN_USER_ID,
    TELEGRAM_GROUP_ID,
    INSTAGRAM_USERNAME,
    INSTAGRAM_PASSWORD,
    UPLOADS_DIR,
)
from utils.image_processor import ImageProcessor
from services.telegram_service import TelegramService
from services.instagram_service import InstagramService

try:
    from PIL import Image
except Exception as _:
    Image = None

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test")


def create_sample_image(path: str, size=(1600, 1200), color=(200, 220, 255)) -> None:
    if Image is None:
        raise RuntimeError("Pillow is not installed")
    img = Image.new("RGB", size, color)
    img.save(path, "JPEG", quality=90)


async def maybe_test_telegram(telegram: TelegramService) -> bool:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_GROUP_ID:
        logger.info("Skipping Telegram connectivity test (missing env)")
        return False
    ok = await telegram.test_connection()
    logger.info(f"Telegram connectivity: {'OK' if ok else 'FAILED'}")
    return ok


def maybe_test_instagram(instagram: InstagramService) -> bool:
    if not INSTAGRAM_USERNAME or not INSTAGRAM_PASSWORD:
        logger.info("Skipping Instagram login test (missing env)")
        return False
    ok = instagram.login()
    logger.info(f"Instagram login: {'OK' if ok else 'FAILED'}")
    return ok


async def main() -> None:
    os.makedirs(UPLOADS_DIR, exist_ok=True)

    # Report config presence (non-fatal)
    logger.info(
        "Config snapshot: TG_TOKEN=%s, ADMIN=%s, GROUP=%s, IG_USER=%s", 
        'SET' if bool(TELEGRAM_BOT_TOKEN) else 'MISSING',
        ADMIN_USER_ID,
        TELEGRAM_GROUP_ID if TELEGRAM_GROUP_ID else 'MISSING',
        INSTAGRAM_USERNAME if INSTAGRAM_USERNAME else 'MISSING',
    )

    # Create and process a sample image
    raw_path = os.path.join(UPLOADS_DIR, "sample_raw.jpg")
    create_sample_image(raw_path)
    logger.info("Created sample image: %s", raw_path)

    processor = ImageProcessor()
    assert processor.validate_image(raw_path), "Sample image failed validation"

    processed = processor.process_photos([raw_path])
    logger.info("Processed images: %s", processed)

    # Resize to portrait if applicable
    target = processor.determine_image_format(processed)
    final = [processor.resize_image(p, target) for p in processed]
    logger.info("Final images: %s", final)

    # Optional connectivity checks
    telegram = TelegramService()
    instagram = InstagramService()

    tg_ok = await maybe_test_telegram(telegram)
    ig_ok = maybe_test_instagram(instagram)

    logger.info("Test complete. Telegram OK=%s, Instagram OK=%s", tg_ok, ig_ok)

    # Cleanup generated files
    processor.cleanup_files([raw_path] + processed + final)


if __name__ == "__main__":
    asyncio.run(main())


