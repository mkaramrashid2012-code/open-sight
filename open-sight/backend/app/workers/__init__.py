"""Video processing pipeline worker for camera streams - Enterprise Grade."""
import logging
import threading
import time
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID
import numpy as np
from sqlalchemy.orm import Session
from app.cameras.rtsp import RTSPCamera
from app.detection.yolo import YOLODetector, DetectionResult
from app.tracking.bytetrack import ByteTrackAdapter, create_supervision_detections
from app.storage import storage
from app.models.entities import Detection, Camera
from app.core.config import settings

logger = logging.getLogger(__name__)


class CameraWorker:
    """Background worker that processes video from a single camera with enterprise resilience."""
    
    def __init__(
        self,
        camera_id: UUID,
        camera_name: str,
        rtsp_url: str,
        db_session_factory,
        detector: Optional[YOLODetector] = None,
        tracker: Optional[ByteTrackAdapter] = None,
        fps_target: Optional[float] = None,
        skip_frames: Optional[int] = None,
    ):
        self.camera_id = camera_id
        self.camera_name = camera_name
        self.rtsp_url = rtsp_url
        self.db_session_factory = db_session_factory
        self.detector = detector or YOLODetector()
        self.tracker = tracker or ByteTrackAdapter()
        self.fps_target = fps_target or settings.processing_fps_target
        self.skip_frames = skip_frames if skip_frames is not None else settings.skip_frames
        
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._frame_count = 0
        self._last_detection_time = 0.0
        self._reconnect_delay = settings.reconnect_delay_seconds
        self._consecutive_errors = 0
        self._max_consecutive_errors = 10
        
        # Frame buffer for clip generation
        self._frame_buffer: list[np.ndarray] = []
        self._max_buffer_size = settings.frame_buffer_size
        
        # Statistics
        self._frames_processed = 0
        self._detections_count = 0
        self._last_heartbeat = time.time()
    
    def start(self):
        """Start the background processing thread."""
        if self._running:
            logger.warning(f"Worker for {self.camera_name} already running")
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name=f"camera-worker-{self.camera_name}")
        self._thread.start()
        logger.info(f"Started worker for camera {self.camera_name} ({self.camera_id})")
    
    def stop(self):
        """Stop the background processing thread gracefully."""
        logger.info(f"Stopping worker for camera {self.camera_name}...")
        self._running = False
        if self._thread:
            self._thread.join(timeout=5.0)
            self._thread = None
        logger.info(f"Worker stopped for camera {self.camera_name}")
    
    def get_stats(self) -> dict:
        """Get worker statistics."""
        return {
            "camera_id": str(self.camera_id),
            "camera_name": self.camera_name,
            "running": self._running,
            "frames_processed": self._frames_processed,
            "detections_count": self._detections_count,
            "buffer_size": len(self._frame_buffer),
            "consecutive_errors": self._consecutive_errors,
            "last_heartbeat": self._last_heartbeat,
        }
    
    def _run_loop(self):
        """Main processing loop with automatic reconnection and error handling."""
        camera = RTSPCamera(self.rtsp_url)
        
        while self._running:
            try:
                if not camera.connect():
                    logger.error(f"Failed to connect to {self.rtsp_url}, retrying in {self._reconnect_delay}s")
                    self._consecutive_errors += 1
                    if self._consecutive_errors >= self._max_consecutive_errors:
                        logger.error(f"Max consecutive errors reached for {self.camera_name}, stopping worker")
                        break
                    time.sleep(self._reconnect_delay)
                    continue
                
                logger.info(f"Connected to camera {self.camera_name}")
                self._consecutive_errors = 0  # Reset on successful connection
                
                for frame in camera.frames():
                    if not self._running:
                        break
                    
                    self._process_frame(frame)
                    self._frames_processed += 1
                    self._last_heartbeat = time.time()
                    
                    # Rate limiting
                    target_interval = 1.0 / self.fps_target
                    elapsed = time.time() - self._last_detection_time
                    if elapsed < target_interval:
                        time.sleep(target_interval - elapsed)
                
            except Exception as e:
                self._consecutive_errors += 1
                logger.error(f"Error in camera worker {self.camera_name} (errors={self._consecutive_errors}): {e}")
                if self._consecutive_errors >= self._max_consecutive_errors:
                    logger.error(f"Max consecutive errors reached for {self.camera_name}, stopping worker")
                    break
                time.sleep(self._reconnect_delay)
            finally:
                camera.close()
        
        camera.close()
        logger.info(f"Camera worker loop exited for {self.camera_name}")
    
    def _process_frame(self, frame: np.ndarray):
        """Process a single frame through detection and tracking pipeline."""
        self._frame_count += 1
        
        # Skip frames for efficiency
        if self._frame_count % (self.skip_frames + 1) != 0:
            # Still add to buffer for clip generation
            self._add_to_buffer(frame)
            return
        
        self._last_detection_time = time.time()
        
        try:
            # Run detection
            detections = self.detector.predict(frame)
            
            if not detections:
                self._add_to_buffer(frame)
                return
            
            self._detections_count += len(detections)
            
            # Convert to supervision format for tracking
            sv_detections = create_supervision_detections(
                self.detector.model.predict(frame, conf=settings.confidence_threshold, verbose=False),
                self.detector.model.names
            )
            
            # Update tracker
            tracked = self.tracker.update(sv_detections, frame)
            
            # Store detections in database
            self._store_detections(detections, tracked, frame)
            
            # Add annotated frame to buffer
            annotated = self._annotate_frame(frame, detections, tracked)
            self._add_to_buffer(annotated)
            
            self._consecutive_errors = 0  # Reset on success
            
        except Exception as e:
            logger.error(f"Error processing frame: {e}", exc_info=True)
            self._consecutive_errors += 1
    
    def _add_to_buffer(self, frame: np.ndarray):
        """Add frame to circular buffer for clip generation."""
        self._frame_buffer.append(frame.copy())
        if len(self._frame_buffer) > self._max_buffer_size:
            self._frame_buffer.pop(0)
    
    def _annotate_frame(self, frame: np.ndarray, detections: list[DetectionResult], tracked: list[dict]) -> np.ndarray:
        """Draw bounding boxes and labels on frame."""
        import cv2
        
        annotated = frame.copy()
        for i, det in enumerate(detections):
            x1, y1, x2, y2 = map(int, det.bbox)
            
            # Get track ID if available
            track_id = tracked[i]["track_id"] if i < len(tracked) else None
            
            # Color based on class
            color = (0, 255, 0)  # Green default
            
            # Draw box
            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
            
            # Label
            label = f"{det.class_name}"
            if track_id is not None:
                label += f" #{track_id}"
            label += f" {det.confidence:.2f}"
            
            cv2.putText(annotated, label, (x1, y1 - 10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
        
        return annotated
    
    def _store_detections(self, detections: list[DetectionResult], tracked: list[dict], frame: np.ndarray):
        """Store detections in database with optional thumbnail."""
        db = self.db_session_factory()
        try:
            for i, det in enumerate(detections):
                track_id = tracked[i]["track_id"] if i < len(tracked) else None
                
                # Create detection record
                detection = Detection(
                    camera_id=self.camera_id,
                    timestamp=datetime.now(timezone.utc),
                    object_class=det.class_name,
                    confidence=det.confidence,
                    track_id=track_id,
                    bbox=[float(x) for x in det.bbox],
                    attributes={"width": frame.shape[1], "height": frame.shape[0]},
                )
                
                db.add(detection)
                
                # Save thumbnail for high-confidence detections
                if det.confidence >= 0.7:
                    # Crop detection region
                    x1, y1, x2, y2 = map(int, det.bbox)
                    x1, y1 = max(0, x1), max(0, y1)
                    x2, y2 = min(frame.shape[1], x2), min(frame.shape[0], y2)
                    
                    if x2 > x1 and y2 > y1:
                        crop = frame[y1:y2, x1:x2]
                        # Generate detection ID placeholder (will be set after commit)
                        db.flush()
                        thumb_path = storage.save_thumbnail(
                            crop, 
                            str(self.camera_id), 
                            str(detection.id)
                        )
                        detection.attributes["thumbnail"] = thumb_path
            
            db.commit()
            logger.debug(f"Stored {len(detections)} detections for {self.camera_name}")
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error storing detections: {e}", exc_info=True)
        finally:
            db.close()
    
    def save_clip_for_track(self, track_id: int):
        """Save video clip for a specific track from buffer."""
        if not self._frame_buffer:
            return None
        
        clip_path = storage.save_clip(
            self._frame_buffer.copy(),
            str(self.camera_id),
            track_id=track_id
        )
        
        if clip_path:
            logger.info(f"Saved clip for track {track_id}: {clip_path}")
            return clip_path
        return None


class PipelineManager:
    """Manages multiple camera workers with resource limits."""
    
    def __init__(self, db_session_factory):
        self.db_session_factory = db_session_factory
        self.workers: dict[UUID, CameraWorker] = {}
        self.detector = YOLODetector()
        self.tracker = ByteTrackAdapter()
        self._lock = threading.Lock()
        self._started_cameras = set()  # Track all cameras ever started
    
    def start_camera(self, camera: Camera):
        """Start processing for a camera."""
        with self._lock:
            # Check if we've hit the max concurrent cameras limit
            if len(self.workers) >= settings.max_concurrent_cameras:
                logger.warning(f"Max concurrent cameras ({settings.max_concurrent_cameras}) reached, cannot start {camera.name}")
                raise RuntimeError(f"Max concurrent cameras limit reached: {settings.max_concurrent_cameras}")
            
            if camera.id in self.workers:
                logger.warning(f"Camera {camera.name} already has a worker")
                return
            
            worker = CameraWorker(
                camera_id=camera.id,
                camera_name=camera.name,
                rtsp_url=camera.rtsp_url,
                db_session_factory=self.db_session_factory,
                detector=self.detector,
                tracker=self.tracker,
            )
            
            self.workers[camera.id] = worker
            self._started_cameras.add(camera.id)
            worker.start()
    
    def stop_camera(self, camera_id: UUID):
        """Stop processing for a camera."""
        with self._lock:
            if camera_id in self.workers:
                self.workers[camera_id].stop()
                del self.workers[camera_id]
    
    def stop_all(self):
        """Stop all camera workers gracefully."""
        logger.info(f"Stopping all {len(self.workers)} camera workers...")
        with self._lock:
            workers_to_stop = list(self.workers.values())
        
        # Stop workers outside the lock to avoid deadlock
        for worker in workers_to_stop:
            worker.stop()
        
        with self._lock:
            self.workers.clear()
        
        logger.info("All camera workers stopped")
    
    def get_worker(self, camera_id: UUID) -> Optional[CameraWorker]:
        """Get worker for a specific camera."""
        return self.workers.get(camera_id)
    
    def get_stats(self) -> dict:
        """Get statistics for all workers."""
        with self._lock:
            return {
                "active_workers": len(self.workers),
                "total_cameras_started": len(self._started_cameras),
                "max_concurrent": settings.max_concurrent_cameras,
                "workers": [w.get_stats() for w in self.workers.values()],
            }


# Global pipeline manager instance
pipeline_manager: Optional[PipelineManager] = None


def init_pipeline(db_session_factory):
    """Initialize the global pipeline manager."""
    global pipeline_manager
    logger.info("Initializing video processing pipeline...")
    pipeline_manager = PipelineManager(db_session_factory)
    return pipeline_manager


def get_pipeline_manager() -> Optional[PipelineManager]:
    """Get the global pipeline manager."""
    return pipeline_manager