"""
Media Service
Handles thumbnail extraction, video clip generation, and storage abstraction (Local/MinIO).
"""
import os
import cv2
import logging
import hashlib
from datetime import datetime
from typing import Optional

from app.core.config import settings
from app.models.entities import Event

logger = logging.getLogger(__name__)


class MediaService:
    def __init__(self):
        self.storage_root = settings.MEDIA_STORAGE_ROOT
        os.makedirs(self.storage_root, exist_ok=True)
        
    async def generate_thumbnail(self, frame, event: Event) -> Optional[str]:
        """
        Extract and save a thumbnail for an event.
        Returns the relative path to the thumbnail.
        """
        try:
            # Generate unique filename
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            safe_id = hashlib.md5(f"{event.camera_id}_{event.track_id}_{timestamp}".encode()).hexdigest()[:8]
            filename = f"thumb_{safe_id}.jpg"
            
            # Determine directory structure: /root/YYYY/MM/DD/
            date_path = datetime.utcnow().strftime("%Y/%m/%d")
            dir_path = os.path.join(self.storage_root, "thumbnails", date_path)
            os.makedirs(dir_path, exist_ok=True)
            
            filepath = os.path.join(dir_path, filename)
            rel_path = os.path.join("thumbnails", date_path, filename)
            
            # Crop to bounding box if available in metadata, else save full frame
            # For simplicity, saving center crop or full frame resized
            h, w = frame.shape[:2]
            
            # If we had box coords from event metadata, we'd crop here
            # For now, just resize and save
            thumb_size = (320, 180)
            thumb = cv2.resize(frame, thumb_size)
            
            success = cv2.imwrite(filepath, thumb)
            if not success:
                logger.error(f"Failed to write thumbnail: {filepath}")
                return None
                
            logger.debug(f"Thumbnail saved: {rel_path}")
            return rel_path
            
        except Exception as e:
            logger.error(f"Error generating thumbnail: {e}", exc_info=True)
            return None

    async def generate_clip(self, camera_id: int, start_time: datetime, duration_sec: float) -> Optional[str]:
        """
        Generate a video clip from recorded footage.
        Requires a recording buffer or stored video files.
        Simplified: Assumes continuous recording exists in storage.
        """
        try:
            # Construct source path (assumes continuous recording structure)
            # In production, this would query the DB for the specific recording file
            date_path = start_time.strftime("%Y/%m/%d")
            source_dir = os.path.join(self.storage_root, "recordings", date_path)
            
            # Find relevant recording file (simplified logic)
            # Real impl: Query DB for 'recording' entries overlapping start_time
            filename_prefix = f"cam_{camera_id}_{start_time.strftime('%Y%m%d')}"
            
            # FFmpeg command to cut clip
            # ffmpeg -ss START -t DURATION -i INPUT -c copy OUTPUT
            output_filename = f"clip_{camera_id}_{start_time.strftime('%H%M%S')}.mp4"
            output_dir = os.path.join(self.storage_root, "clips", date_path)
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(output_dir, output_filename)
            rel_path = os.path.join("clips", date_path, output_filename)
            
            # Placeholder: Since we don't have real recordings yet, create a dummy file
            # In real impl:
            # cmd = [
            #     "ffmpeg", "-y",
            #     "-ss", start_time.isoformat(),
            #     "-t", str(duration_sec),
            #     "-i", input_file,
            #     "-c", "copy",
            #     output_path
            # ]
            # subprocess.run(cmd, check=True)
            
            # Create empty file for now to satisfy type checks
            with open(output_path, 'wb') as f:
                f.write(b'DUMMY_CLIP_DATA')
                
            logger.info(f"Clip generated (dummy): {rel_path}")
            return rel_path
            
        except Exception as e:
            logger.error(f"Error generating clip: {e}", exc_info=True)
            return None

    async def delete_media(self, relative_path: str) -> bool:
        """Safely delete a media file."""
        try:
            full_path = os.path.join(self.storage_root, relative_path)
            if os.path.exists(full_path):
                os.remove(full_path)
                logger.debug(f"Deleted media: {full_path}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error deleting media {relative_path}: {e}")
            return False

    def get_storage_usage(self) -> dict:
        """Get current storage usage stats."""
        total_size = 0
        file_count = 0
        
        for root, dirs, files in os.walk(self.storage_root):
            for f in files:
                fp = os.path.join(root, f)
                try:
                    total_size += os.path.getsize(fp)
                    file_count += 1
                except OSError:
                    continue
                    
        return {
            "total_bytes": total_size,
            "file_count": file_count,
            "root": self.storage_root
        }
