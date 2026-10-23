"""Stress index and fingerprint classification."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from math import sqrt


NORM_KEYS = ("norm_bioelectric", "norm_leaf_temp", "norm_color", "norm_el")


def stress_index(row: Mapping[str, float], weights: Mapping[str, float]) -> float:
    total_weight = 0.0
    weighted = 0.0
    for key in NORM_KEYS:
        weight = float(weights.get(key, weights.get(key.removeprefix("norm_"), 1.0)))
        if weight < 0:
            raise ValueError("Bobot tidak boleh negatif.")
        weighted += float(row[key]) * weight
        total_weight += weight
    if total_weight == 0:
        raise ValueError("Setidaknya satu bobot harus lebih besar dari nol.")
    return weighted / total_weight


def status(si: float, warning: float, high: float) -> str:
    if not 0 <= warning < high <= 1:
        raise ValueError("Ambang status harus berada pada 0 <= warning < high <= 1.")
    if si >= high:
        return "High Stress"
    if si >= warning:
        return "Warning"
    return "Normal"


def nearest(
    row: Mapping[str, float],
    centroids: Mapping[str, Mapping[str, float]],
    delta: float,
) -> dict[str, object]:
    if not centroids:
        raise ValueError("Centroid fingerprint belum tersedia.")
    distances = sorted(
        (
            (name, sqrt(sum((float(row[key]) - float(point[key])) ** 2 for key in NORM_KEYS)))
            for name, point in centroids.items()
        ),
        key=lambda item: item[1],
    )
    first, second = distances[0], distances[1] if len(distances) > 1 else (None, None)
    ambiguous = bool(second[1] and second[1] > 0 and (second[1] - first[1]) / second[1] < delta)
    return {
        "nearest_treatment": first[0],
        "nearest_distance": first[1],
        "second_treatment": second[0],
        "second_distance": second[1],
        "ambiguous": ambiguous,
    }


def apply_persistence(history: Iterable[str], candidate: str, n: int) -> str:
    if n < 1:
        raise ValueError("Jumlah observasi persistensi minimal satu.")
    values = list(history)
    if candidate == "Normal" or len(values) + 1 < n:
        return "Normal" if candidate != "High Stress" else candidate
    if len(values) + 1 >= n and all(value == candidate for value in (values + [candidate])[-n:]):
        return candidate
    return values[-1] if values else "Normal"
