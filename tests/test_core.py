import numpy as np
import pandas as pd
import pytest
from pathlib import Path

from core.classify import nearest, status, stress_index
from core.features import electrolyte_leakage
from core.image_analysis import analyze_leaf
from core.normalize import normalize
from core.stats import anova_tukey
from core.fingerprint import centroids, classify_fingerprint
from core.db import Database


def test_electrolyte_leakage():
    assert electrolyte_leakage(25, 100) == 25
    with pytest.raises(ValueError):
        electrolyte_leakage(101, 100)


def test_normalization_direction_and_clipping():
    frame = pd.DataFrame({"bioelectric_mv": [-1, 5, 20], "delta_t": [0, 5, 20],
                          "dgci": [0, .5, 1], "el_pct": [0, 50, 100]})
    cfg = {"parameters": {
        "bioelectric": {"min": 0, "max": 10, "direction": "up"},
        "leaf_temp": {"min": 0, "max": 10, "direction": "up"},
        "color": {"min": 0, "max": 1, "direction": "down"},
        "el": {"min": 0, "max": 100, "direction": "up"},
    }}
    result = normalize(frame, cfg)
    assert result.iloc[0]["norm_bioelectric"] == 0
    assert result.iloc[2]["norm_color"] == 0


def test_classification():
    row = {key: .5 for key in ("norm_bioelectric", "norm_leaf_temp", "norm_color", "norm_el")}
    assert stress_index(row, {}) == .5
    assert status(.2, .33, .66) == "Normal"
    assert status(.8, .33, .66) == "High Stress"
    result = nearest(row, {"panas": row, "kontrol": {key: 0 for key in row}}, .15)
    assert result["nearest_treatment"] == "panas"


def test_image_analysis():
    image = np.zeros((100, 100, 3), dtype=np.uint8)
    image[:, :, 1] = 180
    result = analyze_leaf(image, [25, 40, 40], [95, 255, 255],
                          min_leaf_pixels=500, max_mask_coverage=1.0)
    assert result["leaf_pixels"] == 10000
    assert result["mask"].shape == (100, 100)
    assert result["mask_coverage"] == 1.0


def test_anova_and_tukey():
    frame = pd.DataFrame({
        "treatment": ["kontrol"] * 3 + ["panas"] * 3,
        "value": [1.0, 1.1, 0.9, 3.0, 3.1, 2.9],
    })
    result = anova_tukey(frame, "value")
    assert result["p_value"] < 0.01
    assert result["tukey"] is not None


def test_fingerprint_uses_observations():
    frame = pd.DataFrame({
        "treatment": ["kontrol", "kontrol", "panas", "panas"],
        "norm_bio": [0.1, 0.2, 0.8, 0.9],
        "norm_temp": [0.1, 0.2, 0.8, 0.9],
        "norm_color": [0.1, 0.2, 0.8, 0.9],
        "norm_el": [0.1, 0.2, 0.8, 0.9],
    })
    references = centroids(frame)
    settings = {
        "parameters": {key: {"weight": 1} for key in ("bioelectric", "leaf_temp", "color", "el")},
        "thresholds": {"warning": 0.33, "high": 0.66, "ambiguity_delta": 0.15},
    }
    result = classify_fingerprint(
        {"norm_bioelectric": 0.85, "norm_leaf_temp": 0.85,
         "norm_color": 0.85, "norm_el": 0.85},
        settings, references,
    )
    assert result["nearest_treatment"] == "panas"
    assert result["status"] == "High Stress"


def test_database_observation_and_analysis_round_trip(tmp_path):
    db = Database(tmp_path / "test.db")
    db.migrate(Path("migrations/001_init.sql"))
    config_id = db.save_config("{}", "test")
    plant_id = db.add_plant("P-01", "kontrol")
    observation_id = db.add_observation(plant_id, "2026-01-01T08:00", {
        "bioelectric_mv": 10, "leaf_temp_c": 28, "air_temp_c": 27,
        "ec1_us": 50, "ec2_us": 100, "el_percent": 50, "wilt_score": 0,
        "day_after_treatment": 0,
    })
    db.save_analysis(observation_id, config_id, {
        "norm_bioelectric": 0.1, "norm_leaf_temp": 0.2,
        "norm_color": 0.3, "norm_el": 0.4,
        "stress_index": 0.25, "status": "Normal",
    })
    frame = db.list_observations()
    assert len(frame) == 1
    assert frame.iloc[0]["stress_index"] == 0.25
    assert len(db.fingerprint_data()) == 1


def test_database_csv_import(tmp_path):
    db = Database(tmp_path / "import.db")
    db.migrate(Path("migrations/001_init.sql"))
    db.add_plant("P-01", "kontrol")
    frame = pd.DataFrame([{
        "plant_code": "P-01", "observed_at": "2026-01-01T08:00",
        "bioelectric_mv": 10, "leaf_temp_c": 28, "air_temp_c": 27,
        "ec1_us": 50, "ec2_us": 100, "wilt_score": 0,
    }])
    imported, errors = db.import_observations(frame)
    assert imported == 1
    assert errors == []
    assert len(db.list_observations()) == 1
