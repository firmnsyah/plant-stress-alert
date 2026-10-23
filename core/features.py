"""Feature calculations and input validation."""

from __future__ import annotations

from collections.abc import Mapping
from math import isfinite


def electrolyte_leakage(ec1_us: float, ec2_us: float) -> float:
    if ec1_us <= 0 or ec2_us <= 0:
        raise ValueError("EC1 dan EC2 harus lebih besar dari nol.")
    if ec1_us > ec2_us:
        raise ValueError("EC1 tidak boleh lebih besar daripada EC2.")
    return ec1_us / ec2_us * 100.0


def delta_temperature(leaf_temp_c: float, air_temp_c: float) -> float:
    return float(leaf_temp_c) - float(air_temp_c)


def compute_features(
    observation: Mapping[str, float],
    image_stats: Mapping[str, float],
) -> dict[str, float]:
    required = ("leaf_temp_c", "air_temp_c", "ec1_us", "ec2_us")
    missing = [key for key in required if key not in observation]
    if missing:
        raise ValueError(f"Kolom observasi tidak lengkap: {', '.join(missing)}.")
    dgci = float(image_stats["dgci"])
    if not isfinite(dgci):
        raise ValueError("DGCI harus berupa angka terbatas.")
    return {
        "el_pct": electrolyte_leakage(float(observation["ec1_us"]), float(observation["ec2_us"])),
        "delta_t": delta_temperature(float(observation["leaf_temp_c"]), float(observation["air_temp_c"])),
        "dgci": dgci,
        "bioelectric_mv": float(observation.get("bioelectric_mv", 0.0)),
    }
