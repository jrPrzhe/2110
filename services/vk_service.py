"""
VK service for the Auto-Poster Bot.
Handles posting to VK groups.
"""

import logging
import os
from typing import List, Optional
import vk_api
from vk_api import VkUpload

from config import VK_ACCESS_TOKEN, VK_GROUP_ID

logger = logging.getLogger("vk")


class VKService:
    """Handles VK operations."""
    
    def __init__(self):
        """Initialize the VK service."""
        self.access_token = VK_ACCESS_TOKEN
        self.group_id = VK_GROUP_ID
        self.vk_session = None
        self.vk = None
        self.upload = None
        
        if self.access_token:
            self._initialize()
    
    def _initialize(self):
        """Initialize VK API session."""
        try:
            self.vk_session = vk_api.VkApi(token=self.access_token)
            self.vk = self.vk_session.get_api()
            self.upload = VkUpload(self.vk_session)
            logger.info("VK service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize VK service: {e}")
            raise
    
    def _upload_photo_to_wall(self, photo_path: str) -> Optional[dict]:
        """
        Upload a photo to VK wall.
        
        Args:
            photo_path: Path to the photo file
            
        Returns:
            dict: Photo object with owner_id and id, or None if failed
        """
        try:
            # Upload photo to wall
            photo = self.upload.photo_wall(
                photo_path,
                group_id=self.group_id
            )
            
            if photo and len(photo) > 0:
                return photo[0]
            else:
                logger.error("Photo upload returned empty result")
                return None
                
        except Exception as e:
            logger.error(f"Error uploading photo to VK: {e}")
            return None
    
    async def post_photo(self, photo_path: str, caption: str) -> bool:
        """
        Post a single photo to the VK group.
        
        Args:
            photo_path: Path to the photo file
            caption: Caption for the post
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if not self.vk:
                logger.error("VK service not initialized")
                return False
            
            logger.info(f"Posting single photo to VK group: {photo_path}")
            
            # Upload photo
            photo = self._upload_photo_to_wall(photo_path)
            if not photo:
                return False
            
            # Create attachment string
            attachment = f"photo{photo['owner_id']}_{photo['id']}"
            
            # Post to wall
            self.vk.wall.post(
                owner_id=-int(self.group_id),  # Negative for groups
                from_group=1,
                message=caption,
                attachments=attachment
            )
            
            logger.info("Photo posted successfully to VK group")
            return True
            
        except Exception as e:
            logger.error(f"Error posting photo to VK: {e}")
            return False
    
    async def post_album(self, photo_paths: List[str], caption: str) -> bool:
        """
        Post an album (multiple photos) to the VK group.
        
        Args:
            photo_paths: List of paths to photo files
            caption: Caption for the post
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if not self.vk:
                logger.error("VK service not initialized")
                return False
            
            if len(photo_paths) < 2:
                logger.warning("Album requires at least 2 photos, posting as single photo instead")
                return await self.post_photo(photo_paths[0], caption)
            
            if len(photo_paths) > 10:
                logger.warning("VK supports max 10 photos in album, truncating...")
                photo_paths = photo_paths[:10]
            
            logger.info(f"Posting album to VK group with {len(photo_paths)} photos")
            
            # Upload all photos
            attachments = []
            for photo_path in photo_paths:
                photo = self._upload_photo_to_wall(photo_path)
                if photo:
                    attachment = f"photo{photo['owner_id']}_{photo['id']}"
                    attachments.append(attachment)
                else:
                    logger.warning(f"Failed to upload photo: {photo_path}")
            
            if not attachments:
                logger.error("No photos were uploaded successfully")
                return False
            
            # Post to wall with all attachments
            self.vk.wall.post(
                owner_id=-int(self.group_id),  # Negative for groups
                from_group=1,
                message=caption,
                attachments=','.join(attachments)
            )
            
            logger.info("Album posted successfully to VK group")
            return True
            
        except Exception as e:
            logger.error(f"Error posting album to VK: {e}")
            return False
    
    async def post_to_vk(self, photo_paths: List[str], caption: str) -> bool:
        """
        Post photos to VK group (single or album based on count).
        
        Args:
            photo_paths: List of paths to photo files
            caption: Caption for the post
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not photo_paths:
            logger.error("No photos provided for VK post")
            return False
        
        if not self.vk:
            logger.error("VK service not initialized - check VK_ACCESS_TOKEN in .env")
            return False
        
        if len(photo_paths) == 1:
            return await self.post_photo(photo_paths[0], caption)
        else:
            return await self.post_album(photo_paths, caption)
    
    async def post_video(self, video_path: str, caption: str) -> bool:
        """
        Post a video to the VK group.
        
        Args:
            video_path: Path to the video file
            caption: Caption for the post
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if not self.vk:
                logger.error("VK service not initialized")
                return False
            
            logger.info(f"Posting video to VK group: {video_path}")
            
            # Step 1: Get video upload server
            logger.info("Getting VK video upload server...")
            upload_server = self.vk.video.save(
                group_id=self.group_id,
                name=caption[:100] if len(caption) > 100 else caption,  # VK limit for name
                description=caption,
                is_private=0,
                wallpost=0  # Don't auto-post, we'll post manually with caption
            )
            
            logger.info(f"Upload URL: {upload_server['upload_url']}")
            
            # Step 2: Upload video to server
            import requests
            import os
            import time
            from requests.adapters import HTTPAdapter
            from urllib3.util.retry import Retry
            
            # Check file size
            file_size_mb = os.path.getsize(video_path) / (1024 * 1024)
            logger.info(f"Video file size: {file_size_mb:.2f} MB")
            
            logger.info("Uploading video file to VK...")
            
            # Create session with retry strategy
            session = requests.Session()
            retry_strategy = Retry(
                total=5,  # Maximum number of retries
                backoff_factor=2,  # Wait 1, 2, 4, 8, 16 seconds between retries
                status_forcelist=[429, 500, 502, 503, 504],
                allowed_methods=["POST"]
            )
            adapter = HTTPAdapter(max_retries=retry_strategy)
            session.mount("http://", adapter)
            session.mount("https://", adapter)
            
            # Try uploading with retries
            max_attempts = 3
            response = None
            upload_success = False
            
            for attempt in range(max_attempts):
                try:
                    logger.info(f"Upload attempt {attempt + 1}/{max_attempts}")
                    
                    with open(video_path, 'rb') as video_file:
                        response = session.post(
                            upload_server['upload_url'],
                            files={'video_file': video_file},
                            timeout=None  # No timeout for large files
                        )
                    
                    if response.status_code == 200:
                        logger.info("Video file uploaded successfully")
                        upload_success = True
                        break
                    else:
                        logger.error(f"Failed to upload video to VK: {response.status_code}")
                        if attempt < max_attempts - 1:
                            wait_time = 2 ** attempt
                            logger.info(f"Retrying in {wait_time} seconds...")
                            time.sleep(wait_time)
                            
                except (requests.exceptions.SSLError, requests.exceptions.ConnectionError) as e:
                    logger.error(f"SSL/Connection error on attempt {attempt + 1}: {e}")
                    if attempt < max_attempts - 1:
                        wait_time = 2 ** attempt
                        logger.info(f"Retrying in {wait_time} seconds...")
                        time.sleep(wait_time)
                        
                except Exception as e:
                    logger.error(f"Unexpected error uploading video: {e}")
                    import traceback
                    logger.error(f"Traceback: {traceback.format_exc()}")
                    if attempt < max_attempts - 1:
                        wait_time = 2 ** attempt
                        logger.info(f"Retrying in {wait_time} seconds...")
                        time.sleep(wait_time)
            
            if not upload_success or not response or response.status_code != 200:
                logger.error(f"Failed to upload video to VK after all attempts")
                return False
            
            # Step 3: Get video info from response
            video_data = response.json()
            logger.info(f"Video data: {video_data}")
            
            # The video is being processed by VK, we need to wait and then post
            # VK returns video_id and owner_id in the upload_server response
            if 'video_id' in upload_server:
                video_id = upload_server['video_id']
                owner_id = upload_server['owner_id']
            else:
                logger.error("No video_id in response")
                return False
            
            # Step 4: Post video to wall with caption
            logger.info(f"Posting video to wall: video{owner_id}_{video_id}")
            attachment = f"video{owner_id}_{video_id}"
            
            self.vk.wall.post(
                owner_id=-int(self.group_id),  # Negative for groups
                from_group=1,
                message=caption,
                attachments=attachment
            )
            
            logger.info("Video posted successfully to VK group with caption")
            return True
            
        except Exception as e:
            logger.error(f"Error posting video to VK: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return False
    
    def test_connection(self) -> bool:
        """
        Test the VK API connection.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            if not self.vk:
                logger.error("VK service not initialized")
                return False
            
            # Get group info to test connection
            group_info = self.vk.groups.getById(group_id=self.group_id)
            if group_info and len(group_info) > 0:
                logger.info(f"VK connection successful: {group_info[0].get('name', 'Unknown')}")
                return True
            else:
                logger.error("Failed to get VK group info")
                return False
                
        except Exception as e:
            logger.error(f"VK connection test failed: {e}")
            return False

