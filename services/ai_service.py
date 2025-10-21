"""
AI service for the Auto-Poster Bot.
Handles text improvement using Google AI Studio.
"""

import logging
import aiohttp
import json
from typing import Optional, List

from config import GOOGLE_API_KEY

logger = logging.getLogger("ai")

class AIService:
    """Handles AI operations using Google AI Studio."""
    
    def __init__(self):
        """Initialize the AI service."""
        self.api_key = GOOGLE_API_KEY
        self.base_url = "https://generativelanguage.googleapis.com/v1/models/gemini-2.0-flash:generateContent"
        self.enabled = bool(self.api_key)
    
    async def improve_caption(self, original_caption: str, platform: str = "both") -> Optional[str]:
        """
        Improve a social media caption using Google AI.
        
        Args:
            original_caption: Original caption text
            platform: Target platform ("instagram", "telegram", or "both")
            
        Returns:
            str: Improved caption or None if error
        """
        if not self.enabled:
            logger.warning("AI service is disabled - no API key provided")
            return None
        
        try:
            # Create platform-specific prompt
            platform_instructions = {
                "instagram": "для Instagram (используй хештеги, эмодзи, привлекательный стиль)",
                "telegram": "для Telegram (более деловой стиль, без избытка эмодзи)",
                "both": "для Instagram и Telegram (универсальный стиль с умеренным использованием эмодзи и хештегов)"
            }
            
            platform_instruction = platform_instructions.get(platform, platform_instructions["both"])
            
            prompt = f"""Улучши это описание поста {platform_instruction}:

Требования:
- Должно быть мемно, популярно,  С КЛИКБЕЙТОМ, не много текста, но и не мало
- Сделай текст более привлекательным и интересным
- Добавь подходящие эмодзи (но не слишком много)
- Если это Instagram, добавь 3-5 релевантных хештегов
- Сохрани основную суть сообщения
- Сделай текст читаемым и структурированным
- Максимум 250 символов
-В Итоге должно получиться уже готовое описание поста, которое можно сразу публиковать

Исходный текст: "{original_caption}"

Улучшенный текст:"""

            payload = {
                "contents": [{
                    "parts": [{
                        "text": prompt
                    }]
                }],
                "generationConfig": {
                    "temperature": 0.7,
                    "topK": 40,
                    "topP": 0.95,
                    "maxOutputTokens": 1024,
                }
            }
            
            headers = {
                "Content-Type": "application/json"
            }
            
            url = f"{self.base_url}?key={self.api_key}"
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        if "candidates" in data and len(data["candidates"]) > 0:
                            improved_text = data["candidates"][0]["content"]["parts"][0]["text"]
                            
                            # Clean up the response
                            improved_text = improved_text.strip()
                            
                            # Remove any prefix that might be added by the AI
                            if improved_text.startswith("Улучшенный текст:"):
                                improved_text = improved_text.replace("Улучшенный текст:", "").strip()
                            
                            logger.info(f"AI improved caption: {len(original_caption)} -> {len(improved_text)} chars")
                            return improved_text
                        else:
                            logger.error("No candidates in AI response")
                            return None
                    else:
                        error_text = await response.text()
                        logger.error(f"AI API error {response.status}: {error_text}")
                        return None
                        
        except Exception as e:
            logger.error(f"Error improving caption with AI: {e}")
            return None
    
    async def adapt_reels_caption(self, original_caption: str, platform: str = "both") -> Optional[str]:
        """
        Adapt Instagram reels caption for posting on other platforms.
        
        Args:
            original_caption: Original caption from Instagram reels
            platform: Target platform ('telegram', 'vk', 'both', 'all')
            
        Returns:
            str: Adapted caption or None if failed
        """
        if not self.enabled:
            logger.warning("AI service is disabled - no API key provided")
            return None
        
        try:
            # Platform-specific instructions
            platform_instructions = {
                'telegram': 'Адаптируй для Telegram канала. Используй эмодзи умеренно.',
                'vk': 'Адаптируй для группы ВКонтакте. Используй популярные хештеги ВК.',
                'both': 'Адаптируй для Telegram и ВКонтакте одновременно.',
                'all': 'Адаптируй для Telegram и ВКонтакте одновременно.'
            }
            
            platform_instruction = platform_instructions.get(platform, platform_instructions['both'])
            
            prompt = f"""Ты - эксперт по SMM и контент-маркетингу.

Задача: Адаптировать описание рилса из Instagram для публикации в русскоязычных соцсетях.

Оригинальное описание из Instagram:
"{original_caption}"

Требования:
1. {platform_instruction}
2. Сохрани основной смысл и суть контента
3. Сделай текст более привлекательным и вовлекающим для русскоязычной аудитории
4. Добавь подходящие эмодзи (но не переборщи)
5. Если в оригинале есть хештеги на английском - замени их на русские аналоги
6. Длина: 100-300 символов
7. Убери упоминания Instagram, если они есть
8. Адаптируй стиль под русскоязычную аудиторию
9. Сделай призыв к действию в конце (если уместно)
10. Текст должен быть готов к публикации сразу

Важно: НЕ добавляй лишнюю информацию, которой нет в оригинале. Только адаптируй то, что есть.

Напиши только адаптированный текст, без объяснений:"""
            
            payload = {
                "contents": [{
                    "parts": [{
                        "text": prompt
                    }]
                }],
                "generationConfig": {
                    "temperature": 0.8,
                    "topK": 40,
                    "topP": 0.95,
                    "maxOutputTokens": 512,
                }
            }
            
            headers = {
                "Content-Type": "application/json"
            }
            
            logger.info("Requesting AI to adapt reels caption...")
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}?key={self.api_key}",
                    json=payload,
                    headers=headers
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        if 'candidates' in data and len(data['candidates']) > 0:
                            adapted_text = data['candidates'][0]['content']['parts'][0]['text'].strip()
                            logger.info(f"AI adapted reels caption: {adapted_text[:100]}...")
                            return adapted_text
                        else:
                            logger.error("No candidates in AI response")
                            return None
                    else:
                        error_text = await response.text()
                        logger.error(f"AI API error {response.status}: {error_text}")
                        return None
                        
        except Exception as e:
            logger.error(f"Error adapting reels caption with AI: {e}")
            return None
    
    async def extract_article_numbers_from_image(self, image_path: str) -> List[str]:
        """
        Extract article numbers from image using Google AI Vision.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            List[str]: List of found article numbers
        """
        if not self.enabled:
            logger.warning("AI service is disabled - no API key provided")
            return []
        
        try:
            import base64
            
            # Read and encode image
            with open(image_path, 'rb') as image_file:
                image_data = base64.b64encode(image_file.read()).decode('utf-8')
            
            prompt = """Найди все артикулы (номера товаров) на этом изображении. 
            Артикулы обычно состоят из 7-9 цифр и могут быть написаны крупным шрифтом.
            Верни только номера артикулов, разделенные запятыми, без дополнительного текста.
            Если артикулов нет, верни пустую строку.
            
            Пример ответа: 342278914, 498034552, 286452047"""
            
            payload = {
                "contents": [{
                    "parts": [
                        {"text": prompt},
                        {
                            "inline_data": {
                                "mime_type": "image/jpeg",
                                "data": image_data
                            }
                        }
                    ]
                }],
                "generationConfig": {
                    "temperature": 0.1,
                    "topK": 1,
                    "topP": 0.8,
                    "maxOutputTokens": 100,
                }
            }
            
            headers = {
                "Content-Type": "application/json"
            }
            
            url = f"{self.base_url}?key={self.api_key}"
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        if "candidates" in data and len(data["candidates"]) > 0:
                            result_text = data["candidates"][0]["content"]["parts"][0]["text"]
                            
                            # Parse the result
                            article_numbers = []
                            if result_text.strip():
                                # Split by comma and clean up
                                numbers = [num.strip() for num in result_text.split(',')]
                                # Filter valid article numbers (7-9 digits)
                                for num in numbers:
                                    if num.isdigit() and 7 <= len(num) <= 9:
                                        article_numbers.append(num)
                            
                            logger.info(f"AI found article numbers: {article_numbers}")
                            return article_numbers
                        else:
                            logger.error("No candidates in AI response for article extraction")
                            return []
                    else:
                        error_text = await response.text()
                        logger.error(f"AI API error for article extraction {response.status}: {error_text}")
                        return []
                        
        except Exception as e:
            logger.error(f"Error extracting article numbers with AI: {e}")
            return []
    
    async def test_connection(self) -> bool:
        """
        Test the AI service connection.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        if not self.enabled:
            return False
        
        try:
            test_caption = "Тест"
            result = await self.improve_caption(test_caption)
            return result is not None
        except Exception as e:
            logger.error(f"AI connection test failed: {e}")
            return False
