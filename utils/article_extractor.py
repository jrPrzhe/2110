"""
Article number extractor utility for the Auto-Poster Bot.
Extracts article numbers (7-9 digits) from images using OCR.
"""

import os
import re
import logging
import cv2
import numpy as np
from PIL import Image
import pytesseract
from typing import List, Optional, Tuple

logger = logging.getLogger("article_extractor")

class ArticleExtractor:
    """Extracts article numbers from images using OCR."""
    
    def __init__(self):
        """Initialize the article extractor."""
        # Configure tesseract for better number recognition
        self.tesseract_config = '--oem 3 --psm 6 -c tessedit_char_whitelist=0123456789'
        
    def preprocess_image(self, image_path: str) -> np.ndarray:
        """
        Preprocess image for better OCR recognition.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            np.ndarray: Preprocessed image
        """
        try:
            # Read image
            image = cv2.imread(image_path)
            if image is None:
                logger.error(f"Could not read image: {image_path}")
                return None
            
            # Convert to grayscale
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Resize image for better OCR (scale up if too small)
            height, width = gray.shape
            if height < 1000 or width < 1000:
                scale_factor = max(1000 / height, 1000 / width)
                new_width = int(width * scale_factor)
                new_height = int(height * scale_factor)
                gray = cv2.resize(gray, (new_width, new_height), interpolation=cv2.INTER_CUBIC)
            
            # Try multiple preprocessing approaches
            processed_images = []
            
            # Approach 1: OTSU threshold
            _, thresh1 = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            processed_images.append(("OTSU", thresh1))
            
            # Approach 2: Adaptive threshold
            thresh2 = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
            processed_images.append(("Adaptive", thresh2))
            
            # Approach 3: OTSU with blur
            blurred = cv2.GaussianBlur(gray, (3, 3), 0)
            _, thresh3 = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            processed_images.append(("OTSU+Blur", thresh3))
            
            # Approach 4: Morphological operations
            kernel = np.ones((2, 2), np.uint8)
            cleaned = cv2.morphologyEx(thresh1, cv2.MORPH_CLOSE, kernel)
            processed_images.append(("Morphology", cleaned))
            
            # Approach 5: Inverted image
            inverted = cv2.bitwise_not(thresh1)
            processed_images.append(("Inverted", inverted))
            
            # Return the first processed image (OTSU) as default
            # The OCR will try multiple configurations anyway
            return thresh1
            
        except Exception as e:
            logger.error(f"Error preprocessing image {image_path}: {e}")
            return None
    
    def extract_text_from_image(self, image_path: str) -> str:
        """
        Extract text from image using OCR.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            str: Extracted text
        """
        try:
            # Preprocess image
            processed_image = self.preprocess_image(image_path)
            if processed_image is None:
                return ""
            
            # Try multiple OCR configurations for better recognition
            texts = []
            
            # Configuration 1: Default settings
            text1 = pytesseract.image_to_string(processed_image, config=self.tesseract_config)
            texts.append(("Default", text1.strip()))
            
            # Configuration 2: Different PSM mode
            text2 = pytesseract.image_to_string(processed_image, config='--oem 3 --psm 8 -c tessedit_char_whitelist=0123456789')
            texts.append(("PSM 8", text2.strip()))
            
            # Configuration 3: Single text line
            text3 = pytesseract.image_to_string(processed_image, config='--oem 3 --psm 7 -c tessedit_char_whitelist=0123456789')
            texts.append(("PSM 7", text3.strip()))
            
            # Configuration 4: Single word
            text4 = pytesseract.image_to_string(processed_image, config='--oem 3 --psm 8 -c tessedit_char_whitelist=0123456789')
            texts.append(("PSM 8", text4.strip()))
            
            # Log all extracted texts for debugging
            logger.info(f"OCR results for {image_path}:")
            for config_name, text in texts:
                if text:
                    logger.info(f"  {config_name}: '{text}'")
                else:
                    logger.info(f"  {config_name}: (empty)")
            
            # Use the text with most numbers found
            best_text = ""
            max_numbers = 0
            for config_name, text in texts:
                if text:
                    numbers = re.findall(r'\d+', text)
                    if len(numbers) > max_numbers:
                        max_numbers = len(numbers)
                        best_text = text
            
            if not best_text:
                # If no text found, try without whitelist
                logger.info("Trying OCR without character whitelist...")
                text_no_whitelist = pytesseract.image_to_string(processed_image, config='--oem 3 --psm 6')
                if text_no_whitelist.strip():
                    logger.info(f"OCR without whitelist: '{text_no_whitelist.strip()}'")
                    best_text = text_no_whitelist.strip()
            
            logger.info(f"Selected best text: '{best_text}'")
            return best_text
            
        except Exception as e:
            logger.error(f"Error extracting text from {image_path}: {e}")
            return ""
    
    def find_article_numbers(self, text: str) -> List[str]:
        """
        Find article numbers (7-9 digits) in the extracted text.
        
        Args:
            text: Text extracted from image
            
        Returns:
            List[str]: List of found article numbers
        """
        try:
            if not text:
                return []
            
            # Try multiple patterns for better recognition
            patterns = [
                r'\b\d{7,9}\b',  # Word boundaries
                r'\d{7,9}',      # Any 7-9 digits
                r'(?<!\d)\d{7,9}(?!\d)',  # Not preceded or followed by digits
            ]
            
            all_matches = []
            for i, pattern in enumerate(patterns):
                matches = re.findall(pattern, text)
                logger.info(f"Pattern {i+1} ({pattern}): {matches}")
                all_matches.extend(matches)
            
            # Also try to find numbers that might be separated by spaces or other characters
            # Split text and look for 7-9 digit sequences
            words = re.split(r'[^\d]', text)
            for word in words:
                if len(word) >= 7 and len(word) <= 9 and word.isdigit():
                    all_matches.append(word)
            
            # Remove duplicates and sort
            unique_matches = list(set(all_matches))
            unique_matches.sort()
            
            # Filter out numbers that are too short or too long
            filtered_matches = [match for match in unique_matches if 7 <= len(match) <= 9]
            
            logger.info(f"All matches: {unique_matches}")
            logger.info(f"Filtered article numbers (7-9 digits): {filtered_matches}")
            return filtered_matches
            
        except Exception as e:
            logger.error(f"Error finding article numbers: {e}")
            return []
    
    def extract_articles_from_image(self, image_path: str, ai_service=None) -> List[str]:
        """
        Extract article numbers from a single image using both OCR and AI.
        
        Args:
            image_path: Path to the image file
            ai_service: Optional AI service for enhanced detection
            
        Returns:
            List[str]: List of found article numbers
        """
        try:
            if not os.path.exists(image_path):
                logger.error(f"Image file not found: {image_path}")
                return []
            
            all_articles = []
            
            # Method 1: OCR-based extraction
            logger.info(f"Trying OCR extraction for {image_path}")
            text = self.extract_text_from_image(image_path)
            if text:
                ocr_articles = self.find_article_numbers(text)
                all_articles.extend(ocr_articles)
                logger.info(f"OCR found: {ocr_articles}")
            
            # Method 2: AI-based extraction (if available)
            if ai_service and ai_service.enabled:
                try:
                    logger.info(f"Trying AI extraction for {image_path}")
                    # Skip AI extraction in sync context - will be handled in async context
                    logger.info("AI extraction skipped in sync context")
                except Exception as e:
                    logger.warning(f"AI extraction failed: {e}")
            
            # Method 3: Enhanced image preprocessing for OCR
            if not all_articles:
                logger.info(f"Trying enhanced preprocessing for {image_path}")
                enhanced_articles = self._extract_with_enhanced_preprocessing(image_path)
                all_articles.extend(enhanced_articles)
                logger.info(f"Enhanced preprocessing found: {enhanced_articles}")
            
            # Remove duplicates and sort
            unique_articles = list(set(all_articles))
            unique_articles.sort()
            
            logger.info(f"Final article numbers for {image_path}: {unique_articles}")
            return unique_articles
            
        except Exception as e:
            logger.error(f"Error extracting articles from {image_path}: {e}")
            return []
    
    def _extract_with_enhanced_preprocessing(self, image_path: str) -> List[str]:
        """
        Extract article numbers using enhanced image preprocessing.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            List[str]: List of found article numbers
        """
        try:
            # Read image
            image = cv2.imread(image_path)
            if image is None:
                return []
            
            # Convert to grayscale
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Resize for better OCR
            height, width = gray.shape
            if height < 2000 or width < 2000:
                scale_factor = max(2000 / height, 2000 / width)
                new_width = int(width * scale_factor)
                new_height = int(height * scale_factor)
                gray = cv2.resize(gray, (new_width, new_height), interpolation=cv2.INTER_CUBIC)
            
            # Try multiple preprocessing techniques
            processed_images = []
            
            # 1. High contrast
            clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
            enhanced = clahe.apply(gray)
            processed_images.append(("High Contrast", enhanced))
            
            # 2. Edge detection
            edges = cv2.Canny(gray, 50, 150)
            processed_images.append(("Edge Detection", edges))
            
            # 3. Morphological operations
            kernel = np.ones((3,3), np.uint8)
            morphed = cv2.morphologyEx(gray, cv2.MORPH_CLOSE, kernel)
            processed_images.append(("Morphology", morphed))
            
            # 4. Gaussian blur + threshold
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)
            _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            processed_images.append(("Blur + OTSU", thresh))
            
            # 5. Adaptive threshold with different parameters
            adaptive1 = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 15, 10)
            processed_images.append(("Adaptive Mean", adaptive1))
            
            adaptive2 = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 15, 10)
            processed_images.append(("Adaptive Gaussian", adaptive2))
            
            # Try OCR on each processed image
            all_articles = []
            for name, processed_img in processed_images:
                try:
                    # Try different OCR configurations
                    configs = [
                        '--oem 3 --psm 6 -c tessedit_char_whitelist=0123456789',
                        '--oem 3 --psm 8 -c tessedit_char_whitelist=0123456789',
                        '--oem 3 --psm 7 -c tessedit_char_whitelist=0123456789',
                        '--oem 3 --psm 13 -c tessedit_char_whitelist=0123456789',
                    ]
                    
                    for config in configs:
                        text = pytesseract.image_to_string(processed_img, config=config)
                        if text.strip():
                            articles = self.find_article_numbers(text)
                            if articles:
                                all_articles.extend(articles)
                                logger.info(f"Enhanced preprocessing ({name}) with config {config}: {articles}")
                except Exception as e:
                    logger.warning(f"Error in enhanced preprocessing {name}: {e}")
            
            # Remove duplicates
            unique_articles = list(set(all_articles))
            return unique_articles
            
        except Exception as e:
            logger.error(f"Error in enhanced preprocessing: {e}")
            return []
    
    def extract_articles_from_multiple_images(self, image_paths: List[str], ai_service=None) -> List[str]:
        """
        Extract article numbers from multiple images.
        
        Args:
            image_paths: List of paths to image files
            ai_service: Optional AI service for enhanced detection
            
        Returns:
            List[str]: List of all found article numbers (unique)
        """
        try:
            all_articles = []
            
            for image_path in image_paths:
                articles = self.extract_articles_from_image(image_path, ai_service)
                all_articles.extend(articles)
            
            # Remove duplicates and sort
            unique_articles = list(set(all_articles))
            unique_articles.sort()
            
            logger.info(f"Total unique article numbers found: {unique_articles}")
            return unique_articles
            
        except Exception as e:
            logger.error(f"Error extracting articles from multiple images: {e}")
            return []
    
    def format_articles_for_caption(self, article_numbers: List[str]) -> str:
        """
        Format article numbers for inclusion in caption.
        
        Args:
            article_numbers: List of article numbers
            
        Returns:
            str: Formatted string for caption
        """
        if not article_numbers:
            return ""
        
        if len(article_numbers) == 1:
            return f"Артикул: {article_numbers[0]}"
        else:
            articles_str = ", ".join(article_numbers)
            return f"Артикулы: {articles_str}"
