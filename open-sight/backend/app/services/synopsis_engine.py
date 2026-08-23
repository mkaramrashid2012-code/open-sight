"""
OpenSight Enterprise - Video Synopsis Engine
Compresses hours of footage into seconds by compositing non-colliding tracks.
"""
import cv2
import numpy as np
from typing import List, Dict, Any, Tuple
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class VideoSynopsisEngine:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.output_fps = config.get("output_fps", 15)
        self.collision_threshold = config.get("collision_threshold", 0.2) # IoU threshold
        
    def generate_synopsis(self, tracks_data: List[Dict[str, Any]], 
                          original_duration_sec: float,
                          target_duration_sec: float = 30.0) -> Dict[str, Any]:
        """
        Generate a video synopsis from track data.
        
        Args:
            tracks_data: List of track dictionaries with trajectories
            original_duration_sec: Duration of original video in seconds
            target_duration_sec: Target duration for synopsis
            
        Returns:
            Synopsis plan (metadata for rendering)
        """
        if not tracks_data:
            return {"status": "empty", "frames": []}
            
        # Calculate time compression ratio
        compression_ratio = original_duration_sec / target_duration_sec
        logger.info(f"Compressing {original_duration_sec}s into {target_duration_sec}s (Ratio: {compression_ratio:.1f}x)")
        
        # Extract all track segments
        segments = []
        for track in tracks_data:
            trajectory = track.get("trajectory", [])
            if len(trajectory) < 2:
                continue
                
            # Create segment info
            segment = {
                "track_id": track["track_id"],
                "start_time": track.get("start_time"),
                "end_time": track.get("last_time"),
                "trajectory": trajectory,
                "class_name": track.get("class_name", "object"),
                "color": self._get_color_for_class(track.get("class_name", "person"))
            }
            segments.append(segment)
        
        # Time-shift segments to avoid collisions
        shifted_segments = self._time_shift_segments(segments, compression_ratio, target_duration_sec)
        
        # Generate frame plan
        total_frames = int(target_duration_sec * self.output_fps)
        frame_plan = []
        
        for frame_idx in range(total_frames):
            frame_time = frame_idx / self.output_fps
            objects_in_frame = []
            
            for seg in shifted_segments:
                # Check if object should appear in this frame based on shifted time
                obj_appears = self._is_object_visible(seg, frame_time, target_duration_sec)
                if obj_appears:
                    # Get position at this time
                    pos = self._interpolate_position(seg, frame_time, target_duration_sec)
                    if pos:
                        objects_in_frame.append({
                            "track_id": seg["track_id"],
                            "bbox": pos,
                            "color": seg["color"],
                            "class": seg["class_name"]
                        })
            
            frame_plan.append({
                "frame_number": frame_idx,
                "timestamp": frame_time,
                "objects": objects_in_frame
            })
        
        return {
            "status": "success",
            "compression_ratio": compression_ratio,
            "original_duration": original_duration_sec,
            "synopsis_duration": target_duration_sec,
            "total_tracks": len(segments),
            "tracks_processed": len(shifted_segments),
            "total_frames": total_frames,
            "fps": self.output_fps,
            "frame_plan": frame_plan[:10] # Return first 10 frames as sample
        }

    def _time_shift_segments(self, segments: List[Dict], 
                             compression_ratio: float, 
                             target_duration: float) -> List[Dict]:
        """
        Shift segments in time to minimize collisions while maintaining order.
        Simplified algorithm: random shift within bounds.
        Production would use optimization algorithms.
        """
        shifted = []
        
        for seg in segments:
            # Compress trajectory duration
            original_span = len(seg["trajectory"])
            compressed_span = max(2, int(original_span / compression_ratio))
            
            # Random start time within target duration
            import random
            max_start = max(0, target_duration - (compressed_span / self.output_fps))
            start_offset = random.uniform(0, max_start)
            
            shifted_seg = seg.copy()
            shifted_seg["shifted_start"] = start_offset
            shifted_seg["compressed_span"] = compressed_span
            shifted.append(shifted_seg)
        
        return shifted

    def _is_object_visible(self, segment: Dict, current_time: float, total_duration: float) -> bool:
        """Check if object should be visible at current_time."""
        start = segment.get("shifted_start", 0)
        span_frames = segment.get("compressed_span", 10)
        span_seconds = span_frames / self.output_fps
        
        return start <= current_time < (start + span_seconds)

    def _interpolate_position(self, segment: Dict, current_time: float, total_duration: float) -> List[float]:
        """Interpolate bounding box position for current time."""
        trajectory = segment.get("trajectory", [])
        if not trajectory:
            return None
            
        start = segment.get("shifted_start", 0)
        span_frames = segment.get("compressed_span", len(trajectory))
        
        # Calculate progress through the compressed segment
        elapsed = current_time - start
        if elapsed < 0:
            return None
            
        progress = min(1.0, elapsed / (span_frames / self.output_fps))
        traj_index = int(progress * (len(trajectory) - 1))
        
        # Return bbox at that index (simplified - trajectory stores time+bbox)
        if traj_index < len(trajectory):
            # Trajectory format: [(datetime, [x,y,w,h]), ...]
            return trajectory[traj_index][1]
        
        return trajectory[-1][1] if trajectory else None

    def _get_color_for_class(self, class_name: str) -> Tuple[int, int, int]:
        """Get BGR color for object class."""
        colors = {
            "person": (0, 255, 0),      # Green
            "car": (255, 0, 0),         # Blue
            "truck": (255, 0, 0),
            "bus": (255, 0, 0),
            "bicycle": (0, 255, 255),   # Cyan
            "motorcycle": (0, 255, 255),
            "default": (0, 0, 255)      # Red
        }
        return colors.get(class_name.lower(), colors["default"])

    def render_frame(self, base_frame: np.ndarray, objects: List[Dict]) -> np.ndarray:
        """
        Render objects onto a base frame.
        
        Args:
            base_frame: Background frame (numpy array)
            objects: List of objects with bbox and color
            
        Returns:
            Rendered frame
        """
        output = base_frame.copy()
        
        for obj in objects:
            bbox = obj.get("bbox")
            if not bbox:
                continue
                
            # bbox format: [x, y, w, h] or [x1, y1, x2, y2]
            if len(bbox) == 4:
                if max(bbox) > 1000: # Likely xyxy
                    x1, y1, x2, y2 = map(int, bbox)
                    w, h = x2 - x1, y2 - y1
                else: # Likely xywh
                    x1, y1, w, h = map(int, bbox)
                    x2, y2 = x1 + w, y1 + h
                    
                color = obj.get("color", (0, 255, 0))
                
                # Draw rectangle
                cv2.rectangle(output, (x1, y1), (x2, y2), color, 2)
                
                # Draw label
                label = f"{obj.get('class', 'obj')}:{obj.get('track_id')}"
                cv2.putText(output, label, (x1, y1 - 5), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
        
        return output
