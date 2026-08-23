"""
Retention Worker
Scheduled job to cleanup expired data respecting legal holds.
"""
import asyncio
import logging
from datetime import datetime, timedelta

from app.core.config import settings
from app.db import AsyncSessionLocal
from app.repositories.event_repository import EventRepository
from app.repositories.media_repository import MediaRepository
from app.services.media_service import MediaService
from app.services.audit_service import AuditService

logger = logging.getLogger(__name__)


class RetentionWorker:
    def __init__(self):
        self.media_service = MediaService()
        self.audit_service = AuditService()
        self.running = False

    async def start(self):
        """Main loop: run cleanup every hour."""
        self.running = True
        logger.info("Starting Retention Worker...")
        
        while self.running:
            try:
                await self._run_cleanup()
            except Exception as e:
                logger.error(f"Retention cleanup failed: {e}", exc_info=True)
            
            # Sleep for 1 hour
            await asyncio.sleep(settings.retention_check_interval_hours * 3600)

    async def stop(self):
        self.running = False
        logger.info("Retention Worker stopped.")

    async def _run_cleanup(self):
        """Execute retention policies."""
        logger.info("Running retention cleanup job...")
        now = datetime.utcnow()
        deleted_count = 0
        
        async with AsyncSessionLocal() as session:
            event_repo = EventRepository(session)
            media_repo = MediaRepository(session)
            
            # 1. Find expired events (older than retention period)
            cutoff_date = now - timedelta(days=settings.retention_event_days)
            
            # Get events eligible for deletion
            expired_events = await event_repo.get_events_older_than(cutoff_date)
            
            for event in expired_events:
                # 2. Check for Legal Holds / Evidence Cases
                is_held = await event_repo.is_under_legal_hold(event.id)
                
                if is_held:
                    logger.debug(f"Skipping event {event.id} due to legal hold.")
                    continue
                
                # 3. Delete associated media
                if event.thumbnail_path:
                    success = await self.media_service.delete_media(event.thumbnail_path)
                    if success:
                        await media_repo.delete_by_path(event.thumbnail_path)
                        
                if event.clip_path:
                    success = await self.media_service.delete_media(event.clip_path)
                    if success:
                        await media_repo.delete_by_path(event.clip_path)
                
                # 4. Delete event record
                await event_repo.delete(event.id)
                deleted_count += 1
                
                # 5. Audit the deletion
                await self.audit_service.log_action(
                    actor="SYSTEM_RETENTION",
                    action="EVENT_DELETED",
                    resource_id=event.id,
                    result="SUCCESS",
                    details={"reason": "retention_policy", "cutoff": cutoff_date.isoformat()}
                )
        
        logger.info(f"Retention cleanup complete. Deleted {deleted_count} events.")


def main():
    """Entry point for retention worker container."""
    worker = RetentionWorker()
    try:
        asyncio.run(worker.start())
    except KeyboardInterrupt:
        pass
    finally:
        asyncio.run(worker.stop())


if __name__ == "__main__":
    main()
