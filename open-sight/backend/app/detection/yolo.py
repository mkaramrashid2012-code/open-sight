from dataclasses import dataclass
from typing import Any
from app.core.config import settings

@dataclass
class DetectionResult:
    class_name: str
    confidence: float
    bbox: list[float]

class YOLODetector:
    def __init__(self, model_path: str | None = None):
        try:
            from ultralytics import YOLO
        except ImportError as exc:
            raise RuntimeError("Install backend requirements to enable YOLO") from exc
        self.model = YOLO(model_path or settings.model_path)

    def predict(self, frame: Any) -> list[DetectionResult]:
        results = self.model.predict(frame, conf=settings.confidence_threshold, verbose=False)
        output: list[DetectionResult] = []
        names = self.model.names
        for result in results:
            boxes = result.boxes
            for i in range(len(boxes)):
                cls = int(boxes.cls[i].item())
                output.append(DetectionResult(str(names[cls]), float(boxes.conf[i].item()), boxes.xyxy[i].tolist()))
        return output
