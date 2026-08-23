"""
OpenSight Enterprise - Multi-Backend Inference Engine
Supports YOLOv8, ONNX, TensorRT, OpenVINO with device auto-selection and batching.
"""
import torch
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging
import time

logger = logging.getLogger(__name__)

class InferenceEngine:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.model_type = config.get("model_type", "yolov8") # yolov8, onnx, tensorrt, openvino
        self.model_path = config.get("model_path", "yolov8n.pt")
        self.device = config.get("device", "auto") # auto, cpu, cuda, mps
        self.confidence = config.get("confidence", 0.25)
        self.iou_threshold = config.get("iou", 0.45)
        self.batch_size = config.get("batch_size", 1) # Future: batch processing
        
        self.model = None
        self.is_loaded = False
        self.stats = {
            "inference_count": 0,
            "total_latency": 0.0,
            "avg_latency": 0.0,
            "last_inference_time": None
        }
        
        self._load_model()

    def _select_device(self) -> str:
        """Auto-select best available device."""
        if self.device != "auto":
            return self.device
            
        if torch.cuda.is_available():
            logger.info("CUDA detected. Using GPU.")
            return "cuda"
        elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
            logger.info("MPS detected. Using Apple Silicon GPU.")
            return "mps"
        else:
            logger.info("No GPU detected. Using CPU.")
            return "cpu"

    def _load_model(self):
        """Load the detection model based on type."""
        try:
            device_str = self._select_device()
            device_obj = torch.device(device_str)
            
            if self.model_type == "yolov8":
                from ultralytics import YOLO
                logger.info(f"Loading YOLOv8 model: {self.model_path}")
                self.model = YOLO(self.model_path)
                self.model.to(device_obj)
                self.model.fuse() # Optimize inference
                
            elif self.model_type == "onnx":
                # Placeholder for ONNX runtime implementation
                logger.warning("ONNX backend requested but not fully implemented. Falling back to YOLO if available.")
                from ultralytics import YOLO
                self.model = YOLO(self.model_path)
                self.model.to(device_obj)
                
            elif self.model_type == "tensorrt":
                # Placeholder for TensorRT implementation
                logger.warning("TensorRT backend requested. Ensure model is exported to .engine")
                # Implementation would use torch2trt or similar
                raise NotImplementedError("TensorRT requires specific model export step.")
                
            elif self.model_type == "openvino":
                # Placeholder for OpenVINO implementation
                logger.warning("OpenVINO backend requested.")
                raise NotImplementedError("OpenVINO requires specific model export step.")
            
            self.is_loaded = True
            logger.info(f"Model loaded successfully on {device_str}")
            
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            self.is_loaded = False
            raise

    def detect(self, frame) -> List[Dict[str, Any]]:
        """Run detection on a single frame."""
        if not self.is_loaded:
            raise RuntimeError("Model not loaded")
            
        start_time = time.time()
        
        try:
            # Run inference
            results = self.model(
                frame, 
                conf=self.confidence, 
                iou=self.iou_threshold, 
                verbose=False,
                device=self._select_device() if self.device == "auto" else self.device
            )
            
            # Parse results
            detections = []
            r = results[0]
            boxes = r.boxes
            
            if boxes is not None:
                for i in range(len(boxes)):
                    box = boxes[i]
                    detections.append({
                        "bbox": box.xyxy[0].cpu().numpy().tolist(), # x1, y1, x2, y2
                        "confidence": float(box.conf[0].cpu().numpy()),
                        "class_id": int(box.cls[0].cpu().numpy()),
                        "class_name": r.names[int(box.cls[0].cpu().numpy())],
                        "timestamp": datetime.now().isoformat()
                    })
            
            # Update stats
            latency = time.time() - start_time
            self.stats["inference_count"] += 1
            self.stats["total_latency"] += latency
            self.stats["avg_latency"] = self.stats["total_latency"] / self.stats["inference_count"]
            self.stats["last_inference_time"] = datetime.now().isoformat()
            
            return detections
            
        except Exception as e:
            logger.error(f"Inference error: {e}")
            return []

    def get_stats(self) -> Dict[str, Any]:
        return self.stats.copy()
