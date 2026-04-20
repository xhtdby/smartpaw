"""Dog detection service using YOLOv10-nano (COCO pre-trained).

Validates that a dog is present in the uploaded image before running
further analysis. Returns bounding box + confidence for the best detection.
"""

import io
import logging
from PIL import Image

logger = logging.getLogger(__name__)

# Lazy-loaded model singleton
_model = None


def _get_model():
    global _model
    if _model is None:
        from ultralytics import YOLO

        logger.info("Loading YOLOv8n model (COCO pre-trained)...")
        _model = YOLO("yolov8n.pt")
    return _model


# COCO class index for "dog"
DOG_CLASS_ID = 16


def detect_dog(image_bytes: bytes, confidence_threshold: float = 0.4) -> dict | None:
    """Detect a dog in the image.

    Returns dict with keys: confidence, bbox (xyxy list) if a dog is found,
    otherwise returns None.
    """
    model = _get_model()
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")

    results = model.predict(source=image, conf=confidence_threshold, verbose=False)

    best_dog = None
    best_conf = 0.0

    for result in results:
        for box in result.boxes:
            cls_id = int(box.cls[0])
            conf = float(box.conf[0])
            if cls_id == DOG_CLASS_ID and conf > best_conf:
                best_conf = conf
                best_dog = {
                    "confidence": round(conf, 3),
                    "bbox": [round(c, 1) for c in box.xyxy[0].tolist()],
                }

    if best_dog:
        logger.info(f"Dog detected with confidence {best_dog['confidence']}")
    else:
        logger.info("No dog detected in the image.")

    return best_dog
