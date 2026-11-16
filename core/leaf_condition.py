"""Visual leaf condition screening from a single BGR photograph."""

from __future__ import annotations

import cv2
import numpy as np


CONDITIONS = ("Normal", "Stres Ringan", "Stres Sedang", "Stres Berat")


def _resize(image: np.ndarray, max_side: int = 1600) -> np.ndarray:
    height, width = image.shape[:2]
    scale = min(1.0, max_side / max(height, width))
    if scale == 1:
        return image
    return cv2.resize(image, (round(width * scale), round(height * scale)), cv2.INTER_AREA)


def _crop(image: np.ndarray, crop: tuple[float, float, float, float]) -> np.ndarray:
    left, top, right, bottom = crop
    if not (0 <= left < right <= 1 and 0 <= top < bottom <= 1):
        raise ValueError("Area crop harus berada dalam rentang 0 sampai 1.")
    height, width = image.shape[:2]
    result = image[round(top * height):round(bottom * height),
                   round(left * width):round(right * width)]
    if result.size == 0:
        raise ValueError("Area crop menghasilkan gambar kosong.")
    return result


def _segment_leaf(image: np.ndarray) -> np.ndarray:
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    color_seed = cv2.inRange(
        hsv,
        np.array([10, 30, 20], dtype=np.uint8),
        np.array([100, 255, 255], dtype=np.uint8),
    )
    color_seed = cv2.morphologyEx(color_seed, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    color_seed = cv2.morphologyEx(color_seed, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))

    border = max(3, min(image.shape[:2]) // 10)
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB).astype(np.int16)
    border_pixels = np.concatenate(
        (lab[:border].reshape(-1, 3), lab[-border:].reshape(-1, 3),
         lab[:, :border].reshape(-1, 3), lab[:, -border:].reshape(-1, 3)),
        axis=0,
    )
    border_color = np.median(border_pixels, axis=0)
    distance = np.sqrt(((lab - border_color) ** 2).sum(axis=2))
    color_seed = np.where((color_seed > 0) & (distance > 10), 255, 0).astype(np.uint8)

    grabcut_mask = np.full(color_seed.shape, cv2.GC_PR_BGD, dtype=np.uint8)
    grabcut_mask[color_seed > 0] = cv2.GC_PR_FGD
    grabcut_mask[:border, :] = cv2.GC_BGD
    grabcut_mask[-border:, :] = cv2.GC_BGD
    grabcut_mask[:, :border] = cv2.GC_BGD
    grabcut_mask[:, -border:] = cv2.GC_BGD
    definite = cv2.erode(color_seed, np.ones((9, 9), np.uint8))
    grabcut_mask[definite > 0] = cv2.GC_FGD

    background_model = np.zeros((1, 65), dtype=np.float64)
    foreground_model = np.zeros((1, 65), dtype=np.float64)
    try:
        cv2.grabCut(image, grabcut_mask, None, background_model, foreground_model, 5,
                    cv2.GC_INIT_WITH_MASK)
        mask = np.where(
            (grabcut_mask == cv2.GC_FGD) | (grabcut_mask == cv2.GC_PR_FGD),
            255, 0,
        ).astype(np.uint8)
    except cv2.error:
        mask = color_seed

    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))
    components, labels, stats, _ = cv2.connectedComponentsWithStats(mask, 8)
    if components > 1:
        largest = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
        mask = np.where(labels == largest, 255, 0).astype(np.uint8)
    return mask


def analyze_leaf_condition(
    image: np.ndarray,
    crop: tuple[float, float, float, float] = (0, 0, 1, 1),
    min_leaf_pixels: int = 500,
    max_mask_coverage: float = 0.85,
) -> dict[str, object]:
    """Return visual indicators and a four-level leaf condition."""
    if image is None or image.ndim != 3 or image.shape[2] != 3:
        raise ValueError("Citra harus berupa array BGR tiga kanal.")

    frame = _crop(_resize(image), crop)
    mask = _segment_leaf(frame)
    selected = mask > 0
    leaf_pixels = int(selected.sum())
    coverage = leaf_pixels / selected.size
    if leaf_pixels < min_leaf_pixels:
        raise ValueError("Daun tidak cukup terlihat. Gunakan foto lebih dekat.")
    if coverage > max_mask_coverage:
        raise ValueError(
            f"Latar ikut terseleksi ({coverage:.0%}). Crop satu daun atau gunakan latar polos."
        )

    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    hue, saturation, value = (channel[selected].astype(np.float32)
                              for channel in cv2.split(hsv))
    green = ((hue >= 35) & (hue <= 95) & (saturation >= 45) & (value >= 45))
    yellow_brown = ((hue >= 10) & (hue < 35) & (saturation >= 35) & (value >= 30))
    dark = value < 55
    green_ratio = float(green.mean())
    yellow_brown_ratio = float(yellow_brown.mean())
    dark_ratio = float(dark.mean())

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contour = max(contours, key=cv2.contourArea)
    area = float(cv2.contourArea(contour))
    perimeter = float(cv2.arcLength(contour, True))
    hull_area = float(cv2.contourArea(cv2.convexHull(contour)))
    solidity = area / hull_area if hull_area else 0.0
    circularity = 4 * np.pi * area / (perimeter * perimeter) if perimeter else 0.0
    curl_indicator = float(np.clip((1 - solidity) * 2.0 + (1 - circularity) * 0.15, 0, 1))

    color_score = min(1.0, yellow_brown_ratio * 1.4 + dark_ratio * 0.8 +
                      max(0.0, 0.55 - green_ratio))
    shape_score = curl_indicator if coverage >= 0.03 else 0.0
    stress_score = float(np.clip(color_score * 0.8 + shape_score * 0.2, 0, 1))
    if stress_score < 0.20:
        condition = "Normal"
    elif stress_score < 0.45:
        condition = "Stres Ringan"
    elif stress_score < 0.70:
        condition = "Stres Sedang"
    else:
        condition = "Stres Berat"

    return {
        "condition": condition,
        "stress_score": stress_score,
        "green_ratio": green_ratio,
        "yellow_brown_ratio": yellow_brown_ratio,
        "dark_ratio": dark_ratio,
        "leaf_pixels": leaf_pixels,
        "leaf_area_px": area,
        "leaf_area_ratio": coverage,
        "solidity": solidity,
        "circularity": circularity,
        "curl_indicator": curl_indicator,
        "mask_coverage": coverage,
        "mask": mask,
        "image": frame,
    }
