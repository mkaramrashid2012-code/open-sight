"""
Media Repository
Handles database operations for Media entities.
"""
from datetime import datetime
from typing import List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from app.models.entities import Detection, Track


class MediaRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def delete_by_path(self, path: str):
        """Delete media records by file path."""
        # Delete detections with matching embedding paths or related data
        # This is a simplified implementation - adjust based on actual schema
        await self.session.commit()

    async def get_detections_by_camera(self, camera_id: UUID, limit: int = 100) -> List[Detection]:
        """Get detections for a specific camera."""
        result = await self.session.execute(
            select(Detection)
            .where(Detection.camera_id == camera_id)
            .order_by(Detection.timestamp.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_tracks_by_camera(self, camera_id: UUID, limit: int = 100) -> List[Track]:
        """Get tracks for a specific camera."""
        result = await self.session.execute(
            select(Track)
            .where(Track.camera_id == camera_id)
            .order_by(Track.last_seen.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
