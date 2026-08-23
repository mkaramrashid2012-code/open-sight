"""
Production Camera Worker
Handles RTSP ingestion, reconnection, frame buffering, and health monitoring.
"""
import asyncio
import cv2
import time
import logging
from typing import Optional, Any
from datetime import datetime
from enum import Enum

from app.core.config import settings
from app.models.entities import CameraStatus
from app.db import AsyncSessionLocal
from app.repositories.camera_repository import CameraRepository
from app.services.detector import DetectorService
from app.services.tracker_service import TrackerService
from app.engines.event_engine import EventEngine
from app.services.media_service import MediaService
from app.security import decrypt_rtsp_url

logger = logging.getLogger(__name__)


class CameraWorkerState(Enum):
    STOPPED = "STOPPED"
    CONNECTING = "CONNECTING"
    ONLINE = "ONLINE"
    DEGRADED = "DEGRADED"
    RECONNECTING = "RECONNECTING"
    ERROR = "ERROR"


class CameraWorker:
    def __init__(self, camera_id: int, rtsp_url: str, fps_target: float = 15.0):
        self.camera_id = camera_id
        self.raw_rtsp_url = rtsp_url
        self.fps_target = fps_target
        self.state = CameraWorkerState.STOPPED
        
        # Components
        self.detector = DetectorService()
        self.tracker = TrackerService()
        self.event_engine = EventEngine()
        self.media_service = MediaService()
        
        # Runtime state
        self.cap: Optional[cv2.VideoCapture] = None
        self.running = False
        self.frame_count = 0
        self.dropped_frames = 0
        self.last_frame_time = 0.0
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = settings.camera_max_reconnect_attempts
        self.backoff_seconds = 1.0
        
        # Buffer for backpressure
        self.frame_buffer: Optional[Any] = None
        self.buffer_lock = asyncio.Lock()

    async def start(self):
        """Main entry point for the worker loop."""
        self.running = True
        logger.info(f"Starting camera worker for ID {self.camera_id}")
        
        while self.running:
            try:
                await self._run_loop()
            except Exception as e:
                logger.error(f"Critical error in camera {self.camera_id}: {e}", exc_info=True)
                self.state = CameraWorkerState.ERROR
                await self._update_camera_status(CameraStatus.ERROR)
                
                if not self.running:
                    break
                    
                # Exponential backoff before retry
                if self.reconnect_attempts < self.max_reconnect_attempts:
                    wait_time = min(self.backoff_seconds * (2 ** self.reconnect_attempts), 60)
                    logger.warning(f"Reconnecting in {wait_time}s... (Attempt {self.reconnect_attempts + 1})")
                    await asyncio.sleep(wait_time)
                    self.reconnect_attempts += 1
                else:
                    logger.error(f"Max reconnect attempts reached for camera {self.camera_id}. Stopping.")
                    self.running = False

    async def stop(self):
        """Graceful shutdown."""
        logger.info(f"Stopping camera worker for ID {self.camera_id}")
        self.running = False
        self.state = CameraWorkerState.STOPPED
        
        if self.cap:
            self.cap.release()
            self.cap = None
            
        await self.detector.close()
        await self._update_camera_status(CameraStatus.OFFLINE)

    async def _run_loop(self):
        """Inner loop handling connection and frame processing."""
        decrypted_url = decrypt_rtsp_url(self.raw_rtsp_url)
        
        self.state = CameraWorkerState.CONNECTING
        await self._update_camera_status(CameraStatus.CONNECTING)
        
        # Support multiple camera types: RTSP, HTTP, Webcam (0, 1, etc.), video files
        if decrypted_url.isdigit():
            # Webcam index
            self.cap = cv2.VideoCapture(int(decrypted_url))
        elif decrypted_url.startswith(('http://', 'https://')):
            # HTTP/HTTPS stream (IP cameras, YouTube, etc.)
            self.cap = cv2.VideoCapture(decrypted_url, cv2.CAP_FFMPEG)
        elif decrypted_url.endswith(('.mp4', '.avi', '.mkv', '.mov')):
            # Video file
            self.cap = cv2.VideoCapture(decrypted_url)
        else:
            # RTSP/RTMP or other protocols - try with FFMPEG first, then default
            self.cap = cv2.VideoCapture(decrypted_url, cv2.CAP_FFMPEG)
            if not self.cap.isOpened():
                self.cap.release()
                self.cap = cv2.VideoCapture(decrypted_url)
        
        if not self.cap.isOpened():
            raise ConnectionError(f"Failed to open camera stream for camera {self.camera_id} (URL: {decrypted_url[:50]}...)")
            
        self.state = CameraWorkerState.ONLINE
        self.reconnect_attempts = 0
        self.backoff_seconds = 1.0
        await self._update_camera_status(CameraStatus.ONLINE)
        
        frame_interval = 1.0 / self.fps_target
        
        while self.running:
            loop_start = time.time()
            
            # Read frame with timeout
            ret, frame = self.cap.read()
            
            if not ret:
                logger.warning(f"Frame read failed for camera {self.camera_id}")
                self.state = CameraWorkerState.DEGRADED
                await self._update_camera_status(CameraStatus.DEGRADED)
                # Trigger reconnect by breaking inner loop
                if self.cap:
                    self.cap.release()
                return 

            current_time = time.time()
            self.frame_count += 1
            
            # Calculate FPS and dropped frames
            if self.last_frame_time > 0:
                delta = current_time - self.last_frame_time
                if delta > frame_interval * 1.5:
                    self.dropped_frames += 1
            
            self.last_frame_time = current_time
            
            # Process frame (Offload to thread if needed, but keeping simple for now)
            await self._process_frame(frame)
            
            # Maintain target FPS
            elapsed = time.time() - loop_start
            sleep_time = frame_interval - elapsed
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)

    async def _process_frame(self, frame):
        """Run detection, tracking, and event generation on a frame."""
        try:
            # 1. Detect
            detections = await self.detector.detect(frame)
            
            if not detections:
                return

            # 2. Track
            tracks = await self.tracker.update(detections)
            
            # 3. Persist Tracks & Detections
            async with AsyncSessionLocal() as session:
                repo = CameraRepository(session)
                await repo.persist_tracks(self.camera_id, tracks)
                
                # 4. Generate Events
                events = await self.event_engine.process_tracks(tracks, self.camera_id)
                
                if events:
                    await repo.persist_events(events)
                    
                    # 5. Generate Media for high confidence events
                    for event in events:
                        if event.confidence > 0.7:
                            await self.media_service.generate_thumbnail(frame, event)
                            # Optional: Generate clip if buffer available
                            
        except Exception as e:
            logger.error(f"Error processing frame for camera {self.camera_id}: {e}")

    async def _update_camera_status(self, status: CameraStatus):
        """Update camera status in DB."""
        try:
            async with AsyncSessionLocal() as session:
                repo = CameraRepository(session)
                await repo.update_status(
                    self.camera_id, 
                    status, 
                    fps_current=self.fps_target, # Simplified
                    frames_dropped=self.dropped_frames,
                    last_seen=datetime.utcnow()
                )
        except Exception as e:
            logger.error(f"Failed to update camera status: {e}")
