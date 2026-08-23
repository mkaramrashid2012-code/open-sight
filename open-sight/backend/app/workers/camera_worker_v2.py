"""
OpenSight Enterprise - Robust Camera Ingestion Engine
Handles RTSP, HTTP, USB, Files with auto-reconnect, buffering, and health monitoring.
"""
import cv2
import threading
import time
import queue
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class CameraStatus(Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    READY = "ready"
    ERROR = "error"
    RECONNECTING = "reconnecting"

class RobustCameraWorker:
    def __init__(self, camera_id: str, source: str, config: Dict[str, Any]):
        self.camera_id = camera_id
        self.source = source
        self.config = config
        
        # Configuration
        self.buffer_size = config.get("buffer_size", 2)  # Low latency default
        self.reconnect_delay = config.get("reconnect_delay", 5)
        self.max_reconnect_attempts = config.get("max_reconnect_attempts", -1)  # Infinite
        self.read_timeout = config.get("read_timeout", 5.0)
        self.target_fps = config.get("target_fps", 30)
        
        # State
        self.status = CameraStatus.DISCONNECTED
        self.frame_queue = queue.Queue(maxsize=self.buffer_size)
        self.latest_frame: Optional[Any] = None
        self.latest_timestamp: Optional[datetime] = None
        self.stats = {
            "frames_received": 0,
            "frames_dropped": 0,
            "reconnect_count": 0,
            "last_error": None,
            "uptime_start": None,
            "fps_current": 0.0
        }
        
        # Threads
        self.capture_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        self.lock = threading.Lock()
        
        # OpenCV capture object
        self.cap: Optional[cv2.VideoCapture] = None

    def start(self):
        """Start the capture thread."""
        if self.capture_thread and self.capture_thread.is_alive():
            logger.warning(f"Camera {self.camera_id} already running.")
            return
            
        self.stop_event.clear()
        self.stats["uptime_start"] = datetime.now()
        self.capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.capture_thread.start()
        logger.info(f"Camera {self.camera_id} started.")

    def stop(self):
        """Stop the capture thread gracefully."""
        self.stop_event.set()
        if self.capture_thread:
            self.capture_thread.join(timeout=5.0)
        if self.cap:
            self.cap.release()
            self.cap = None
        self.status = CameraStatus.DISCONNECTED
        logger.info(f"Camera {self.camera_id} stopped.")

    def _capture_loop(self):
        """Main capture loop with reconnection logic."""
        attempt = 0
        
        while not self.stop_event.is_set():
            try:
                self.status = CameraStatus.CONNECTING
                logger.info(f"Camera {self.camera_id} connecting to {self.source}...")
                
                # Smart backend selection based on source type
                backends = self._get_optimized_backends(self.source)
                connected = False
                
                for backend in backends:
                    if self.stop_event.is_set(): break
                    self.cap = cv2.VideoCapture(self.source, backend)
                    if self.cap.isOpened():
                        # Set properties
                        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1) # Internal buffer low
                        connected = True
                        logger.info(f"Camera {self.camera_id} connected via {backend}")
                        break
                    else:
                        self.cap.release()
                        self.cap = None
                
                if not connected:
                    raise ConnectionError(f"Failed to open stream with any backend")

                self.status = CameraStatus.READY
                attempt = 0  # Reset attempts on success
                last_frame_time = time.time()
                frame_count = 0
                
                while not self.stop_event.is_set():
                    # Read with timeout logic (non-blocking check)
                    ret, frame = self.cap.read()
                    
                    if not ret or frame is None:
                        # Stream broken
                        logger.warning(f"Camera {self.camera_id} stream lost.")
                        self.stats["last_error"] = "Stream read failed"
                        break
                    
                    # Update stats
                    now = time.time()
                    frame_count += 1
                    self.stats["frames_received"] += 1
                    
                    # Calculate FPS every second
                    if now - last_frame_time >= 1.0:
                        self.stats["fps_current"] = frame_count / (now - last_frame_time)
                        frame_count = 0
                        last_frame_time = now
                    
                    # Handle Backpressure
                    if self.frame_queue.full():
                        try:
                            self.frame_queue.get_nowait() # Drop oldest
                            self.stats["frames_dropped"] += 1
                        except queue.Empty:
                            pass
                    
                    # Put new frame
                    self.frame_queue.put((frame, datetime.now()))
                    with self.lock:
                        self.latest_frame = frame
                        self.latest_timestamp = datetime.now()

            except Exception as e:
                self.status = CameraStatus.ERROR
                self.stats["last_error"] = str(e)
                logger.error(f"Camera {self.camera_id} error: {e}")
                
                if self.cap:
                    self.cap.release()
                    self.cap = None
                
                # Reconnect Logic
                if self.stop_event.is_set():
                    break
                    
                self.status = CameraStatus.RECONNECTING
                attempt += 1
                self.stats["reconnect_count"] += 1
                
                if self.max_reconnect_attempts != -1 and attempt > self.max_reconnect_attempts:
                    logger.error(f"Camera {self.camera_id} max reconnect attempts reached.")
                    break
                
                # Exponential backoff
                delay = min(self.reconnect_delay * (2 ** min(attempt, 5)), 60)
                logger.info(f"Camera {self.camera_id} reconnecting in {delay}s (Attempt {attempt})...")
                
                # Wait in chunks to allow quick stop
                for _ in range(int(delay * 10)):
                    if self.stop_event.is_set(): break
                    time.sleep(0.1)

    def _get_optimized_backends(self, source: str) -> list:
        """Determine best OpenCV backends based on source type."""
        if source.startswith(("rtsp://", "rtsps://")):
            # Try GStreamer first for RTSP (better latency/control), then FFMPEG, then Default
            return [
                cv2.CAP_GSTREAMER,
                cv2.CAP_FFMPEG,
                cv2.CAP_ANY
            ]
        elif source.startswith(("http://", "https://")):
            return [cv2.CAP_FFMPEG, cv2.CAP_ANY]
        elif source.isdigit() or source.startswith("/dev/"):
            return [cv2.CAP_V4L2, cv2.CAP_ANY] # Linux USB
        else:
            return [cv2.CAP_ANY]

    def get_frame(self) -> Optional[tuple]:
        """Get the latest frame (non-blocking)."""
        if self.status != CameraStatus.READY:
            return None
        try:
            return self.frame_queue.get_nowait()
        except queue.Empty:
            return None

    def get_latest_frame(self) -> Optional[Any]:
        """Get the most recent frame without removing from queue."""
        with self.lock:
            return self.latest_frame

    def get_health(self) -> Dict[str, Any]:
        """Return current health metrics."""
        return {
            "id": self.camera_id,
            "source": self.source,
            "status": self.status.value,
            "stats": self.stats.copy(),
            "queue_size": self.frame_queue.qsize(),
            "timestamp": datetime.now().isoformat()
        }
