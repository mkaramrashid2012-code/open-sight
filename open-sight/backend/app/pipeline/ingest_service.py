"""
Ingest Service Entry Point
Manages lifecycle of multiple Camera Workers.
Handles signals for graceful shutdown.
"""
import asyncio
import signal
import logging
from typing import List, Dict

from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.repositories.camera_repository import CameraRepository
from app.workers.camera_worker import CameraWorker
from app.models.entities import CameraStatus

logger = logging.getLogger(__name__)


class IngestService:
    def __init__(self):
        self.workers: Dict[int, CameraWorker] = {}
        self.tasks: Dict[int, asyncio.Task] = {}
        self.running = False
        self.shutdown_event = asyncio.Event()

    async def start(self):
        """Initialize and start all active camera workers."""
        self.running = True
        logger.info("Starting Ingest Service...")
        
        # Register signal handlers
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, lambda: asyncio.create_task(self.shutdown()))
        
        # Load active cameras from DB
        await self._load_and_start_cameras()
        
        # Wait for shutdown signal
        await self.shutdown_event.wait()
        logger.info("Shutdown signal received.")

    async def shutdown(self):
        """Gracefully stop all workers."""
        if not self.running:
            return
            
        logger.info("Shutting down Ingest Service...")
        self.running = False
        
        # Stop all workers
        stop_tasks = []
        for worker_id, worker in self.workers.items():
            logger.info(f"Stopping worker for camera {worker_id}")
            task = asyncio.create_task(worker.stop())
            stop_tasks.append(task)
            
        if stop_tasks:
            await asyncio.gather(*stop_tasks, return_exceptions=True)
            
        self.workers.clear()
        self.tasks.clear()
        self.shutdown_event.set()
        logger.info("Ingest Service stopped.")

    async def _load_and_start_cameras(self):
        """Query DB for active cameras and spawn workers."""
        try:
            async with AsyncSessionLocal() as session:
                repo = CameraRepository(session)
                cameras = await repo.get_active_cameras()
                
            logger.info(f"Found {len(cameras)} active cameras to process.")
            
            for cam in cameras:
                if cam.id in self.workers:
                    continue  # Already running
                    
                worker = CameraWorker(
                    camera_id=cam.id,
                    rtsp_url=cam.rtsp_url_encrypted, # Assumes encrypted in DB
                    fps_target=cam.fps_target or settings.DEFAULT_CAMERA_FPS
                )
                
                self.workers[cam.id] = worker
                task = asyncio.create_task(worker.start())
                self.tasks[cam.id] = task
                logger.info(f"Started worker for camera {cam.id} ({cam.name})")
                
        except Exception as e:
            logger.error(f"Failed to load cameras: {e}", exc_info=True)
            # Retry logic could go here

    async def add_camera(self, camera_id: int, rtsp_url: str):
        """Dynamically add a camera worker."""
        if camera_id in self.workers:
            logger.warning(f"Camera {camera_id} already running.")
            return
            
        worker = CameraWorker(camera_id, rtsp_url)
        self.workers[camera_id] = worker
        task = asyncio.create_task(worker.start())
        self.tasks[camera_id] = task
        logger.info(f"Dynamically started worker for camera {camera_id}")

    async def remove_camera(self, camera_id: int):
        """Stop and remove a camera worker."""
        if camera_id not in self.workers:
            return
            
        worker = self.workers.pop(camera_id)
        await worker.stop()
        
        if camera_id in self.tasks:
            self.tasks.pop(camera_id)
            
        logger.info(f"Stopped worker for camera {camera_id}")


def main():
    """Entry point for the ingest service container."""
    service = IngestService()
    try:
        asyncio.run(service.start())
    except KeyboardInterrupt:
        pass
    finally:
        asyncio.run(service.shutdown())


if __name__ == "__main__":
    main()
