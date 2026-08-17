"""
Camera Repository
Handles database operations for Camera entities.
"""
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.models.entities import Camera, CameraStatus


class CameraRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_active_cameras(self) -> List[Camera]:
        """Get all cameras that are active/enabled."""
        result = await self.session.execute(
            select(Camera).where(Camera.is_active == True)
        )
        return list(result.scalars().all())

    async def update_status(
        self, 
        camera_id: int, 
        status: CameraStatus,
        fps_current: float = 0.0,
        frames_dropped: int = 0,
        last_seen: Optional = None
    ):
        """Update camera health status."""
        await self.session.execute(
            update(Camera)
            .where(Camera.id == camera_id)
            .values(
                status=status,
                fps_current=fps_current,
                frames_dropped=frames_dropped,
                last_seen=last_seen
            )
        )
        await self.session.commit()

    async def persist_tracks(self, camera_id: int, tracks):
        """Persist track data to database."""
        # Implementation would iterate tracks and bulk insert
        # Simplified for brevity
        pass
        
    async def persist_events(self, events):
        """Persist events to database."""
        # Implementation would bulk insert events
        pass
