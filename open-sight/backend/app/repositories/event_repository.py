"""
Event Repository
Handles database operations for Event entities.
"""
from datetime import datetime
from typing import List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload

from app.models.entities import Event, Track, EvidenceHold


class EventRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_events_older_than(self, cutoff_date: datetime) -> List[Event]:
        """Get all events older than the cutoff date."""
        result = await self.session.execute(
            select(Event)
            .where(Event.start_time < cutoff_date)
            .options(selectinload(Event.track))
        )
        return list(result.scalars().all())

    async def is_under_legal_hold(self, event_id: UUID) -> bool:
        """Check if an event is under legal hold."""
        result = await self.session.execute(
            select(EvidenceHold)
            .where(
                EvidenceHold.is_active == True,
                EvidenceHold.event_ids.contains([str(event_id)])
            )
        )
        hold = result.scalar_one_or_none()
        return hold is not None

    async def delete(self, event_id: UUID):
        """Delete an event by ID."""
        await self.session.execute(
            delete(Event).where(Event.id == event_id)
        )
        await self.session.commit()

    async def get_by_id(self, event_id: UUID) -> Optional[Event]:
        """Get an event by ID."""
        result = await self.session.execute(
            select(Event)
            .where(Event.id == event_id)
            .options(selectinload(Event.track), selectinload(Event.camera))
        )
        return result.scalar_one_or_none()

    async def get_by_camera(self, camera_id: UUID, limit: int = 100) -> List[Event]:
        """Get events for a specific camera."""
        result = await self.session.execute(
            select(Event)
            .where(Event.camera_id == camera_id)
            .order_by(Event.start_time.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_type(self, event_type: str, limit: int = 100) -> List[Event]:
        """Get events by type."""
        result = await self.session.execute(
            select(Event)
            .where(Event.event_type == event_type)
            .order_by(Event.start_time.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def create_event(self, event: Event) -> Event:
        """Create a new event."""
        self.session.add(event)
        await self.session.commit()
        await self.session.refresh(event)
        return event
