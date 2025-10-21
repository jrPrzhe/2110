#!/usr/bin/env python3
"""
Test script for article number detection.
Tests both OCR and AI-based detection methods.
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
from config import GOOGLE_API_KEY

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_article_detection():
    """Test article detection on sample images."""
    
    # Initialize services
    article_extractor = ArticleExtractor()
    ai_service = AIService()
    
    # Test images directory
    test_images_dir = Path("uploads")
    
    if not test_images_dir.exists():
        logger.error("Test images directory 'uploads' not found!")
        return
    
    # Find test images
    test_images = list(test_images_dir.glob("*.jpg")) + list(test_images_dir.glob("*.png"))
    
    if not test_images:
        logger.error("No test images found in 'uploads' directory!")
        return
    
    logger.info(f"Found {len(test_images)} test images")
    
    # Test each image
    for i, image_path in enumerate(test_images[:5]):  # Test first 5 images
        logger.info(f"\n{'='*50}")
        logger.info(f"Testing image {i+1}: {image_path.name}")
        logger.info(f"{'='*50}")
        
        # Test OCR-only detection
        logger.info("🔍 Testing OCR-only detection...")
        ocr_articles = article_extractor.extract_articles_from_image(str(image_path))
        logger.info(f"OCR found: {ocr_articles}")
        
        # Test AI detection (if available)
        if ai_service.enabled:
            logger.info("🤖 Testing AI detection...")
            ai_articles = await ai_service.extract_article_numbers_from_image(str(image_path))
            logger.info(f"AI found: {ai_articles}")
        else:
            logger.warning("AI service not available (no GOOGLE_API_KEY)")
            ai_articles = []
        
        # Test combined detection
        logger.info("🔄 Testing combined detection...")
        combined_articles = article_extractor.extract_articles_from_image(str(image_path), ai_service)
        logger.info(f"Combined found: {combined_articles}")
        
        # Summary
        logger.info(f"📊 Summary for {image_path.name}:")
        logger.info(f"  OCR: {ocr_articles}")
        logger.info(f"  AI: {ai_articles}")
        logger.info(f"  Combined: {combined_articles}")
        
        # Format for caption
        if combined_articles:
            caption_text = article_extractor.format_articles_for_caption(combined_articles)
            logger.info(f"  Caption format: {caption_text}")

def test_enhanced_preprocessing():
    """Test enhanced preprocessing methods."""
    logger.info("\n" + "="*50)
    logger.info("Testing enhanced preprocessing methods")
    logger.info("="*50)
    
    article_extractor = ArticleExtractor()
    test_images_dir = Path("uploads")
    
    if not test_images_dir.exists():
        logger.error("Test images directory 'uploads' not found!")
        return
    
    test_images = list(test_images_dir.glob("*.jpg")) + list(test_images_dir.glob("*.png"))
    
    if not test_images:
        logger.error("No test images found!")
        return
    
    # Test enhanced preprocessing on first image
    image_path = test_images[0]
    logger.info(f"Testing enhanced preprocessing on: {image_path.name}")
    
    enhanced_articles = article_extractor._extract_with_enhanced_preprocessing(str(image_path))
    logger.info(f"Enhanced preprocessing found: {enhanced_articles}")

async def main():
    """Main test function."""
    logger.info("🚀 Starting article detection tests...")
    
    # Test basic detection
    await test_article_detection()
    
    # Test enhanced preprocessing
    test_enhanced_preprocessing()
    
    logger.info("\n✅ All tests completed!")

if __name__ == "__main__":
    asyncio.run(main())
