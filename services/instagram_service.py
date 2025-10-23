"""
Instagram service for the Auto-Poster Bot.
Handles Instagram login, session management, and photo posting.
"""

import os
import time
import logging
from typing import List, Optional
from instagrapi import Client
from instagrapi.exceptions import LoginRequired, ChallengeRequired, TwoFactorRequired

from config import INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD, INSTAGRAM_SESSIONID, SESSIONS_DIR

logger = logging.getLogger("ig")


class InstagramService:
    """Handles Instagram operations."""

    def __init__(self):
        """Initialize the Instagram service."""
        self.client = Client()
        # Set longer timeouts for better stability (especially for video downloads)
        self.client.request_timeout = 30  # 30 seconds for general requests
        self.client.private.request_timeout = 30  # 30 seconds for private API
        self.username = INSTAGRAM_USERNAME
        self.password = INSTAGRAM_PASSWORD
        # Use a stable session file to preserve exact session across restarts
        self.session_file = os.path.join(SESSIONS_DIR, "session.json")
        self._ensure_sessions_dir()

    def _ensure_sessions_dir(self):
        """Ensure the sessions directory exists."""
        if not os.path.exists(SESSIONS_DIR):
            os.makedirs(SESSIONS_DIR)
    
    def reset_session(self) -> bool:
        """
        Reset Instagram session completely.
        Deletes session file and reinitializes the client.
        
        Returns:
            bool: True if reset and login successful, False otherwise
        """
        try:
            logger.info("Resetting Instagram session...")
            
            # Step 1: Delete session file if exists
            if os.path.exists(self.session_file):
                try:
                    os.remove(self.session_file)
                    logger.info(f"Deleted session file: {self.session_file}")
                except Exception as e:
                    logger.error(f"Failed to delete session file: {e}")
                    return False
            else:
                logger.info("No session file found to delete")
            
            # Step 2: Recreate client from scratch
            logger.info("Recreating Instagram client...")
            self.client = Client()
            # Set longer timeouts for better stability
            self.client.request_timeout = 30
            self.client.private.request_timeout = 30
            
            # Step 3: Try to login with fresh client
            logger.info("Attempting fresh login...")
            login_success = self.login()
            
            if login_success:
                logger.info("Instagram session reset successful")
                return True
            else:
                logger.error("Instagram session reset failed - login unsuccessful")
                return False
                
        except Exception as e:
            logger.error(f"Error during session reset: {e}")
            return False

    def login(self) -> bool:
        """
        Login to Instagram with session caching.

        Returns:
            bool: True if login successful, False otherwise
        """
        try:
            # 1. Try login via sessionid if provided
            if INSTAGRAM_SESSIONID:
                try:
                    logger.info("Attempting login via sessionid cookie...")
                    self.client.set_settings({})  # Clear to avoid conflicts
                    self.client.login_by_sessionid(INSTAGRAM_SESSIONID)
                    # Validate session
                    if self.is_logged_in():
                        if INSTAGRAM_USERNAME:
                            self.client.dump_settings(self.session_file)
                        logger.info("Instagram login successful (sessionid)")
                        return True
                    else:
                        raise Exception("Sessionid login did not yield valid session")
                except Exception as e:
                    logger.warning(f"Sessionid login failed: {e}. Falling back to session file / credentials.")

            # 2. Try loading existing session file
            if os.path.exists(self.session_file):
                logger.info("Loading existing Instagram session...")
                try:
                    self.client.load_settings(self.session_file)
                    if self.is_logged_in():
                        logger.info("Instagram login successful (session loaded)")
                        return True
                    else:
                        logger.warning("Loaded session is invalid.")
                except Exception as e:
                    logger.warning(f"Failed to load session file: {e}")

            # 3. Perform fresh login with credentials
            if not (self.username and self.password):
                raise Exception("Missing INSTAGRAM_USERNAME/INSTAGRAM_PASSWORD and sessionid login failed")

            logger.info("Performing fresh Instagram login...")
            self.client.login(self.username, self.password)

            # Save session for future use
            self.client.dump_settings(self.session_file)

            # Final validation
            if self.is_logged_in():
                logger.info("Instagram login successful (fresh login)")
                return True
            else:
                raise Exception("Fresh login succeeded but session is not valid")

        except Exception as e:
            logger.error(f"Instagram login failed: {e}")
            return False

    def is_logged_in(self) -> bool:
        """Check login by calling a lightweight private endpoint."""
        try:
            # account_info() is lighter than get_timeline_feed()
            self.client.account_info()
            return True
        except Exception:
            return False

    def post_photo(self, photo_path: str, caption: str) -> bool:
        """
        Post a single photo to Instagram.

        Args:
            photo_path: Path to the photo file
            caption: Caption for the post

        Returns:
            bool: True if successful, False otherwise
        """
        def _attempt_upload() -> bool:
            logger.info(f"Posting single photo to Instagram: {photo_path}")
            # No "warm-up" — rely on is_logged_in() instead
            time.sleep(1.0)  # Small delay to avoid rate-limiting
            self.client.photo_upload(photo_path, caption)
            logger.info("Photo posted successfully to Instagram")
            return True

        # Ensure logged in before attempting upload
        if not self.is_logged_in():
            logger.warning("Not logged in to Instagram, attempting login...")
            if not self.login():
                return False

        try:
            return _attempt_upload()
        except Exception as e:
            message = str(e)
            logger.error(f"Error posting photo to Instagram: {message}")
            # Retry once on auth-related errors
            if any(err in message for err in ("login_required", "LoginRequired", "user_has_logged_out")):
                logger.warning("login_required during upload, attempting session reload and retry once...")
                # Reload session if exists
                if os.path.exists(self.session_file):
                    try:
                        self.client.load_settings(self.session_file)
                    except Exception as load_err:
                        logger.warning(f"Failed to reload session: {load_err}")
                # Re-login if still not valid
                if not self.is_logged_in():
                    if not self.login():
                        return False
                # Retry upload
                try:
                    return _attempt_upload()
                except Exception as e2:
                    logger.error(f"Retry failed: {e2}")
                    return False
            return False

    def post_album(self, photo_paths: List[str], caption: str) -> bool:
        """
        Post an album (carousel) to Instagram.

        Args:
            photo_paths: List of paths to photo files
            caption: Caption for the post

        Returns:
            bool: True if successful, False otherwise
        """
        def _attempt_album() -> bool:
            if len(photo_paths) < 2:
                logger.warning("Album requires at least 2 photos, posting as single photo instead")
                return self.post_photo(photo_paths[0], caption)
            if len(photo_paths) > 10:
                logger.warning("Instagram supports max 10 photos in album, truncating...")
                limited_paths = photo_paths[:10]
            else:
                limited_paths = photo_paths
            logger.info(f"Posting album to Instagram with {len(limited_paths)} photos")
            time.sleep(1.0)
            self.client.album_upload(limited_paths, caption)
            logger.info("Album posted successfully to Instagram")
            return True

        if not self.is_logged_in():
            logger.warning("Not logged in to Instagram, attempting login...")
            if not self.login():
                return False

        try:
            return _attempt_album()
        except Exception as e:
            message = str(e)
            logger.error(f"Error posting album to Instagram: {message}")
            if any(err in message for err in ("login_required", "LoginRequired", "user_has_logged_out")):
                logger.warning("login_required during album upload, attempting session reload and retry once...")
                if os.path.exists(self.session_file):
                    try:
                        self.client.load_settings(self.session_file)
                    except Exception as load_err:
                        logger.warning(f"Failed to reload session: {load_err}")
                if not self.is_logged_in():
                    if not self.login():
                        return False
                try:
                    return _attempt_album()
                except Exception as e2:
                    logger.error(f"Retry failed: {e2}")
                    return False
            return False

    def post_video(self, video_path: str, caption: str) -> bool:
        """
        Post a video to Instagram as a regular post (not reels).

        Args:
            video_path: Path to the video file
            caption: Caption for the post

        Returns:
            bool: True if successful, False otherwise
        """
        def _attempt_video_upload() -> bool:
            logger.info(f"Posting video to Instagram: {video_path}")
            time.sleep(1.0)  # Small delay to avoid rate-limiting
            self.client.video_upload(video_path, caption)
            logger.info("Video posted successfully to Instagram")
            return True

        # Ensure logged in before attempting upload
        if not self.is_logged_in():
            logger.warning("Not logged in to Instagram, attempting login...")
            if not self.login():
                return False

        try:
            return _attempt_video_upload()
        except Exception as e:
            message = str(e)
            logger.error(f"Error posting video to Instagram: {message}")
            # Retry once on auth-related errors
            if any(err in message for err in ("login_required", "LoginRequired", "user_has_logged_out")):
                logger.warning("login_required during video upload, attempting session reload and retry once...")
                # Reload session if exists
                if os.path.exists(self.session_file):
                    try:
                        self.client.load_settings(self.session_file)
                    except Exception as load_err:
                        logger.warning(f"Failed to reload session: {load_err}")
                # Re-login if still not valid
                if not self.is_logged_in():
                    if not self.login():
                        return False
                # Retry upload
                try:
                    return _attempt_video_upload()
                except Exception as e2:
                    logger.error(f"Retry failed: {e2}")
                    return False
            return False

    def post_to_instagram(self, photo_paths: List[str], caption: str) -> bool:
        """
        Post photos to Instagram (single or album based on count).

        Args:
            photo_paths: List of paths to photo files
            caption: Caption for the post

        Returns:
            bool: True if successful, False otherwise
        """
        if not photo_paths:
            logger.error("No photos provided for Instagram post")
            return False

        if len(photo_paths) == 1:
            return self.post_photo(photo_paths[0], caption)
        else:
            return self.post_album(photo_paths, caption)
    
    def create_draft_with_music_instructions(self, photo_paths: List[str], caption: str) -> bool:
        """
        Create a draft post with instructions for adding New Year music.
        This posts the content and provides instructions for manual music addition.

        Args:
            photo_paths: List of paths to photo files
            caption: Caption for the post

        Returns:
            bool: True if successful, False otherwise
        """
        if not photo_paths:
            logger.error("No photos provided for Instagram draft")
            return False

        # Add music instructions to caption
        music_instructions = """

🎵 ДОБАВЬТЕ НОВОГОДНЮЮ МУЗЫКУ:
1. Откройте этот пост в Instagram
2. Нажмите "Редактировать" 
3. Выберите "Добавить музыку"
4. Найдите новогодние треки в библиотеке
5. Сохраните изменения

#новыйгод #музыка #праздник"""
        
        enhanced_caption = caption + music_instructions
        
        # Post normally with enhanced caption
        if len(photo_paths) == 1:
            return self.post_photo(photo_paths[0], enhanced_caption)
        else:
            return self.post_album(photo_paths, enhanced_caption)

    def logout(self):
        """Logout from Instagram and clean up session."""
        try:
            if self.is_logged_in():
                self.client.logout()
                logger.info("Logged out from Instagram")
        except Exception as e:
            logger.error(f"Error during Instagram logout: {e}")

    def get_user_info(self) -> Optional[dict]:
        """
        Get current user information.

        Returns:
            dict: User information or None if not logged in
        """
        try:
            if self.is_logged_in():
                return self.client.user_info(self.client.user_id)
            return None
        except Exception as e:
            logger.error(f"Error getting user info: {e}")
            return None
    
    def download_reels(self, url: str, progress_callback=None, cancel_check=None) -> Optional[str]:
        """
        Download reels/video from Instagram URL.
        
        Args:
            url: Instagram reels/video URL
            progress_callback: Optional callback function(downloaded, total) for progress updates
            cancel_check: Optional function that returns True if download should be cancelled
            
        Returns:
            str: Path to downloaded video file or None if failed
        """
        try:
            # Try method 1: Using instagrapi with login
            logger.info(f"Attempting to download reels from URL: {url}")
            
            # Try to use existing session first
            if not self.is_logged_in():
                logger.warning("Not logged in to Instagram, attempting login...")
                if not self.login():
                    logger.error("Failed to login to Instagram, trying alternative method")
                    # Try alternative method without login
                    return self._download_reels_alternative(url, progress_callback, cancel_check)
            
            logger.info(f"Downloading reels from URL: {url}")
            
            # Extract media ID from URL
            try:
                media_pk = self.client.media_pk_from_url(url)
                logger.info(f"Extracted media PK: {media_pk}")
            except Exception as e:
                logger.error(f"Failed to extract media PK: {e}")
                return self._download_reels_alternative(url, progress_callback, cancel_check)
            
            # Get media info
            try:
                media_info = self.client.media_info(media_pk)
                logger.info(f"Media type: {media_info.media_type}")
            except Exception as e:
                logger.error(f"Failed to get media info: {e}")
                return self._download_reels_alternative(url, progress_callback, cancel_check)
            
            # Check if it's a video/reels
            if media_info.media_type not in [2, 8]:  # 2 = video, 8 = album with video
                logger.error(f"Media is not a video/reels (type: {media_info.media_type})")
                return None
            
            # Download video
            from config import UPLOADS_DIR
            if not os.path.exists(UPLOADS_DIR):
                os.makedirs(UPLOADS_DIR)
            
            try:
                video_path = self.client.video_download(media_pk, folder=UPLOADS_DIR)
                
                if video_path and os.path.exists(video_path):
                    logger.info(f"Reels downloaded successfully: {video_path}")
                    return str(video_path)
                else:
                    logger.error("Failed to download reels via instagrapi")
                    return self._download_reels_alternative(url, progress_callback, cancel_check)
            except Exception as e:
                logger.error(f"Error during video download: {e}")
                return self._download_reels_alternative(url, progress_callback, cancel_check)
                
        except Exception as e:
            logger.error(f"Error downloading reels: {e}")
            return self._download_reels_alternative(url, progress_callback, cancel_check)
    
    def get_reels_caption(self, url: str) -> Optional[str]:
        """
        Get caption/description from Instagram reels.
        
        Args:
            url: Instagram reels URL
            
        Returns:
            str: Caption text or None if failed
        """
        try:
            logger.info(f"Getting caption from reels: {url}")
            
            # Try with login first
            if self.is_logged_in():
                try:
                    media_pk = self.client.media_pk_from_url(url)
                    media_info = self.client.media_info(media_pk)
                    
                    if media_info.caption_text:
                        logger.info(f"Caption extracted via API: {media_info.caption_text[:100]}...")
                        return media_info.caption_text
                except Exception as e:
                    logger.warning(f"Failed to get caption via API: {e}")
            
            # Alternative method - parse from embed page
            import requests
            import re
            
            shortcode_match = re.search(r'/reel/([A-Za-z0-9_-]+)', url)
            if not shortcode_match:
                logger.error("Could not extract shortcode from URL")
                return None
            
            shortcode = shortcode_match.group(1)
            embed_url = f"https://www.instagram.com/p/{shortcode}/embed/"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(embed_url, headers=headers, timeout=30)
            
            if response.status_code != 200:
                logger.error(f"Failed to fetch embed page: {response.status_code}")
                return None
            
            # Try to extract caption from embed page
            caption_match = re.search(r'"caption":"([^"]*)"', response.text)
            if caption_match:
                caption = caption_match.group(1)
                # Decode unicode escapes
                caption = caption.encode().decode('unicode_escape')
                logger.info(f"Caption extracted from embed: {caption[:100]}...")
                return caption
            
            # Try alternative pattern
            caption_match = re.search(r'<meta property="og:description" content="([^"]*)"', response.text)
            if caption_match:
                caption = caption_match.group(1)
                logger.info(f"Caption extracted from meta: {caption[:100]}...")
                return caption
            
            logger.warning("Could not find caption in embed page")
            return None
            
        except Exception as e:
            logger.error(f"Error getting reels caption: {e}")
            return None
    
    def _download_reels_alternative(self, url: str, progress_callback=None, cancel_check=None) -> Optional[str]:
        """
        Alternative method to download reels using public API or third-party services.
        
        Args:
            url: Instagram reels/video URL
            progress_callback: Optional callback function(downloaded, total) for progress updates
            cancel_check: Optional function that returns True if download should be cancelled
            
        Returns:
            str: Path to downloaded video file or None if failed
        """
        try:
            import requests
            import re
            from config import UPLOADS_DIR
            
            logger.info("Trying alternative download method...")
            
            # Extract shortcode from URL
            shortcode_match = re.search(r'/reel/([A-Za-z0-9_-]+)', url)
            if not shortcode_match:
                logger.error("Could not extract shortcode from URL")
                return None
            
            shortcode = shortcode_match.group(1)
            logger.info(f"Extracted shortcode: {shortcode}")
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Cache-Control': 'max-age=0',
            }
            
            # Try to get video URL from Instagram's public embed API
            embed_url = f"https://www.instagram.com/p/{shortcode}/embed/"
            
            logger.info(f"Fetching embed page: {embed_url}")
            response = requests.get(embed_url, headers=headers, timeout=30)
            
            if response.status_code != 200:
                logger.error(f"Failed to fetch embed page: {response.status_code}")
                return None
            
            # Check if cancelled
            if cancel_check and cancel_check():
                logger.info("Download cancelled by user")
                return None
            
            # Extract video URL from embed page - try multiple patterns
            video_url = None
            
            # Pattern 1: JSON format
            video_url_match = re.search(r'"video_url":"([^"]+)"', response.text)
            if video_url_match:
                video_url = video_url_match.group(1).replace('\\u0026', '&')
                logger.info(f"Found video URL (pattern 1): {video_url[:100]}...")
            
            # Pattern 2: Direct video source
            if not video_url:
                video_url_match = re.search(r'<video[^>]*src="([^"]+)"', response.text)
                if video_url_match:
                    video_url = video_url_match.group(1)
                    logger.info(f"Found video URL (pattern 2): {video_url[:100]}...")
            
            # Pattern 3: og:video meta tag
            if not video_url:
                video_url_match = re.search(r'<meta property="og:video" content="([^"]+)"', response.text)
                if video_url_match:
                    video_url = video_url_match.group(1)
                    logger.info(f"Found video URL (pattern 3): {video_url[:100]}...")
            
            # Pattern 4: Try to find any .mp4 URL
            if not video_url:
                video_url_match = re.search(r'(https://[^"\s]+\.mp4[^"\s]*)', response.text)
                if video_url_match:
                    video_url = video_url_match.group(1).replace('\\u0026', '&')
                    logger.info(f"Found video URL (pattern 4): {video_url[:100]}...")
            
            if not video_url:
                logger.error("Could not find video URL in embed page using any pattern")
                logger.debug(f"First 500 chars of response: {response.text[:500]}")
                return None
            
            # Download video
            if not os.path.exists(UPLOADS_DIR):
                os.makedirs(UPLOADS_DIR)
            
            video_filename = f"reels_{shortcode}.mp4"
            video_path = os.path.join(UPLOADS_DIR, video_filename)
            
            logger.info(f"Downloading video to: {video_path}")
            # Long timeout for connection, no timeout for read (download until complete or cancelled)
            video_response = requests.get(video_url, headers=headers, stream=True, timeout=(30, None))
            
            if video_response.status_code != 200:
                logger.error(f"Failed to download video: {video_response.status_code}")
                return None
            
            # Get total file size if available
            total_size = int(video_response.headers.get('content-length', 0))
            downloaded_size = 0
            
            if total_size > 0:
                logger.info(f"Total file size: {total_size / (1024*1024):.2f} MB")
            else:
                logger.warning("Total file size unknown (no content-length header)")
            
            chunk_count = 0
            with open(video_path, 'wb') as f:
                for chunk in video_response.iter_content(chunk_size=8192):
                    # Check if cancelled
                    if cancel_check and cancel_check():
                        logger.info("Download cancelled by user")
                        # Remove partial file
                        if os.path.exists(video_path):
                            os.remove(video_path)
                        return None
                    
                    if chunk:
                        f.write(chunk)
                        downloaded_size += len(chunk)
                        chunk_count += 1
                        
                        # Report progress (even if total_size is 0)
                        if progress_callback:
                            try:
                                progress_callback(downloaded_size, total_size)
                                # Log every 100 chunks to avoid spam
                                if chunk_count % 100 == 0:
                                    logger.debug(f"Progress callback called: {downloaded_size / (1024*1024):.2f} MB / {total_size / (1024*1024) if total_size > 0 else 'unknown'}")
                            except Exception as e:
                                logger.error(f"Error calling progress_callback: {e}")
            
            if os.path.exists(video_path) and os.path.getsize(video_path) > 0:
                logger.info(f"Reels downloaded successfully via alternative method: {video_path}")
                return video_path
            else:
                logger.error("Downloaded file is empty or doesn't exist")
                return None
                
        except Exception as e:
            logger.error(f"Alternative download method failed: {e}")
            return None