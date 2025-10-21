#!/usr/bin/env python3
"""
Simple test script for article number detection.
"""

import os
import sys
import asyncio
import logging
from pathlib import Path

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.article_extractor import ArticleExtractor
from services.ai_service import AIService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_single_image():
    """Test article detection on a single image."""
    
    # Initialize services
    article_extractor = ArticleExtractor()
    ai_service = AIService()
    
    # Test with one of the uploaded images
    test_image = "uploads/temp_AgACAgQAAxkBAAMQaPT1_zuGZyvWZU0Cj71uva4xtuoAAh_IMRuxSahTD1kE4GaxYIIBAAMCAAN5AAM2BA.jpg"
    
    if not os.path.exists(test_image):
        logger.error(f"Test image not found: {test_image}")
        return
    
    logger.info(f"Testing image: {test_image}")
    
    # Test OCR-only detection
    logger.info("🔍 Testing OCR-only detection...")
    ocr_articles = article_extractor.extract_articles_from_image(test_image)
    logger.info(f"OCR found: {ocr_articles}")
    
    # Test AI detection (if available)
    if ai_service.enabled:
        logger.info("🤖 Testing AI detection...")
        ai_articles = await ai_service.extract_article_numbers_from_image(test_image)
        logger.info(f"AI found: {ai_articles}")
    else:
        logger.warning("AI service not available (no GOOGLE_API_KEY)")
        ai_articles = []
    
    # Test enhanced preprocessing
    logger.info("🔄 Testing enhanced preprocessing...")
    enhanced_articles = article_extractor._extract_with_enhanced_preprocessing(test_image)
    logger.info(f"Enhanced preprocessing found: {enhanced_articles}")
    
    # Summary
    all_articles = list(set(ocr_articles + ai_articles + enhanced_articles))
    logger.info(f"📊 Summary:")
    logger.info(f"  OCR: {ocr_articles}")
    logger.info(f"  AI: {ai_articles}")
    logger.info(f"  Enhanced: {enhanced_articles}")
    logger.info(f"  Combined: {all_articles}")

if __name__ == "__main__":
    asyncio.run(test_single_image())
