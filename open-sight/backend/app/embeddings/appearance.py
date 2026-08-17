"""
Deep Appearance Embeddings Engine
Generates robust feature vectors for ReID using multi-modal deep learning features
Comparable to BriefCam's appearance matching without cloud dependencies
"""
import numpy as np
from typing import List, Dict, Optional, Tuple, Union
from dataclasses import dataclass
from datetime import datetime
import logging
import cv2

try:
    import torch
    import torch.nn as nn
    from torchvision import models, transforms
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("PyTorch not available. Using fallback feature extraction.")

logger = logging.getLogger(__name__)


@dataclass
class AppearanceEmbedding:
    """Represents appearance embedding for a detected object"""
    track_id: int
    camera_id: str
    timestamp: datetime
    embedding: np.ndarray  # Feature vector
    bbox: Tuple[int, int, int, int]
    object_class: str
    confidence: float
    metadata: Dict = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
    
    def to_dict(self) -> Dict:
        return {
            "track_id": self.track_id,
            "camera_id": self.camera_id,
            "timestamp": self.timestamp.isoformat(),
            "embedding": self.embedding.tolist(),
            "bbox": self.bbox,
            "object_class": self.object_class,
            "confidence": self.confidence,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'AppearanceEmbedding':
        return cls(
            track_id=data["track_id"],
            camera_id=data["camera_id"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            embedding=np.array(data["embedding"]),
            bbox=tuple(data["bbox"]),
            object_class=data["object_class"],
            confidence=data["confidence"],
            metadata=data.get("metadata", {})
        )


class DeepAppearanceEngine:
    """
    Enterprise-grade appearance embedding engine for ReID
    Uses deep learning features when available, falls back to traditional CV features
    """
    
    def __init__(self, model_name: str = "resnet50", use_gpu: bool = False):
        self.model_name = model_name
        self.use_gpu = use_gpu and TORCH_AVAILABLE and torch.cuda.is_available()
        self.model = None
        self.transform = None
        self.device = None
        
        if TORCH_AVAILABLE:
            self._initialize_model()
        else:
            logger.info("Using traditional CV features (PyTorch not available)")
        
        # Feature cache for efficiency
        self.feature_cache: Dict[int, AppearanceEmbedding] = {}
        self.cache_max_size = 10000
        
        logger.info(f"Deep Appearance Engine initialized (GPU: {self.use_gpu})")
    
    def _initialize_model(self):
        """Initialize deep learning model for feature extraction"""
        try:
            self.device = torch.device("cuda" if self.use_gpu else "cpu")
            
            # Load pre-trained ResNet50
            if self.model_name == "resnet50":
                backbone = models.resnet50(weights=models.ResNet50_Weights.IMAGENET1K_V1)
                # Remove final classification layer to get features
                self.model = nn.Sequential(*list(backbone.children())[:-1])
                self.feature_dim = 2048
            elif self.model_name == "resnet18":
                backbone = models.resnet18(weights=models.ResNet18_Weights.IMAGENET1K_V1)
                self.model = nn.Sequential(*list(backbone.children())[:-1])
                self.feature_dim = 512
            else:
                raise ValueError(f"Unknown model: {self.model_name}")
            
            self.model.to(self.device)
            self.model.eval()
            
            # Define image transformation
            self.transform = transforms.Compose([
                transforms.ToPILImage(),
                transforms.Resize((256, 128)),  # Standard person ReID size
                transforms.ToTensor(),
                transforms.Normalize(
                    mean=[0.485, 0.456, 0.406],
                    std=[0.229, 0.224, 0.225]
                )
            ])
            
            logger.info(f"Loaded {self.model_name} for feature extraction (dim={self.feature_dim})")
        
        except Exception as e:
            logger.error(f"Failed to initialize deep model: {e}. Falling back to CV features.")
            self.model = None
    
    def extract_embedding(self, image: np.ndarray, bbox: Tuple[int, int, int, int],
                         object_class: str, track_id: int, camera_id: str,
                         confidence: float, timestamp: datetime) -> AppearanceEmbedding:
        """
        Extract appearance embedding from cropped object image
        """
        x1, y1, x2, y2 = map(int, bbox)
        
        # Crop object from image
        crop = image[y1:y2, x1:x2]
        if crop.size == 0:
            logger.warning(f"Empty crop for track {track_id}")
            # Return zero embedding
            embedding = np.zeros(self.feature_dim if TORCH_AVAILABLE else 256)
        else:
            # Extract features
            if self.model is not None and TORCH_AVAILABLE:
                embedding = self._extract_deep_features(crop)
            else:
                embedding = self._extract_cv_features(crop)
        
        # Normalize embedding
        embedding = embedding / (np.linalg.norm(embedding) + 1e-8)
        
        appearance = AppearanceEmbedding(
            track_id=track_id,
            camera_id=camera_id,
            timestamp=timestamp,
            embedding=embedding,
            bbox=bbox,
            object_class=object_class,
            confidence=confidence,
            metadata={"crop_shape": crop.shape if crop.size > 0 else (0, 0, 0)}
        )
        
        # Cache embedding
        self._cache_embedding(appearance)
        
        return appearance
    
    def _extract_deep_features(self, crop: np.ndarray) -> np.ndarray:
        """Extract features using deep neural network"""
        try:
            # Convert BGR to RGB
            crop_rgb = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
            
            # Apply transformation
            input_tensor = self.transform(crop_rgb).unsqueeze(0).to(self.device)
            
            # Extract features
            with torch.no_grad():
                features = self.model(input_tensor)
                features = features.view(features.size(0), -1)
            
            return features.cpu().numpy().flatten()
        
        except Exception as e:
            logger.error(f"Deep feature extraction failed: {e}. Using CV fallback.")
            return self._extract_cv_features(crop)
    
    def _extract_cv_features(self, crop: np.ndarray) -> np.ndarray:
        """
        Extract traditional CV features as fallback
        Multi-modal: color histograms, HOG, LBP, texture features
        """
        if crop.size == 0:
            return np.zeros(256)
        
        features = []
        
        # Resize to standard size
        crop_resized = cv2.resize(crop, (64, 128))
        
        # 1. Color Histograms (HSV space) - 32 bins per channel = 96 dims
        hsv = cv2.cvtColor(crop_resized, cv2.COLOR_BGR2HSV)
        h_hist = cv2.calcHist([hsv], [0], None, [32], [0, 180]).flatten()
        s_hist = cv2.calcHist([hsv], [1], None, [32], [0, 256]).flatten()
        v_hist = cv2.calcHist([hsv], [2], None, [32], [0, 256]).flatten()
        features.extend([h_hist, s_hist, v_hist])
        
        # 2. Color Moments (mean, std, skew for each RGB channel) = 9 dims
        for i in range(3):
            channel = crop_resized[:, :, i].flatten()
            mean = np.mean(channel)
            std = np.std(channel)
            skew = np.mean(((channel - mean) / (std + 1e-8)) ** 3)
            features.extend([mean, std, skew])
        
        # 3. Edge Density (Canny edges) - 16 dims (grid-based)
        gray = cv2.cvtColor(crop_resized, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        h, w = edges.shape
        grid_h, grid_w = 4, 4
        for i in range(grid_h):
            for j in range(grid_w):
                y1, y2 = i * (h // grid_h), (i + 1) * (h // grid_h)
                x1, x2 = j * (w // grid_w), (j + 1) * (w // grid_w)
                density = np.sum(edges[y1:y2, x1:x2] > 0) / ((h // grid_h) * (w // grid_w))
                features.append(density)
        
        # 4. Local Binary Patterns (LBP) histogram - 64 dims
        lbp = self._compute_lbp(gray)
        lbp_hist = cv2.calcHist([lbp], [0], None, [64], [0, 256]).flatten()
        features.append(lbp_hist)
        
        # Concatenate all features
        feature_vector = np.concatenate([f.flatten() for f in features])
        
        return feature_vector
    
    def _compute_lbp(self, image: np.ndarray, radius: int = 1) -> np.ndarray:
        """Compute Local Binary Patterns"""
        lbp = np.zeros_like(image, dtype=np.uint8)
        h, w = image.shape
        
        for i in range(radius, h - radius):
            for j in range(radius, w - radius):
                center = image[i, j]
                code = 0
                code |= (image[i - radius, j] >= center) << 7
                code |= (image[i - radius, j + radius] >= center) << 6
                code |= (image[i, j + radius] >= center) << 5
                code |= (image[i + radius, j + radius] >= center) << 4
                code |= (image[i + radius, j] >= center) << 3
                code |= (image[i + radius, j - radius] >= center) << 2
                code |= (image[i, j - radius] >= center) << 1
                code |= (image[i - radius, j - radius] >= center) << 0
                lbp[i, j] = code
        
        return lbp
    
    def compute_similarity(self, emb1: AppearanceEmbedding, 
                          emb2: AppearanceEmbedding) -> float:
        """
        Compute cosine similarity between two embeddings
        Returns value in [0, 1] where 1 = identical
        """
        # Ensure embeddings are normalized
        v1 = emb1.embedding / (np.linalg.norm(emb1.embedding) + 1e-8)
        v2 = emb2.embedding / (np.linalg.norm(emb2.embedding) + 1e-8)
        
        cosine_sim = np.dot(v1, v2)
        
        # Clamp to [0, 1]
        return max(0.0, min(1.0, cosine_sim))
    
    def find_similar(self, query_embedding: AppearanceEmbedding,
                    candidates: List[AppearanceEmbedding],
                    threshold: float = 0.6,
                    top_k: int = 10) -> List[Tuple[AppearanceEmbedding, float]]:
        """
        Find most similar embeddings from candidate list
        Returns list of (embedding, similarity_score) tuples
        """
        similarities = []
        
        for candidate in candidates:
            # Skip same track
            if candidate.track_id == query_embedding.track_id:
                continue
            
            # Skip different object classes (optional optimization)
            if candidate.object_class != query_embedding.object_class:
                continue
            
            sim = self.compute_similarity(query_embedding, candidate)
            if sim >= threshold:
                similarities.append((candidate, sim))
        
        # Sort by similarity descending
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        return similarities[:top_k]
    
    def _cache_embedding(self, embedding: AppearanceEmbedding):
        """Cache embedding with LRU eviction"""
        key = embedding.track_id
        
        if len(self.feature_cache) >= self.cache_max_size:
            # Remove oldest entry
            oldest_key = next(iter(self.feature_cache))
            del self.feature_cache[oldest_key]
        
        self.feature_cache[key] = embedding
    
    def get_cached_embedding(self, track_id: int) -> Optional[AppearanceEmbedding]:
        """Get cached embedding for track"""
        return self.feature_cache.get(track_id)
    
    def clear_cache(self):
        """Clear feature cache"""
        self.feature_cache.clear()
        logger.info("Appearance embedding cache cleared")
    
    def get_statistics(self) -> Dict:
        """Get engine statistics"""
        return {
            "model_name": self.model_name,
            "feature_dim": self.feature_dim if TORCH_AVAILABLE else 256,
            "using_gpu": self.use_gpu,
            "torch_available": TORCH_AVAILABLE,
            "cache_size": len(self.feature_cache),
            "cache_max_size": self.cache_max_size
        }
