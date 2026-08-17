"""
Video Synopsis Engine
Creates compressed timeline views by stacking non-overlapping events - core BriefCam capability
"""
import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict
import logging
import cv2

logger = logging.getLogger(__name__)


@dataclass
class TrackSegment:
    """Represents a segment of a track for synopsis generation"""
    track_id: int
    start_time: datetime
    end_time: datetime
    frames: List[Dict]  # [{timestamp, bbox, appearance}]
    camera_id: str
    object_class: str
    
    @property
    def duration(self) -> float:
        return (self.end_time - self.start_time).total_seconds()


@dataclass
class SynopsisConfig:
    """Configuration for synopsis generation"""
    output_fps: int = 30
    compression_ratio: float = 0.1  # Target: 10% of original duration
    min_track_duration: float = 1.0  # seconds
    max_concurrent_objects: int = 5  # Max objects shown simultaneously
    preserve_audio: bool = False
    add_timestamp_overlay: bool = True
    background_model: str = "median"  # "median", "first_frame", "custom"


class VideoSynopsisEngine:
    """
    Enterprise video synopsis engine comparable to BriefCam's core technology
    Creates time-compressed videos by stacking non-conflicting events
    """
    
    def __init__(self, config: Optional[SynopsisConfig] = None):
        self.config = config or SynopsisConfig()
        self.track_segments: Dict[str, List[TrackSegment]] = defaultdict(list)  # camera_id -> segments
        self.background_cache: Dict[str, np.ndarray] = {}  # camera_id -> background frame
        
        logger.info("Video Synopsis Engine initialized")
    
    def add_track_segment(self, segment: TrackSegment):
        """Add a track segment for synopsis processing"""
        if segment.duration < self.config.min_track_duration:
            logger.debug(f"Skipping short segment: {segment.duration:.2f}s")
            return
        
        self.track_segments[segment.camera_id].append(segment)
        logger.debug(f"Added track segment: {segment.track_id}, duration: {segment.duration:.2f}s")
    
    def generate_background(self, camera_id: str, frames: List[np.ndarray], 
                           method: str = "median") -> np.ndarray:
        """Generate background model from frames"""
        if not frames:
            raise ValueError("No frames provided")
        
        if method == "median":
            # Stack frames and compute median
            stack = np.stack(frames)
            background = np.median(stack, axis=0).astype(np.uint8)
        elif method == "first_frame":
            background = frames[0]
        else:
            raise ValueError(f"Unknown background method: {method}")
        
        self.background_cache[camera_id] = background
        logger.info(f"Generated background model for camera {camera_id}: {background.shape}")
        return background
    
    def create_synopsis_timeline(self, camera_id: str) -> List[Tuple[datetime, List[TrackSegment]]]:
        """
        Create optimized timeline by stacking non-overlapping tracks
        Returns: [(synopsis_time, [segments_to_display]), ...]
        """
        segments = self.track_segments.get(camera_id, [])
        if not segments:
            return []
        
        # Sort segments by start time
        sorted_segments = sorted(segments, key=lambda s: s.start_time)
        
        # Timeline optimization: pack segments to minimize gaps while avoiding overlaps
        timeline = []
        current_synopsis_time = datetime.now()
        
        # Group segments that can be displayed together
        active_groups = []
        current_group = []
        group_end_time = None
        
        for segment in sorted_segments:
            if group_end_time is None or segment.start_time >= group_end_time:
                # Start new group
                if current_group:
                    active_groups.append((current_synopsis_time, current_group))
                
                current_group = [segment]
                group_end_time = segment.end_time
                current_synopsis_time += timedelta(seconds=segment.duration * self.config.compression_ratio)
            else:
                # Check if segment can be added to current group without overlap
                can_add = True
                for existing in current_group:
                    if self._segments_overlap(existing, segment):
                        can_add = False
                        break
                
                if can_add and len(current_group) < self.config.max_concurrent_objects:
                    current_group.append(segment)
                    group_end_time = max(group_end_time, segment.end_time)
                else:
                    # Start new group
                    active_groups.append((current_synopsis_time, current_group))
                    current_group = [segment]
                    group_end_time = segment.end_time
                    current_synopsis_time += timedelta(seconds=segment.duration * self.config.compression_ratio)
        
        # Add last group
        if current_group:
            active_groups.append((current_synopsis_time, current_group))
        
        logger.info(f"Created synopsis timeline: {len(active_groups)} groups from {len(segments)} segments")
        return active_groups
    
    def _segments_overlap(self, seg1: TrackSegment, seg2: TrackSegment) -> bool:
        """Check if two segments spatially overlap in any frame"""
        # Simplified: check bounding box overlap at similar timestamps
        for frame1 in seg1.frames[:10]:  # Sample first 10 frames
            for frame2 in seg2.frames[:10]:
                bbox1 = frame1.get('bbox', (0, 0, 0, 0))
                bbox2 = frame2.get('bbox', (0, 0, 0, 0))
                
                if self._bboxes_overlap(bbox1, bbox2):
                    return True
        return False
    
    def _bboxes_overlap(self, bbox1: Tuple[int, int, int, int], 
                       bbox2: Tuple[int, int, int, int], 
                       threshold: float = 0.3) -> bool:
        """Check if two bounding boxes overlap beyond threshold"""
        x1_min, y1_min, x1_max, y1_max = bbox1
        x2_min, y2_min, x2_max, y2_max = bbox2
        
        # Calculate intersection
        inter_x_min = max(x1_min, x2_min)
        inter_y_min = max(y1_min, y2_min)
        inter_x_max = min(x1_max, x2_max)
        inter_y_max = min(y1_max, y2_max)
        
        if inter_x_min >= inter_x_max or inter_y_min >= inter_y_max:
            return False
        
        intersection = (inter_x_max - inter_x_min) * (inter_y_max - inter_y_min)
        
        # Calculate union
        area1 = (x1_max - x1_min) * (y1_max - y1_min)
        area2 = (x2_max - x2_min) * (y2_max - y2_min)
        union = area1 + area2 - intersection
        
        iou = intersection / union if union > 0 else 0
        return iou > threshold
    
    def render_synopsis_video(self, camera_id: str, output_path: str, 
                             background: Optional[np.ndarray] = None) -> str:
        """
        Render synopsis video to file
        Returns path to generated video
        """
        timeline = self.create_synopsis_timeline(camera_id)
        if not timeline:
            logger.warning(f"No segments to render for camera {camera_id}")
            return ""
        
        # Get or generate background
        if background is None:
            if camera_id in self.background_cache:
                background = self.background_cache[camera_id]
            else:
                logger.warning(f"No background available for camera {camera_id}")
                # Create dummy background
                background = np.zeros((720, 1280, 3), dtype=np.uint8)
        
        height, width = background.shape[:2]
        
        # Initialize video writer
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_path, fourcc, self.config.output_fps, (width, height))
        
        if not out.isOpened():
            logger.error(f"Failed to open video writer: {output_path}")
            return ""
        
        total_frames = 0
        
        for synopsis_time, segments in timeline:
            # Create frame with background
            frame = background.copy()
            
            # Draw each segment's objects at current position
            for segment in segments:
                # Find closest frame to synopsis time
                closest_frame = self._find_closest_frame(segment, synopsis_time)
                if closest_frame:
                    bbox = closest_frame.get('bbox', (0, 0, 0, 0))
                    appearance = closest_frame.get('appearance', None)
                    
                    # Draw bounding box
                    x1, y1, x2, y2 = map(int, bbox)
                    color = self._get_class_color(segment.object_class)
                    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                    
                    # Draw label
                    label = f"{segment.object_class}:{segment.track_id}"
                    cv2.putText(frame, label, (x1, y1 - 10), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
            
            # Add timestamp overlay if enabled
            if self.config.add_timestamp_overlay:
                timestamp_str = synopsis_time.strftime("%Y-%m-%d %H:%M:%S")
                cv2.putText(frame, timestamp_str, (10, 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
            
            out.write(frame)
            total_frames += 1
        
        out.release()
        logger.info(f"Synopsis video rendered: {output_path} ({total_frames} frames)")
        return output_path
    
    def _find_closest_frame(self, segment: TrackSegment, target_time: datetime) -> Optional[Dict]:
        """Find frame closest to target time"""
        if not segment.frames:
            return None
        
        # Simple approach: return first frame (can be enhanced with interpolation)
        return segment.frames[0]
    
    def _get_class_color(self, object_class: str) -> Tuple[int, int, int]:
        """Get color for object class (BGR format)"""
        colors = {
            "person": (0, 255, 0),      # Green
            "car": (255, 0, 0),         # Blue
            "truck": (255, 0, 0),       # Blue
            "bus": (255, 0, 0),         # Blue
            "bicycle": (0, 255, 255),   # Yellow
            "motorcycle": (0, 255, 255),# Yellow
            "bag": (0, 0, 255),         # Red
            "default": (255, 255, 255)  # White
        }
        return colors.get(object_class, colors["default"])
    
    def get_synopsis_statistics(self, camera_id: str) -> Dict:
        """Get statistics about synopsis data"""
        segments = self.track_segments.get(camera_id, [])
        
        if not segments:
            return {"total_segments": 0}
        
        total_duration = sum(s.duration for s in segments)
        avg_duration = total_duration / len(segments)
        
        class_counts = defaultdict(int)
        for s in segments:
            class_counts[s.object_class] += 1
        
        return {
            "total_segments": len(segments),
            "total_duration_seconds": total_duration,
            "average_duration_seconds": avg_duration,
            "compression_ratio": self.config.compression_ratio,
            "estimated_synopsis_duration": total_duration * self.config.compression_ratio,
            "object_classes": dict(class_counts),
            "max_concurrent_objects": self.config.max_concurrent_objects
        }
    
    def clear_camera_data(self, camera_id: str):
        """Clear all data for a camera"""
        self.track_segments.pop(camera_id, None)
        self.background_cache.pop(camera_id, None)
        logger.info(f"Cleared synopsis data for camera {camera_id}")
