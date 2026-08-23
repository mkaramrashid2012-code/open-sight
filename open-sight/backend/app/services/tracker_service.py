"""
Production ByteTrack Tracker Service
Handles track lifecycle, state machine, trajectory storage, and quality scoring.
"""
import logging
from typing import List, Dict
from datetime import datetime

from app.services.detector import DetectionResult
from app.core.config import settings

logger = logging.getLogger(__name__)


class TrackState:
    NEW = "NEW"
    TENTATIVE = "TENTATIVE"
    ACTIVE = "ACTIVE"
    LOST = "LOST"
    RECOVERED = "RECOVERED"
    ENDED = "ENDED"


class TrackedObject:
    def __init__(self, track_id: int, detection: DetectionResult):
        self.track_id = track_id
        self.state = TrackState.NEW
        self.class_id = detection.class_id
        self.class_name = detection.class_name
        
        # Current box
        self.box = detection.box
        self.confidence = detection.confidence
        
        # Lifecycle
        self.first_seen = datetime.utcnow()
        self.last_seen = datetime.utcnow()
        self.age = 0
        self.consecutive_misses = 0
        
        # History
        self.trajectory: List[Dict] = []  # List of {box, timestamp}
        self.detection_count = 0
        self.quality_score = 0.0
        
        self._update_trajectory()

    def update(self, detection: DetectionResult):
        """Update track with new detection."""
        self.box = detection.box
        self.confidence = detection.confidence
        self.last_seen = datetime.utcnow()
        self.age += 1
        self.consecutive_misses = 0
        self.detection_count += 1
        
        if self.state == TrackState.NEW:
            self.state = TrackState.TENTATIVE
            if self.detection_count >= 3:
                self.state = TrackState.ACTIVE
        elif self.state == TrackState.LOST:
            self.state = TrackState.RECOVERED
            
        self._update_trajectory()
        self._calculate_quality()

    def predict(self):
        """Called when no detection matched (predict step)."""
        self.consecutive_misses += 1
        if self.state == TrackState.ACTIVE:
            if self.consecutive_misses > settings.track_max_misses:
                self.state = TrackState.LOST
        elif self.state == TrackState.LOST:
            if self.consecutive_misses > settings.track_max_misses * 2:
                self.state = TrackState.ENDED

    def _update_trajectory(self):
        """Add current box to history."""
        self.trajectory.append({
            "box": self.box,
            "timestamp": self.last_seen.isoformat(),
            "confidence": self.confidence
        })
        # Limit trajectory size
        max_len = settings.track_trajectory_max_length
        if len(self.trajectory) > max_len:
            self.trajectory = self.trajectory[-max_len:]

    def _calculate_quality(self):
        """Calculate track quality score based on consistency and confidence."""
        if self.detection_count == 0:
            self.quality_score = 0.0
            return
            
        avg_conf = self.confidence # Simplified: use current conf
        consistency = 1.0 - (self.consecutive_misses / (settings.track_max_misses + 1))
        self.quality_score = (avg_conf + consistency) / 2.0


class TrackerService:
    def __init__(self):
        self.tracks: Dict[int, TrackedObject] = {}
        self.next_track_id = 1
        self.max_age = settings.track_max_age
        logger.info("TrackerService initialized")

    async def update(self, detections: List[DetectionResult]) -> List[TrackedObject]:
        """
        Main update step: 
        1. Associate detections with existing tracks (simplified IoU matching)
        2. Update matched tracks
        3. Create new tracks for unmatched detections
        4. Predict missed tracks
        """
        
        # Simple IoU Matching (Placeholder for full ByteTrack logic)
        used_detections = set()
        matched_tracks = set()

        # Try to match existing active tracks
        for track_id, track in list(self.tracks.items()):
            if track.state == TrackState.ENDED:
                continue
                
            best_iou = 0.0
            best_det_idx = -1
            
            for i, det in enumerate(detections):
                if i in used_detections:
                    continue
                if det.class_id != track.class_id:
                    continue
                    
                iou = self._calculate_iou(track.box, det.box)
                if iou > best_iou and iou > settings.track_iou_threshold:
                    best_iou = iou
                    best_det_idx = i
            
            if best_det_idx != -1:
                # Match found
                track.update(detections[best_det_idx])
                used_detections.add(best_det_idx)
                matched_tracks.add(track_id)
            else:
                # No match
                track.predict()

        # Create new tracks for unmatched detections
        for i, det in enumerate(detections):
            if i not in used_detections:
                new_track = TrackedObject(self.next_track_id, det)
                self.tracks[self.next_track_id] = new_track
                self.next_track_id += 1

        # Cleanup ended tracks
        self._cleanup_ended_tracks()

        return [t for t in self.tracks.values() if t.state != TrackState.ENDED]

    def _calculate_iou(self, box1: List[float], box2: List[float]) -> float:
        """Calculate Intersection over Union."""
        x1 = max(box1[0], box2[0])
        y1 = max(box1[1], box2[1])
        x2 = min(box1[2], box2[2])
        y2 = min(box1[3], box2[3])
        
        inter_area = max(0, x2 - x1) * max(0, y2 - y1)
        
        box1_area = (box1[2] - box1[0]) * (box1[3] - box1[1])
        box2_area = (box2[2] - box2[0]) * (box2[3] - box2[1])
        
        union_area = box1_area + box2_area - inter_area
        
        if union_area == 0:
            return 0.0
            
        return inter_area / union_area

    def _cleanup_ended_tracks(self):
        """Remove tracks that have ended or are too old."""
        now = datetime.utcnow()
        to_remove = []
        
        for track_id, track in self.tracks.items():
            if track.state == TrackState.ENDED:
                to_remove.append(track_id)
            elif (now - track.last_seen).total_seconds() > self.max_age:
                track.state = TrackState.ENDED
                to_remove.append(track_id)
                
        for tid in to_remove:
            del self.tracks[tid]
