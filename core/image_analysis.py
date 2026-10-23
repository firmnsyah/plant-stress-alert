"""OpenCV-based leaf segmentation and color extraction."""

from __future__ import annotations

from collections.abc import Sequence

import cv2
import numpy as np


def _resize(image: np.ndarray, max_side_px: int) -> np.ndarray:
    height, width = image.shape[:2]
    scale = min(1.0, max_side_px / max(height, width))
    if scale == 1.0:
        return image
    return cv2.resize(image, (round(width * scale), round(height * scale)), interpolation=cv2.INTER_AREA)


def analyze_leaf(
    img: np.ndarray,
    hsv_low: Sequence[int],
    hsv_high: Sequence[int],
    min_leaf_pixels: int = 500,
    max_side_px: int = 1600,
    crop: tuple[float, float, float, float] | None = None,
    keep_largest_component: bool = True,
    max_mask_coverage: float = 0.85,
) -> dict[str, object]:
    if img is None or img.ndim != 3 or img.shape[2] != 3:
        raise ValueError("Citra harus berupa array BGR tiga kanal.")
    image = _resize(img, max_side_px)
    if crop is not None:
        left, top, right, bottom = crop
        if not (0 <= left < right <= 1 and 0 <= top < bottom <= 1):
            raise ValueError("Area crop harus berada dalam rentang 0 sampai 1.")
        height, width = image.shape[:2]
        image = image[round(top * height):round(bottom * height),
                      round(left * width):round(right * width)]
        if image.size == 0:
            raise ValueError("Area crop menghasilkan citra kosong.")
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, np.array(hsv_low, dtype=np.uint8), np.array(hsv_high, dtype=np.uint8))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    if keep_largest_component:
        components, labels, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
        if components > 1:
            largest = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
            mask = np.where(labels == largest, 255, 0).astype(np.uint8)
    selected = mask > 0
    leaf_pixels = int(selected.sum())
    if leaf_pixels < min_leaf_pixels:
        raise ValueError(f"Segmentasi hanya menemukan {leaf_pixels} piksel daun; minimal {min_leaf_pixels}.")
    coverage = leaf_pixels / selected.size
    if coverage > max_mask_coverage:
        raise ValueError(
            f"Mask menutupi {coverage:.0%} citra; latar kemungkinan ikut terseleksi. "
            "Crop area daun atau sesuaikan ambang HSV."
        )
    bgr = image[selected].astype(np.float64)
    hsv_values = hsv[selected].astype(np.float64)
    blue, green, red = bgr.mean(axis=0)
    hue, saturation, value = hsv_values.mean(axis=0)
    saturation /= 255.0
    value /= 255.0
    hue_degrees = hue * 2.0
    dgci = ((hue_degrees - 60.0) / 60.0 + (1.0 - saturation) + (1.0 - value)) / 3.0
    denominator = red + green + blue
    exg = (2.0 * green - red - blue) / denominator if denominator else 0.0
    return {
        "r": float(red), "g": float(green), "b": float(blue),
        "h": float(hue_degrees), "s": float(saturation), "v": float(value),
        "dgci": float(dgci), "exg": float(exg), "leaf_pixels": leaf_pixels,
        "mask_coverage": float(coverage),
        "mask": mask,
        "image": image,
    }


def correct_exposure(img: np.ndarray, card_roi: tuple[int, int, int, int]) -> np.ndarray:
    x, y, width, height = card_roi
    if width <= 0 or height <= 0:
        raise ValueError("Area kartu abu-abu tidak valid.")
    roi = img[y:y + height, x:x + width]
    if roi.size == 0:
        raise ValueError("Area kartu abu-abu berada di luar citra.")
    mean = roi.mean(axis=(0, 1))
    if np.any(mean <= 1):
        raise ValueError("Nilai kartu abu-abu tidak dapat digunakan untuk koreksi.")
    scale = 128.0 / mean
    return np.clip(img.astype(np.float32) * scale, 0, 255).astype(np.uint8)
