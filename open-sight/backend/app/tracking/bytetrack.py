"""ByteTrack tracking adapter using supervision library."""
from typing import Any, Optional
import numpy as np


class ByteTrackAdapter:
    """Adapter for ByteTrack multi-object tracking."""
    
    def __init__(self):
        try:
            import supervision as sv
        except ImportError as exc:
            raise RuntimeError("Install supervision to enable tracking") from exc
        
        # Configure ByteTrack with reasonable defaults
        self.tracker = sv.ByteTrack(
            track_activation_threshold=0.25,
            lost_track_buffer=30,
            match_threshold=0.8,
            minimum_consecutive_frames=3,
        )
        self._sv = sv
    
    def update(self, detections: Any, frame: Optional[np.ndarray] = None) -> list[dict]:
        """
        Update tracker with new detections.
        
        Args:
            detections: Supervision Detections object with boxes and confidence
            frame: Optional frame for visual debugging
            
        Returns:
            List of tracked objects with track_id, bbox, class, confidence
        """
        try:
            tracked = self.tracker.update_with_detections(detections)
        except Exception:
            # Fallback if tracker fails
            return []
        
        results = []
        for i, det in enumerate(detections):
            if hasattr(tracked, 'tracker_id') and len(tracked.tracker_id) > i:
                track_id = int(tracked.tracker_id[i])
            else:
                track_id = None
            
            results.append({
                "track_id": track_id,
                "bbox": det.xyxy[i].tolist() if hasattr(det, 'xyxy') else [],
                "confidence": float(det.confidence[i]) if hasattr(det, 'confidence') else 0.0,
                "class_name": det.class_id[i] if hasattr(det, 'class_id') else -1,
            })
        
        return results
    
    def reset(self):
        """Reset tracker state (call when camera reconnects)."""
        self.tracker.reset()


def create_supervision_detections(yolo_results, class_names: dict) -> Any:
    """
    Convert YOLO results to Supervision Detections format.
    
    Args:
        yolo_results: Results from ultralytics YOLO model
        class_names: Dict mapping class IDs to names
        
    Returns:
        Supervision Detections object
    """
    import supervision as sv
    
    all_boxes = []
    all_confidences = []
    all_class_ids = []
    
    for result in yolo_results:
        boxes = result.boxes
        if boxes is None or len(boxes) == 0:
            continue
            
        all_boxes.extend(boxes.xyxy.cpu().numpy())
        all_confidences.extend(boxes.conf.cpu().numpy())
        all_class_ids.extend(boxes.cls.cpu().numpy().astype(int))
    
    if not all_boxes:
        return sv.Detections.empty()
    
    return sv.Detections(
        xyxy=np.array(all_boxes),
        confidence=np.array(all_confidences),
        class_id=np.array(all_class_ids),
    )
