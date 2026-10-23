"""Fingerprint construction from labelled observation results."""

from __future__ import annotations

from collections.abc import Mapping

import pandas as pd

from core.classify import NORM_KEYS, nearest, status, stress_index


def centroids(frame: pd.DataFrame) -> dict[str, dict[str, float]]:
    required = ["treatment", "norm_bio", "norm_temp", "norm_color", "norm_el"]
    missing = [column for column in required if column not in frame]
    if missing:
        raise ValueError(f"Data fingerprint tidak lengkap: {', '.join(missing)}.")
    grouped = frame.dropna(subset=required).groupby("treatment")
    return {
        str(treatment): {
            "norm_bioelectric": float(values["norm_bio"].mean()),
            "norm_leaf_temp": float(values["norm_temp"].mean()),
            "norm_color": float(values["norm_color"].mean()),
            "norm_el": float(values["norm_el"].mean()),
        }
        for treatment, values in grouped
    }


def classify_fingerprint(
    row: Mapping[str, float],
    settings: Mapping,
    reference_centroids: Mapping[str, Mapping[str, float]],
) -> dict[str, object]:
    weights = {
        f"norm_{key}": settings["parameters"][key]["weight"]
        for key in settings["parameters"]
    }
    result: dict[str, object] = {
        "stress_index": stress_index(row, weights),
    }
    result["status"] = status(
        float(result["stress_index"]),
        settings["thresholds"]["warning"],
        settings["thresholds"]["high"],
    )
    if reference_centroids:
        result.update(nearest(row, reference_centroids, settings["thresholds"]["ambiguity_delta"]))
    return result
