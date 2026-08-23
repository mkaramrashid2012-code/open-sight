"""
OpenSight Enterprise - Pipeline Orchestrator
Unifies camera ingestion, detection, tracking, analytics, and alerting into a cohesive pipeline.
"""
import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from collections import defaultdict

# Import from correct module paths
import sys
sys.path.insert(0, '/workspace/open-sight/backend')

from app.workers.camera_worker_v2 import RobustCameraWorker, CameraStatus
from app.services.inference_engine import InferenceEngine
from app.services.tracker_engine import AdvancedTracker, Track
from app.services.alert_engine import AlertEngine, AlertSeverity
from app.engines.event_engine import EventEngine  # Existing event engine in engines module
from app.services.synopsis_engine import VideoSynopsisEngine

logger = logging.getLogger(__name__)

class PipelineOrchestrator:
    """
    Main orchestration class that coordinates:
    - Camera workers (capture)
    - Inference engines (detection)
    - Trackers (multi-object tracking)
    - Event engines (behavioral analytics)
    - Alert engines (notifications)
    
    Supports multiple cameras with independent pipelines.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        
        # Component registries
        self.camera_workers: Dict[str, RobustCameraWorker] = {}
        self.inference_engines: Dict[str, InferenceEngine] = {}
        self.trackers: Dict[str, AdvancedTracker] = {}
        self.event_engines: Dict[str, EventEngine] = {}
        
        # Shared alert engine (singleton)
        self.alert_engine = AlertEngine(config.get("alert_config", {}))
        
        # Synopsis engine (shared)
        self.synopsis_engine = VideoSynopsisEngine(config.get("synopsis_config", {}))
        
        # Processing state
        self.running = False
        self.processing_tasks: Dict[str, asyncio.Task] = {}
        
        # Statistics
        self.stats = {
            "pipeline_start_time": None,
            "total_frames_processed": 0,
            "total_detections": 0,
            "total_tracks": 0,
            "total_events": 0,
            "total_alerts": 0,
            "cameras_active": 0
        }
        
        # Callbacks for external integration
        self.on_detection_callbacks: List = []
        self.on_track_callbacks: List = []
        self.on_event_callbacks: List = []
        self.on_alert_callbacks: List = []

    def add_camera(self, camera_id: str, source: str, camera_config: Dict[str, Any]):
        """Add a camera to the pipeline."""
        if camera_id in self.camera_workers:
            logger.warning(f"Camera {camera_id} already exists. Stopping old instance.")
            self.remove_camera(camera_id)
        
        # Create camera worker
        worker_config = {
            **camera_config,
            "buffer_size": camera_config.get("buffer_size", 2),
            "reconnect_delay": camera_config.get("reconnect_delay", 5),
            "target_fps": camera_config.get("target_fps", 15)
        }
        worker = RobustCameraWorker(camera_id, source, worker_config)
        self.camera_workers[camera_id] = worker
        
        # Create dedicated inference engine for this camera
        inference_config = {
            "model_type": camera_config.get("model_type", "yolov8"),
            "model_path": camera_config.get("model_path", "yolov8n.pt"),
            "device": camera_config.get("device", "auto"),
            "confidence": camera_config.get("confidence", 0.25),
            "iou": camera_config.get("iou", 0.45)
        }
        try:
            engine = InferenceEngine(inference_config)
            self.inference_engines[camera_id] = engine
        except Exception as e:
            logger.error(f"Failed to load inference engine for {camera_id}: {e}")
            raise
        
        # Create dedicated tracker for this camera
        tracker_config = {
            "tracker_type": camera_config.get("tracker_type", "bytetrack"),
            "track_thresh": camera_config.get("track_thresh", 0.5),
            "match_thresh": camera_config.get("match_thresh", 0.8),
            "max_age": camera_config.get("max_age", 30)
        }
        tracker = AdvancedTracker(tracker_config)
        self.trackers[camera_id] = tracker
        
        # Create event engine for this camera
        event_config = {
            "zones": camera_config.get("zones", []),
            "lines": camera_config.get("lines", []),
            "rules": camera_config.get("analytics_rules", [])
        }
        event_engine = EventEngine(event_config)
        self.event_engines[camera_id] = event_engine
        
        logger.info(f"Camera {camera_id} added to pipeline with source: {source}")

    def remove_camera(self, camera_id: str):
        """Remove a camera from the pipeline."""
        if camera_id in self.processing_tasks:
            self.processing_tasks[camera_id].cancel()
            
        if camera_id in self.camera_workers:
            self.camera_workers[camera_id].stop()
            del self.camera_workers[camera_id]
            
        if camera_id in self.inference_engines:
            del self.inference_engines[camera_id]
            
        if camera_id in self.trackers:
            del self.trackers[camera_id]
            
        if camera_id in self.event_engines:
            del self.event_engines[camera_id]
            
        logger.info(f"Camera {camera_id} removed from pipeline")

    def start(self):
        """Start all camera pipelines."""
        self.running = True
        self.stats["pipeline_start_time"] = datetime.now()
        
        for camera_id in self.camera_workers:
            self._start_camera_pipeline(camera_id)
            
        logger.info(f"Pipeline orchestrator started with {len(self.camera_workers)} cameras")

    def stop(self):
        """Stop all camera pipelines."""
        self.running = False
        
        for camera_id in list(self.processing_tasks.keys()):
            self._stop_camera_pipeline(camera_id)
            
        logger.info("Pipeline orchestrator stopped")

    def _start_camera_pipeline(self, camera_id: str):
        """Start processing pipeline for a single camera."""
        if camera_id in self.processing_tasks:
            return
            
        # Start camera worker
        self.camera_workers[camera_id].start()
        
        # Create async processing task
        task = asyncio.create_task(self._process_camera_loop(camera_id))
        self.processing_tasks[camera_id] = task
        
        self.stats["cameras_active"] += 1
        logger.info(f"Pipeline started for camera {camera_id}")

    def _stop_camera_pipeline(self, camera_id: str):
        """Stop processing pipeline for a single camera."""
        if camera_id in self.processing_tasks:
            self.processing_tasks[camera_id].cancel()
            del self.processing_tasks[camera_id]
            
        if camera_id in self.camera_workers:
            self.camera_workers[camera_id].stop()
            
        self.stats["cameras_active"] -= 1
        logger.info(f"Pipeline stopped for camera {camera_id}")

    async def _process_camera_loop(self, camera_id: str):
        """
        Main processing loop for a camera.
        Fetches frames → Detects → Tracks → Analyzes → Alerts
        """
        logger.info(f"Processing loop started for {camera_id}")
        
        while self.running:
            try:
                # Get frame from camera worker
                worker = self.camera_workers[camera_id]
                
                if worker.status != CameraStatus.READY:
                    await asyncio.sleep(0.5)
                    continue
                
                frame_data = worker.get_frame()
                if not frame_data:
                    await asyncio.sleep(0.01)  # Small sleep to prevent busy waiting
                    continue
                    
                frame, timestamp = frame_data
                
                # Run detection
                engine = self.inference_engines[camera_id]
                detections = engine.detect(frame)
                
                if detections:
                    self.stats["total_detections"] += len(detections)
                    
                    # Trigger detection callbacks
                    for callback in self.on_detection_callbacks:
                        try:
                            callback(camera_id, timestamp, detections)
                        except Exception as e:
                            logger.error(f"Detection callback error: {e}")
                
                # Run tracking
                tracker = self.trackers[camera_id]
                tracks = tracker.update(detections, timestamp)
                
                if tracks:
                    self.stats["total_tracks"] += len(tracks)
                    
                    # Trigger track callbacks
                    for callback in self.on_track_callbacks:
                        try:
                            callback(camera_id, timestamp, tracks)
                        except Exception as e:
                            logger.error(f"Track callback error: {e}")
                
                # Run event/analytics engine
                event_engine = self.event_engines[camera_id]
                events = event_engine.process_frame(tracks, timestamp)
                
                if events:
                    self.stats["total_events"] += len(events)
                    
                    # Process alerts for events
                    for event in events:
                        alert = await self.alert_engine.process_event(event)
                        if alert:
                            self.stats["total_alerts"] += 1
                            
                            # Trigger alert callbacks
                            for callback in self.on_alert_callbacks:
                                try:
                                    callback(alert)
                                except Exception as e:
                                    logger.error(f"Alert callback error: {e}")
                    
                    # Trigger event callbacks
                    for callback in self.on_event_callbacks:
                        try:
                            callback(camera_id, timestamp, events)
                        except Exception as e:
                            logger.error(f"Event callback error: {e}")
                
                self.stats["total_frames_processed"] += 1
                
                # Small yield to prevent blocking
                await asyncio.sleep(0)
                
            except asyncio.CancelledError:
                logger.info(f"Processing loop cancelled for {camera_id}")
                break
            except Exception as e:
                logger.error(f"Processing error for {camera_id}: {e}")
                await asyncio.sleep(1)  # Backoff on error

    def add_detection_callback(self, callback):
        """Register callback for detections: fn(camera_id, timestamp, detections)"""
        self.on_detection_callbacks.append(callback)

    def add_track_callback(self, callback):
        """Register callback for tracks: fn(camera_id, timestamp, tracks)"""
        self.on_track_callbacks.append(callback)

    def add_event_callback(self, callback):
        """Register callback for events: fn(camera_id, timestamp, events)"""
        self.on_event_callbacks.append(callback)

    def add_alert_callback(self, callback):
        """Register callback for alerts: fn(alert)"""
        self.on_alert_callbacks.append(callback)

    def get_health(self) -> Dict[str, Any]:
        """Get overall system health."""
        camera_health = {}
        for cam_id, worker in self.camera_workers.items():
            camera_health[cam_id] = worker.get_health()
            
        return {
            "running": self.running,
            "uptime": (datetime.now() - self.stats["pipeline_start_time"]).total_seconds() if self.stats["pipeline_start_time"] else 0,
            "cameras_active": self.stats["cameras_active"],
            "total_frames_processed": self.stats["total_frames_processed"],
            "total_detections": self.stats["total_detections"],
            "total_tracks": self.stats["total_tracks"],
            "total_events": self.stats["total_events"],
            "total_alerts": self.stats["total_alerts"],
            "cameras": camera_health,
            "inference_stats": {cid: eng.get_stats() for cid, eng in self.inference_engines.items()},
            "tracker_stats": {cid: trk.get_stats() for cid, trk in self.trackers.items()},
            "alert_stats": self.alert_engine.get_stats()
        }

    def generate_synopsis_for_camera(self, camera_id: str, 
                                     original_duration: float,
                                     target_duration: float = 30.0) -> Dict[str, Any]:
        """Generate video synopsis for a camera's track data."""
        if camera_id not in self.trackers:
            return {"error": "Camera not found"}
            
        tracker = self.trackers[camera_id]
        tracks_data = tracker.get_all_tracks()
        
        return self.synopsis_engine.generate_synopsis(
            tracks_data=tracks_data,
            original_duration_sec=original_duration,
            target_duration_sec=target_duration
        )

    def get_active_alerts(self, severity_filter=None):
        """Get active alerts from alert engine."""
        return self.alert_engine.get_active_alerts(severity_filter)

    def acknowledge_alert(self, alert_id: str, user_id: str) -> bool:
        """Acknowledge an alert."""
        return self.alert_engine.acknowledge_alert(alert_id, user_id)

    def resolve_alert(self, alert_id: str) -> bool:
        """Resolve an alert."""
        return self.alert_engine.resolve_alert(alert_id)
