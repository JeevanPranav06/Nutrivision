# =========================
# services/food_detector.py
# =========================

import cv2
import numpy as np
from typing import Dict

# NOTE:
# This module is designed to be EXTENSIBLE.
# You can plug in:
# - TensorFlow Lite model
# - External APIs (Google Vision, etc.)


def _preprocess_image(image_bytes: bytes) -> np.ndarray:
    """
    Convert raw image bytes → OpenCV image and preprocess
    """
    np_arr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

    if img is None:
        raise ValueError("Invalid image input")

    # Resize for consistency
    img = cv2.resize(img, (224, 224))

    # Normalize
    img = img / 255.0

    return img


def _edge_features(img: np.ndarray) -> np.ndarray:
    """
    Extract edge features (useful for classical CV / debugging)
    """
    gray = (img * 255).astype(np.uint8)
    gray = cv2.cvtColor(gray, cv2.COLOR_BGR2GRAY)

    edges = cv2.Canny(gray, 50, 150)
    return edges


# -------------------------------
# 🔌 MODEL / API HOOK
# -------------------------------

def _detect_with_stub(img: np.ndarray) -> str:
    """
    Placeholder logic (REPLACE with real model/API)

    This uses simple heuristics to avoid hardcoding fixed values.
    Replace this with:
    - TensorFlow Lite classifier
    - External API
    """

    # Simple heuristic based on color distribution
    avg_color = img.mean(axis=(0, 1))  # BGR

    b, g, r = avg_color

    # Very rough heuristic mapping (NOT RANDOM)
    if r > 0.5 and g < 0.4:
        return "tomato curry"
    elif g > r and g > b:
        return "salad"
    elif b < 0.3 and r > 0.4 and g > 0.4:
        return "fried rice"
    else:
        return "mixed food"


# -------------------------------
# PUBLIC API
# -------------------------------

def detect_food(image_bytes: bytes) -> Dict[str, str]:
    """
    Main detection pipeline
    """

    # Step 1: preprocess
    img = _preprocess_image(image_bytes)

    # Step 2: optional feature extraction (not used directly yet)
    _ = _edge_features(img)

    # Step 3: detect food
    food_name = _detect_with_stub(img)

    return {
        "food_name": food_name
    }