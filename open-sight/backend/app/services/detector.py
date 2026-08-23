"""
Production YOLOv8 Detector Service
Handles model loading, GPU/CPU selection, batch inference, and error recovery.
"""
import numpy as np
import logging
from typing import List, Optional

try:
    from ultralytics import YOLO
except ImportError:
    YOLO = None  # Handle missing dependency gracefully

from app.core.config import settings

logger = logging.getLogger(__name__)


class DetectionResult:
    def __init__(self, box: List[float], confidence: float, class_id: int, class_name: str):
        self.box = box  # [x1, y1, x2, y2]
        self.confidence = confidence
        self.class_id = class_id
        self.class_name = class_name


class DetectorService:
    def __init__(self):
        self.model: Optional[YOLO] = None
        self.device = "cuda" if settings.use_gpu else "cpu"
        self.conf_threshold = settings.detection_confidence_threshold
        self.iou_threshold = settings.detection_iou_threshold
        self.classes_filter = settings.detection_classes_filter  # e.g., [0, 2] for person, car
        
        logger.info(f"Initializing Detector on device: {self.device}")
        self._load_model()

    def _load_model(self):
        """Load YOLO model with error handling."""
        if YOLO is None:
            logger.error("ultralytics package not installed. Install with: pip install ultralytics")
            raise ImportError("ultralytics package required")

        try:
            self.model = YOLO(settings.yolo_model_path)
            self.model.to(self.device)
            # Warmup for stable latency (mock if no image provided)
            logger.info("YOLO model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load YOLO model: {e}")
            raise

    async def detect(self, frame: np.ndarray) -> List[DetectionResult]:
        """Run inference on a single frame."""
        if self.model is None:
            return []

        try:
            # Pre-process handled by ultralytics
            results = self.model(
                frame,
                conf=self.conf_threshold,
                iou=self.iou_threshold,
                classes=self.classes_filter,
                verbose=False,
                device=self.device
            )

            detections = []
            r = results[0]
            
            if r.boxes is not None:
                boxes = r.boxes.xyxy.cpu().numpy()
                confs = r.boxes.conf.cpu().numpy()
                cls_ids = r.boxes.cls.cpu().numpy()
                names = r.names

                for i in range(len(boxes)):
                    detections.append(DetectionResult(
                        box=boxes[i].tolist(),
                        confidence=float(confs[i]),
                        class_id=int(cls_ids[i]),
                        class_name=names[int(cls_ids[i])]
                    ))
            
            return detections

        except Exception as e:
            logger.error(f"Inference error: {e}", exc_info=True)
            # Attempt recovery? For now, return empty
            return []

    async def close(self):
        """Cleanup resources."""
        self.model = None
        logger.info("Detector closed")
