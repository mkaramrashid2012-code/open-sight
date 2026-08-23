"""
OpenSight Enterprise - Advanced Tracking Engine
Supports ByteTrack, BoT-SORT with track lifecycle management and trajectory storage.
"""
import numpy as np
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging
from collections import deque

logger = logging.getLogger(__name__)

class Track:
    def __init__(self, track_id: int, detection: Dict[str, Any], frame_time: datetime):
        self.track_id = track_id
        self.state = "active" # active, lost, terminated
        self.age = 0
        self.total_count = 1
        self.hits = 1
        self.frame_id_start = frame_time
        self.frame_id_last = frame_time
        
        # Bounding box state
        self.tlwh = np.array(detection["bbox"], dtype=np.float32) # x, y, w, h
        self.confidence = detection["confidence"]
        
        # Trajectory history (max 100 points)
        self.trajectory = deque(maxlen=100)
        self.trajectory.append((frame_time, self.tlwh.copy()))
        
        # Velocity & Direction
        self.velocity = np.zeros(2)
        self.direction = None
        
        # ReID Embedding (optional)
        self.embedding: Optional[np.ndarray] = None

    def update(self, detection: Dict[str, Any], frame_time: datetime):
        """Update track with new detection."""
        self.tlwh = np.array(detection["bbox"], dtype=np.float32)
        self.confidence = detection["confidence"]
        self.hits += 1
        self.age += 1
        self.frame_id_last = frame_time
        
        self.trajectory.append((frame_time, self.tlwh.copy()))
        
        # Calculate velocity if enough history
        if len(self.trajectory) >= 2:
            prev_t, prev_box = self.trajectory[-2]
            curr_t, curr_box = self.trajectory[-1]
            
            dt = (curr_t - prev_t).total_seconds()
            if dt > 0:
                dx = (curr_box[0] - prev_box[0]) / dt
                dy = (curr_box[1] - prev_box[1]) / dt
                self.velocity = np.array([dx, dy])
                
                # Simple direction classification
                if abs(dx) > abs(dy):
                    self.direction = "right" if dx > 0 else "left"
                else:
                    self.direction = "down" if dy > 0 else "up"

    def mark_lost(self):
        self.state = "lost"
    
    def mark_terminated(self):
        self.state = "terminated"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "track_id": self.track_id,
            "state": self.state,
            "age": self.age,
            "hits": self.hits,
            "bbox": self.tlwh.tolist(),
            "confidence": float(self.confidence),
            "velocity": self.velocity.tolist(),
            "direction": self.direction,
            "start_time": self.frame_id_start.isoformat(),
            "last_time": self.frame_id_last.isoformat(),
            "trajectory_length": len(self.trajectory)
        }

class AdvancedTracker:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.tracker_type = config.get("tracker_type", "bytetrack") # bytetrack, botsort
        self.track_thresh = config.get("track_thresh", 0.5)
        self.match_thresh = config.get("match_thresh", 0.8)
        self.min_box_area = config.get("min_box_area", 10)
        self.max_age = config.get("max_age", 30) # Frames to keep lost track
        
        self.tracks: Dict[int, Track] = {}
        self.next_id = 1
        self.frame_count = 0
        
        # Stats
        self.stats = {
            "active_tracks": 0,
            "total_tracks_created": 0,
            "tracks_lost": 0,
            "tracks_terminated": 0
        }

    def update(self, detections: List[Dict[str, Any]], frame_time: datetime) -> List[Track]:
        """
        Update tracker with new detections.
        Simplified ByteTrack-like logic for demonstration.
        Production should use full ByteTrack/BoT-SORT library.
        """
        self.frame_count += 1
        active_tracks = []
        
        # Separate high/low confidence detections
        high_conf_dets = [d for d in detections if d["confidence"] >= self.track_thresh]
        low_conf_dets = [d for d in detections if d["confidence"] < self.track_thresh]
        
        # Get active tracks
        active_track_list = [t for t in self.tracks.values() if t.state == "active"]
        
        # --- Association Step (Simplified IoU Matching) ---
        unmatched_dets = high_conf_dets.copy()
        matched_track_ids = set()
        
        for det in high_conf_dets:
            best_iou = 0
            best_track = None
            
            for track in active_track_list:
                if track.track_id in matched_track_ids:
                    continue
                
                iou = self._calculate_iou(det["bbox"], track.tlwh)
                if iou > self.match_thresh and iou > best_iou:
                    best_iou = iou
                    best_track = track
            
            if best_track:
                best_track.update(det, frame_time)
                matched_track_ids.add(best_track.track_id)
                if det in unmatched_dets:
                    unmatched_dets.remove(det)
            else:
                # Create new track
                new_track = Track(self.next_id, det, frame_time)
                self.tracks[self.next_id] = new_track
                self.next_id += 1
                self.stats["total_tracks_created"] += 1
                active_tracks.append(new_track)
        
        # Add previously matched tracks
        for track in active_track_list:
            if track.track_id in matched_track_ids:
                active_tracks.append(track)
        
        # --- Handle Lost Tracks ---
        for track_id, track in list(self.tracks.items()):
            if track.state != "active":
                continue
            
            if track.track_id not in matched_track_ids:
                track.mark_lost()
                track.age += 1
                self.stats["tracks_lost"] += 1
                
                # Check if should be terminated
                if track.age > self.max_age:
                    track.mark_terminated()
                    self.stats["tracks_terminated"] += 1
                    del self.tracks[track_id]
        
        self.stats["active_tracks"] = len([t for t in self.tracks.values() if t.state == "active"])
        return active_tracks

    def _calculate_iou(self, det_bbox, track_tlwh) -> float:
        """Calculate Intersection over Union."""
        # Convert track tlwh to xyxy
        tx, ty, tw, th = track_tlwh
        track_xyxy = [tx, ty, tx + tw, ty + th]
        
        # Det is already xyxy
        dx1, dy1, dx2, dy2 = det_bbox
        
        # Intersection
        xi1 = max(dx1, track_xyxy[0])
        yi1 = max(dy1, track_xyxy[1])
        xi2 = min(dx2, track_xyxy[2])
        yi2 = min(dy2, track_xyxy[3])
        
        inter_area = max(0, xi2 - xi1) * max(0, yi2 - yi1)
        
        # Union
        det_area = (dx2 - dx1) * (dy2 - dy1)
        track_area = tw * th
        union_area = det_area + track_area - inter_area
        
        if union_area == 0:
            return 0.0
            
        return inter_area / union_area

    def get_all_tracks(self) -> List[Dict[str, Any]]:
        return [t.to_dict() for t in self.tracks.values()]

    def get_stats(self) -> Dict[str, Any]:
        return self.stats.copy()
