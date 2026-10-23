"""Configurable normalization to the [0, 1] stress direction."""

from __future__ import annotations

from collections.abc import Mapping

import pandas as pd


FEATURE_COLUMNS = {
    "bioelectric": "bioelectric_mv",
    "leaf_temp": "delta_t",
    "color": "dgci",
    "el": "el_pct",
}


def normalize(df: pd.DataFrame, cfg: Mapping) -> pd.DataFrame:
    result = pd.DataFrame(index=df.index)
    for parameter, source in FEATURE_COLUMNS.items():
        settings = cfg["parameters"][parameter]
        low, high = float(settings["min"]), float(settings["max"])
        if high <= low:
            raise ValueError(f"Batas normalisasi {parameter} tidak valid.")
        if source not in df:
            raise ValueError(f"Fitur {source} tidak ditemukan.")
        values = ((df[source].astype(float) - low) / (high - low)).clip(0.0, 1.0)
        if settings.get("direction") == "down":
            values = 1.0 - values
        result[f"norm_{parameter}"] = values
    return result
