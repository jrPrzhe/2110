"""
Scheduler service for the Auto-Poster Bot.
Manages post queue and scheduled publishing every 2 hours.
"""

import os
import json
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, asdict

logger = logging.getLogger("scheduler")

@dataclass
class QueuedPost:
    """Represents a post in the queue."""
    id: str
    url: str
    platform: str  # 'instagram', 'telegram', 'vk', 'all'
    added_at: str  # ISO format datetime
    scheduled_for: Optional[str] = None  # ISO format datetime, None if not scheduled yet
    status: str = 'pending'  # 'pending', 'processing', 'published', 'failed'
    error: Optional[str] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'QueuedPost':
        """Create from dictionary."""
        return cls(**data)


class SchedulerService:
    """Handles scheduled posting with fixed 2-hour intervals."""
    
    # Fixed schedule times (hours): 8, 10, 12, 14, 16, 18, 20, 22
    FIXED_HOURS = [8, 10, 12, 14, 16, 18, 20, 22]
    
    def __init__(self, queue_file: str = 'sessions/post_queue.json'):
        """
        Initialize the scheduler service.
        
        Args:
            queue_file: Path to the queue storage file
        """
        self.queue_file = queue_file
        self.queue: List[QueuedPost] = []
        self.running = False
        self.scheduler_task: Optional[asyncio.Task] = None
        self.publish_callback: Optional[Callable] = None
        
        # Load existing queue
        self._load_queue()
    
    def _load_queue(self):
        """Load queue from file."""
        try:
            if os.path.exists(self.queue_file):
                with open(self.queue_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.queue = [QueuedPost.from_dict(item) for item in data]
                    logger.info(f"Loaded {len(self.queue)} posts from queue")
            else:
                logger.info("No existing queue file found, starting with empty queue")
        except Exception as e:
            logger.error(f"Error loading queue: {e}")
            self.queue = []
    
    def _save_queue(self):
        """Save queue to file."""
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.queue_file), exist_ok=True)
            
            with open(self.queue_file, 'w', encoding='utf-8') as f:
                data = [post.to_dict() for post in self.queue]
                json.dump(data, f, ensure_ascii=False, indent=2)
                logger.info(f"Saved {len(self.queue)} posts to queue")
        except Exception as e:
            logger.error(f"Error saving queue: {e}")
    
    def add_to_queue(self, url: str, platform: str = 'all') -> QueuedPost:
        """
        Add a new post to the queue.
        
        Args:
            url: Instagram/post URL
            platform: Target platform ('instagram', 'telegram', 'vk', 'all')
            
        Returns:
            QueuedPost: The created queued post
        """
        # Generate unique ID
        post_id = f"post_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(self.queue)}"
        
        post = QueuedPost(
            id=post_id,
            url=url,
            platform=platform,
            added_at=datetime.now().isoformat(),
            status='pending'
        )
        
        self.queue.append(post)
        self._save_queue()
        
        logger.info(f"Added post to queue: {post.id} - {url}")
        return post
    
    def get_queue(self, status: Optional[str] = None) -> List[QueuedPost]:
        """
        Get posts from queue, optionally filtered by status.
        
        Args:
            status: Filter by status ('pending', 'processing', 'published', 'failed')
            
        Returns:
            List of queued posts
        """
        if status:
            return [post for post in self.queue if post.status == status]
        return self.queue.copy()
    
    def get_pending_posts(self) -> List[QueuedPost]:
        """Get all pending posts."""
        return self.get_queue(status='pending')
    
    def clear_queue(self, status: Optional[str] = None):
        """
        Clear queue, optionally only posts with specific status.
        
        Args:
            status: Clear only posts with this status, or all if None
        """
        if status:
            self.queue = [post for post in self.queue if post.status != status]
            logger.info(f"Cleared posts with status '{status}' from queue")
        else:
            self.queue = []
            logger.info("Cleared entire queue")
        
        self._save_queue()
    
    def remove_from_queue(self, post_id: str) -> bool:
        """
        Remove a specific post from queue.
        
        Args:
            post_id: ID of the post to remove
            
        Returns:
            True if removed, False if not found
        """
        original_len = len(self.queue)
        self.queue = [post for post in self.queue if post.id != post_id]
        
        if len(self.queue) < original_len:
            self._save_queue()
            logger.info(f"Removed post {post_id} from queue")
            return True
        
        logger.warning(f"Post {post_id} not found in queue")
        return False
    
    def update_post_status(self, post_id: str, status: str, error: Optional[str] = None):
        """
        Update post status.
        
        Args:
            post_id: ID of the post
            status: New status
            error: Error message if failed
        """
        for post in self.queue:
            if post.id == post_id:
                post.status = status
                if error:
                    post.error = error
                self._save_queue()
                logger.info(f"Updated post {post_id} status to {status}")
                return
        
        logger.warning(f"Post {post_id} not found for status update")
    
    def get_next_schedule_time(self) -> datetime:
        """
        Get the next scheduled posting time based on fixed hours.
        
        Returns:
            Next posting datetime
        """
        now = datetime.now()
        current_hour = now.hour
        
        # Find next scheduled hour
        next_hour = None
        for hour in self.FIXED_HOURS:
            if hour > current_hour:
                next_hour = hour
                break
        
        # If no hour found today, use first hour tomorrow
        if next_hour is None:
            next_time = now.replace(hour=self.FIXED_HOURS[0], minute=0, second=0, microsecond=0)
            next_time += timedelta(days=1)
        else:
            next_time = now.replace(hour=next_hour, minute=0, second=0, microsecond=0)
        
        return next_time
    
    def set_publish_callback(self, callback: Callable):
        """
        Set callback function for publishing posts.
        
        Args:
            callback: Async function(post: QueuedPost) that handles publishing
        """
        self.publish_callback = callback
    
    async def _scheduler_loop(self):
        """Main scheduler loop that publishes posts at fixed times."""
        logger.info("Scheduler loop started")
        
        while self.running:
            try:
                # Get next scheduled time
                next_time = self.get_next_schedule_time()
                now = datetime.now()
                
                # Calculate wait time
                wait_seconds = (next_time - now).total_seconds()
                
                logger.info(f"Next scheduled post at {next_time.strftime('%Y-%m-%d %H:%M:%S')} (in {wait_seconds/60:.1f} minutes)")
                
                # Wait until next scheduled time
                if wait_seconds > 0:
                    # Check every minute if we should still wait
                    while wait_seconds > 0 and self.running:
                        sleep_time = min(60, wait_seconds)  # Check every minute
                        await asyncio.sleep(sleep_time)
                        wait_seconds -= sleep_time
                        
                        # Recalculate in case system time changed
                        now = datetime.now()
                        wait_seconds = (next_time - now).total_seconds()
                
                if not self.running:
                    break
                
                # Time to publish!
                await self._publish_next_post()
                
            except asyncio.CancelledError:
                logger.info("Scheduler loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                # Wait a bit before retrying
                await asyncio.sleep(60)
    
    async def _publish_next_post(self):
        """Publish the next pending post from queue."""
        try:
            # Get next pending post
            pending_posts = self.get_pending_posts()
            
            if not pending_posts:
                logger.info("No pending posts in queue to publish")
                return
            
            # Get the oldest pending post
            post = pending_posts[0]
            
            logger.info(f"Publishing post {post.id}: {post.url}")
            
            # Update status to processing
            self.update_post_status(post.id, 'processing')
            
            # Call publish callback
            if self.publish_callback:
                try:
                    success = await self.publish_callback(post)
                    
                    if success:
                        self.update_post_status(post.id, 'published')
                        logger.info(f"Successfully published post {post.id}")
                    else:
                        self.update_post_status(post.id, 'failed', error='Publishing returned False')
                        logger.error(f"Failed to publish post {post.id}")
                except Exception as e:
                    error_msg = str(e)
                    self.update_post_status(post.id, 'failed', error=error_msg)
                    logger.error(f"Error publishing post {post.id}: {error_msg}")
            else:
                logger.warning("No publish callback set, marking as failed")
                self.update_post_status(post.id, 'failed', error='No publish callback')
                
        except Exception as e:
            logger.error(f"Error in _publish_next_post: {e}")
    
    async def start(self):
        """Start the scheduler."""
        if self.running:
            logger.warning("Scheduler already running")
            return
        
        self.running = True
        self.scheduler_task = asyncio.create_task(self._scheduler_loop())
        logger.info("Scheduler started")
    
    async def stop(self):
        """Stop the scheduler."""
        if not self.running:
            return
        
        self.running = False
        
        if self.scheduler_task:
            self.scheduler_task.cancel()
            try:
                await self.scheduler_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Scheduler stopped")
    
    def get_schedule_info(self) -> str:
        """
        Get formatted schedule information.
        
        Returns:
            Formatted string with schedule info
        """
        next_time = self.get_next_schedule_time()
        now = datetime.now()
        time_until = next_time - now
        
        hours = int(time_until.total_seconds() // 3600)
        minutes = int((time_until.total_seconds() % 3600) // 60)
        
        schedule_str = f"⏰ <b>Расписание публикаций</b>\n\n"
        schedule_str += f"📅 <b>Фиксированные часы:</b> {', '.join(map(str, self.FIXED_HOURS))}\n"
        schedule_str += f"⏭️ <b>Следующая публикация:</b> {next_time.strftime('%d.%m.%Y в %H:%M')}\n"
        schedule_str += f"⏳ <b>Через:</b> {hours}ч {minutes}мин\n"
        schedule_str += f"📊 <b>В очереди:</b> {len(self.get_pending_posts())} постов"
        
        return schedule_str

