"""
Universal Camera Module - Enterprise Grade
Supports: Webcam, RTSP, IP Cameras (HTTP/RTSP), USB Cameras, MIPI CSI
Features: Auto-reconnect, frame buffering, multi-threading, health monitoring
"""
from collections.abc import Iterator
import cv2
import threading
import time
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum
import queue

logger = logging.getLogger(__name__)


class CameraType(str, Enum):
    WEBCAM = "webcam"
    RTSP = "rtsp"
    HTTP = "http"
    USB = "usb"
    MIPI_CSI = "mipi_csi"
    UNKNOWN = "unknown"


@dataclass
class CameraConfig:
    """Configuration for camera connection"""
    source: str  # URL or device index
    camera_type: CameraType = CameraType.UNKNOWN
    name: str = "Camera"
    width: int = 1920
    height: int = 1080
    fps: int = 30
    reconnect_attempts: int = 5
    reconnect_delay: float = 2.0
    buffer_size: int = 2
    timeout_ms: int = 5000
    
    @classmethod
    def from_url(cls, url: str, name: str = "Camera") -> 'CameraConfig':
        """Auto-detect camera type from URL"""
        if url.isdigit():
            return cls(source=int(url), camera_type=CameraType.WEBCAM, name=name)
        elif url.startswith("rtsp://"):
            return cls(source=url, camera_type=CameraType.RTSP, name=name)
        elif url.startswith(("http://", "https://")):
            if ".m3u8" in url or "stream" in url:
                return cls(source=url, camera_type=CameraType.HTTP, name=name)
            return cls(source=url, camera_type=CameraType.RTSP, name=name)
        elif url.startswith("/dev/video"):
            return cls(source=url, camera_type=CameraType.USB, name=name)
        else:
            return cls(source=url, camera_type=CameraType.UNKNOWN, name=name)


class UniversalCamera:
    """
    Enterprise-grade universal camera handler with auto-reconnect and buffering
    Supports all camera types: webcam, RTSP, IP, USB, MIPI CSI
    """
    
    def __init__(self, config: CameraConfig):
        self.config = config
        self.capture: Optional[cv2.VideoCapture] = None
        self.frame_buffer: queue.Queue = queue.Queue(maxsize=config.buffer_size)
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._frame_count = 0
        self._last_frame_time = 0.0
        self._fps = 0.0
        self._connected = False
        self._reconnect_count = 0
        
        # Backend optimizations
        self._backends = [
            (cv2.CAP_FFMPEG, "FFMPEG"),
            (cv2.CAP_V4L2, "V4L2"),
            (cv2.CAP_GSTREAMER, "GStreamer"),
            (cv2.CAP_OPENCV_MJPEG, "OpenCV MJPEG"),
        ]
        
        logger.info(f"UniversalCamera initialized: {config.name} ({config.camera_type.value})")
    
    def _detect_camera_type(self) -> CameraType:
        """Auto-detect camera type from source"""
        if isinstance(self.config.source, int):
            return CameraType.WEBCAM
        source_str = str(self.config.source)
        if source_str.startswith("rtsp://"):
            return CameraType.RTSP
        elif source_str.startswith(("http://", "https://")):
            return CameraType.HTTP
        elif source_str.startswith("/dev/video"):
            return CameraType.USB
        return CameraType.UNKNOWN
    
    def connect(self) -> bool:
        """
        Connect to camera with backend auto-detection and optimization
        Returns True if successful
        """
        camera_type = self._detect_camera_type()
        logger.info(f"Connecting to {camera_type.value} camera: {self.config.source}")
        
        # Try different backends
        for backend, backend_name in self._backends:
            try:
                if isinstance(self.config.source, int):
                    self.capture = cv2.VideoCapture(self.config.source, backend)
                else:
                    # Add backend-specific options
                    if backend == cv2.CAP_FFMPEG:
                        # FFMPEG options for better RTSP handling
                        ffmpeg_options = [
                            cv2.CAP_FFMPEG,
                            int(cv2.CAP_PROP_FOURCC), cv2.VideoWriter_fourcc(*'MJPG'),
                        ]
                        self.capture = cv2.VideoCapture(self.config.source, backend)
                        if self.capture.isOpened():
                            # Set optimized parameters
                            self.capture.set(cv2.CAP_PROP_BUFFERSIZE, self.config.buffer_size)
                            self.capture.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, self.config.timeout_ms)
                            self.capture.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, self.config.timeout_ms)
                    else:
                        self.capture = cv2.VideoCapture(self.config.source, backend)
                
                if self.capture is not None and self.capture.isOpened():
                    # Configure camera parameters
                    self._configure_capture()
                    self._connected = True
                    logger.info(f"Connected successfully using {backend_name} backend")
                    return True
                else:
                    if self.capture:
                        self.capture.release()
            except Exception as e:
                logger.debug(f"Backend {backend_name} failed: {e}")
                continue
        
        logger.error(f"Failed to connect to camera {self.config.name} with all backends")
        return False
    
    def _configure_capture(self):
        """Optimize capture parameters"""
        if self.capture is None:
            return
        
        # Set resolution
        self.capture.set(cv2.CAP_PROP_FRAME_WIDTH, self.config.width)
        self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self.config.height)
        self.capture.set(cv2.CAP_PROP_FPS, self.config.fps)
        
        # Get actual values (camera may not support requested values)
        actual_width = int(self.capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_height = int(self.capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
        actual_fps = self.capture.get(cv2.CAP_PROP_FPS)
        
        logger.info(f"Camera configured: {actual_width}x{actual_height} @ {actual_fps:.1f} FPS")
    
    def start(self) -> bool:
        """Start background frame grabbing thread"""
        if not self._connected and not self.connect():
            return False
        
        self._running = True
        self._thread = threading.Thread(target=self._grab_frames, daemon=True)
        self._thread.start()
        logger.info(f"Camera {self.config.name} started")
        return True
    
    def _grab_frames(self):
        """Background thread to continuously grab frames"""
        while self._running:
            if self.capture is None or not self.capture.isOpened():
                self._connected = False
                if self._reconnect_count < self.config.reconnect_attempts:
                    logger.info(f"Reconnecting... ({self._reconnect_count + 1}/{self.config.reconnect_attempts})")
                    time.sleep(self.config.reconnect_delay)
                    if self.connect():
                        self._reconnect_count = 0
                        continue
                    self._reconnect_count += 1
                else:
                    logger.error("Max reconnection attempts reached")
                    break
            
            ret, frame = self.capture.read()
            if ret:
                self._frame_count += 1
                current_time = time.time()
                
                # Calculate FPS
                if self._last_frame_time > 0:
                    dt = current_time - self._last_frame_time
                    if dt > 0:
                        self._fps = 0.9 * self._fps + 0.1 * (1.0 / dt)
                self._last_frame_time = current_time
                
                # Put frame in buffer (non-blocking)
                try:
                    if not self.frame_buffer.empty():
                        # Remove oldest frame if buffer is full
                        try:
                            self.frame_buffer.get_nowait()
                        except queue.Empty:
                            pass
                    self.frame_buffer.put(frame, block=False)
                except queue.Full:
                    pass
            else:
                logger.warning("Failed to read frame, attempting reconnect...")
                self._connected = False
                if self.capture:
                    self.capture.release()
            
            time.sleep(0.001)  # Prevent CPU hogging
    
    def read(self) -> Optional[Any]:
        """Get latest frame (non-blocking)"""
        try:
            return self.frame_buffer.get_nowait()
        except queue.Empty:
            return None
    
    def frames(self) -> Iterator[Any]:
        """Generator that yields frames (blocking)"""
        if self.capture is None and not self.connect():
            raise RuntimeError(f"Unable to connect to camera: {self.config.name}")
        
        assert self.capture is not None
        
        while True:
            ok, frame = self.capture.read()
            if not ok:
                logger.warning("Frame read failed, attempting reconnect...")
                self.capture.release()
                if not self.connect():
                    break
                continue
            yield frame
    
    def get_fps(self) -> float:
        """Get current FPS"""
        return self._fps
    
    def get_frame_count(self) -> int:
        """Get total frames captured"""
        return self._frame_count
    
    def is_connected(self) -> bool:
        """Check if camera is connected"""
        return self._connected and self.capture is not None and self.capture.isOpened()
    
    def get_status(self) -> Dict[str, Any]:
        """Get camera status information"""
        return {
            "name": self.config.name,
            "source": str(self.config.source),
            "type": self.config.camera_type.value,
            "connected": self.is_connected(),
            "fps": round(self._fps, 2),
            "frame_count": self._frame_count,
            "buffer_size": self.frame_buffer.qsize(),
            "reconnect_count": self._reconnect_count,
            "resolution": f"{int(self.capture.get(cv2.CAP_PROP_FRAME_WIDTH)) if self.capture else 0}x"
                         f"{int(self.capture.get(cv2.CAP_PROP_FRAME_HEIGHT)) if self.capture else 0}"
        }
    
    def stop(self):
        """Stop camera and release resources"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
        if self.capture:
            self.capture.release()
        self._connected = False
        logger.info(f"Camera {self.config.name} stopped")
    
    def __enter__(self):
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()


# Backward compatibility alias
RTSPCamera = UniversalCamera
