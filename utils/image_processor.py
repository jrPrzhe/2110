"""
Image processing utilities for the Auto-Poster Bot.
Handles image resizing, validation, and format conversion.
"""

import os
import uuid
from PIL import Image, ImageOps
from typing import List, Tuple, Optional
import logging

from config import MAX_IMAGE_SIZE, STORY_IMAGE_SIZE, MAX_FILE_SIZE, SUPPORTED_FORMATS, UPLOADS_DIR
from .article_extractor import ArticleExtractor

logger = logging.getLogger("img")

class ImageProcessor:
    """Handles image processing operations."""
    
    def __init__(self):
        """Initialize the image processor."""
        self.uploads_dir = UPLOADS_DIR
        self.article_extractor = ArticleExtractor()
        self._ensure_uploads_dir()
    
    def _ensure_uploads_dir(self):
        """Ensure the uploads directory exists."""
        if not os.path.exists(self.uploads_dir):
            os.makedirs(self.uploads_dir)
    
    def validate_image(self, file_path: str) -> bool:
        """
        Validate if the image file is valid and meets requirements.
        
        Args:
            file_path: Path to the image file
            
        Returns:
            bool: True if valid, False otherwise
        """
        try:
            # Check file size
            if os.path.getsize(file_path) > MAX_FILE_SIZE:
                logger.warning(f"Image too large: {file_path}")
                return False
            
            # Try to open and validate image
            with Image.open(file_path) as img:
                # Check format
                if img.format not in SUPPORTED_FORMATS:
                    logger.warning(f"Unsupported format: {img.format}")
                    return False
                
                # Check dimensions (must be reasonable)
                width, height = img.size
                if width < 100 or height < 100:
                    logger.warning(f"Image too small: {width}x{height}")
                    return False
                
                if width > 5000 or height > 5000:
                    logger.warning(f"Image too large: {width}x{height}")
                    return False
                
                return True
                
        except Exception as e:
            logger.error(f"Error validating image {file_path}: {e}")
            return False
    
    def resize_image(self, file_path: str, target_size: Tuple[int, int] = None) -> str:
        """
        Resize image to target size while maintaining aspect ratio.
        
        Args:
            file_path: Path to the input image
            target_size: Target size as (width, height). Defaults to MAX_IMAGE_SIZE.
            
        Returns:
            str: Path to the processed image
        """
        if target_size is None:
            target_size = MAX_IMAGE_SIZE
        
        try:
            with Image.open(file_path) as img:
                # Convert to RGB if necessary
                if img.mode in ('RGBA', 'LA', 'P'):
                    # Create white background
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                    img = background
                elif img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Calculate new size maintaining aspect ratio
                original_width, original_height = img.size
                target_width, target_height = target_size
                
                # Calculate scaling factor
                scale_w = target_width / original_width
                scale_h = target_height / original_height
                scale = min(scale_w, scale_h)
                
                new_width = int(original_width * scale)
                new_height = int(original_height * scale)
                
                # Resize image
                resized_img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                
                # Create square canvas if needed
                if target_width == target_height:  # Square format
                    canvas = Image.new('RGB', target_size, (255, 255, 255))
                    # Center the image
                    x = (target_width - new_width) // 2
                    y = (target_height - new_height) // 2
                    canvas.paste(resized_img, (x, y))
                    resized_img = canvas
                
                # Generate output filename
                base_name = os.path.splitext(os.path.basename(file_path))[0]
                output_filename = f"{base_name}_processed_{uuid.uuid4().hex[:8]}.jpg"
                output_path = os.path.join(self.uploads_dir, output_filename)
                
                # Save processed image
                resized_img.save(output_path, 'JPEG', quality=95, optimize=True)
                
                logger.info(f"Image processed: {file_path} -> {output_path}")
                return output_path
                
        except Exception as e:
            logger.error(f"Error processing image {file_path}: {e}")
            raise
    
    def process_photos(self, photo_paths: List[str]) -> List[str]:
        """
        Process a list of photos for posting.
        
        Args:
            photo_paths: List of paths to photo files
            
        Returns:
            List[str]: List of paths to processed photos
            
        Raises:
            ValueError: If any photo is invalid
        """
        if not photo_paths:
            raise ValueError("No photos provided")
        
        if len(photo_paths) > 10:
            raise ValueError("Too many photos (maximum 10)")
        
        processed_paths = []
        
        for photo_path in photo_paths:
            # Validate image
            if not self.validate_image(photo_path):
                raise ValueError(f"Invalid image: {photo_path}")
            
            # Process image
            processed_path = self.resize_image(photo_path)
            processed_paths.append(processed_path)
        
        return processed_paths
    
    def determine_image_format(self, photo_paths: List[str]) -> Tuple[int, int]:
        """
        Determine the best image format based on the photos.
        
        Args:
            photo_paths: List of paths to photo files
            
        Returns:
            Tuple[int, int]: Target size (width, height)
        """
        if len(photo_paths) == 1:
            # Single photo - check if it's more portrait-like
            try:
                with Image.open(photo_paths[0]) as img:
                    width, height = img.size
                    aspect_ratio = height / width
                    
                    # If aspect ratio is significantly taller than 1:1, use story format
                    if aspect_ratio > 1.2:
                        return STORY_IMAGE_SIZE
            except Exception as e:
                logger.warning(f"Error analyzing image aspect ratio: {e}")
        
        # Default to square format
        return MAX_IMAGE_SIZE
    
    def cleanup_files(self, file_paths: List[str]):
        """
        Clean up temporary files.
        
        Args:
            file_paths: List of file paths to delete
        """
        for file_path in file_paths:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    logger.info(f"Cleaned up file: {file_path}")
            except Exception as e:
                logger.error(f"Error cleaning up file {file_path}: {e}")
    
    def cleanup_uploads_dir(self):
        """Clean up all files in the uploads directory."""
        try:
            for filename in os.listdir(self.uploads_dir):
                file_path = os.path.join(self.uploads_dir, filename)
                if os.path.isfile(file_path):
                    os.remove(file_path)
            logger.info("Cleaned up uploads directory")
        except Exception as e:
            logger.error(f"Error cleaning up uploads directory: {e}")
    
    def extract_article_numbers(self, image_paths: List[str], ai_service=None) -> List[str]:
        """
        Extract article numbers from multiple images.
        
        Args:
            image_paths: List of paths to image files
            ai_service: Optional AI service for enhanced detection
            
        Returns:
            List[str]: List of found article numbers
        """
        try:
            if not image_paths:
                return []
            
            logger.info(f"Extracting article numbers from {len(image_paths)} images")
            article_numbers = self.article_extractor.extract_articles_from_multiple_images(image_paths, ai_service)
            
            if article_numbers:
                logger.info(f"Found article numbers: {article_numbers}")
            else:
                logger.warning("No article numbers found in images")
            
            return article_numbers
            
        except Exception as e:
            logger.error(f"Error extracting article numbers: {e}")
            return []
    
    async def extract_article_numbers_async(self, image_paths: List[str], ai_service=None) -> List[str]:
        """
        Extract article numbers from multiple images with AI support.
        
        Args:
            image_paths: List of paths to image files
            ai_service: Optional AI service for enhanced detection
            
        Returns:
            List[str]: List of found article numbers
        """
        try:
            if not image_paths:
                return []
            
            logger.info(f"Extracting article numbers from {len(image_paths)} images")
            
            # First try OCR extraction
            ocr_articles = self.article_extractor.extract_articles_from_multiple_images(image_paths, None)
            all_articles = ocr_articles.copy()
            
            # Then try AI extraction if available
            if ai_service and ai_service.enabled:
                logger.info("Trying AI extraction for all images")
                for image_path in image_paths:
                    try:
                        ai_articles = await ai_service.extract_article_numbers_from_image(image_path)
                        all_articles.extend(ai_articles)
                        logger.info(f"AI found for {image_path}: {ai_articles}")
                    except Exception as e:
                        logger.warning(f"AI extraction failed for {image_path}: {e}")
            
            # Remove duplicates and sort
            unique_articles = list(set(all_articles))
            unique_articles.sort()
            
            if unique_articles:
                logger.info(f"Found article numbers: {unique_articles}")
            else:
                logger.warning("No article numbers found in images")
            
            return unique_articles
            
        except Exception as e:
            logger.error(f"Error extracting article numbers: {e}")
            return []
    
    def format_articles_for_caption(self, article_numbers: List[str]) -> str:
        """
        Format article numbers for inclusion in caption.
        
        Args:
            article_numbers: List of article numbers
            
        Returns:
            str: Formatted string for caption
        """
        return self.article_extractor.format_articles_for_caption(article_numbers)
