"""Storage module for saving media files (clips, thumbnails)."""
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional
import cv2
import numpy as np
from app.core.config import settings


class MediaStorage:
    """Handles saving and retrieving media files."""
    
    def __init__(self):
        self.media_root = Path(settings.media_root)
        self.clips_root = Path(settings.clips_root)
        self.thumbnails_root = Path(settings.thumbnails_root)
        self._ensure_dirs()
    
    def _ensure_dirs(self):
        """Create storage directories if they don't exist."""
        for root in [self.media_root, self.clips_root, self.thumbnails_root]:
            root.mkdir(parents=True, exist_ok=True)
            # Create date-based subdirectories for organization
            (root / datetime.now().strftime("%Y/%m")).mkdir(parents=True, exist_ok=True)
    
    def _get_date_path(self, base: Path) -> Path:
        """Get date-based subdirectory path."""
        return base / datetime.now().strftime("%Y/%m")
    
    def save_thumbnail(self, frame: np.ndarray, camera_id: str, detection_id: str) -> str:
        """Save a thumbnail image for a detection."""
        thumb_path = self._get_date_path(self.thumbnails_root)
        filename = f"{camera_id}_{detection_id}.jpg"
        filepath = thumb_path / filename
        
        # Resize frame for thumbnail
        h, w = frame.shape[:2]
        new_size = (min(320, w), min(240, h))
        resized = cv2.resize(frame, new_size, interpolation=cv2.INTER_AREA)
        
        cv2.imwrite(str(filepath), resized)
        return str(filepath.relative_to(self.media_root.parent))
    
    def save_clip(
        self, 
        frames: list[np.ndarray], 
        camera_id: str, 
        track_id: Optional[int] = None,
        fps: float = 10.0
    ) -> str:
        """Save a video clip from a list of frames."""
        clip_path = self._get_date_path(self.clips_root)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        track_suffix = f"_track_{track_id}" if track_id is not None else ""
        filename = f"{camera_id}{track_suffix}_{timestamp}.mp4"
        filepath = clip_path / filename
        
        if not frames:
            return ""
        
        h, w = frames[0].shape[:2]
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(str(filepath), fourcc, fps, (w, h))
        
        for frame in frames:
            out.write(frame)
        
        out.release()
        return str(filepath.relative_to(self.media_root.parent))
    
    def get_thumbnail_url(self, relative_path: str) -> str:
        """Get URL path for a thumbnail."""
        return f"/media/{relative_path}"
    
    def get_clip_url(self, relative_path: str) -> str:
        """Get URL path for a clip."""
        return f"/media/{relative_path}"
    
    def cleanup_old_media(self, retention_days: int) -> int:
        """Remove media older than retention period. Returns count of deleted files."""
        from datetime import timedelta
        cutoff = datetime.now() - timedelta(days=retention_days)
        deleted = 0
        
        for root in [self.clips_root, self.thumbnails_root]:
            if not root.exists():
                continue
            for filepath in root.rglob("*"):
                if filepath.is_file():
                    try:
                        mtime = datetime.fromtimestamp(filepath.stat().st_mtime)
                        if mtime < cutoff:
                            filepath.unlink()
                            deleted += 1
                    except (OSError, ValueError):
                        continue
        
        return deleted


# Global instance
storage = MediaStorage()