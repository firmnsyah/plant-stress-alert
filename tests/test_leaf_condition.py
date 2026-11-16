import numpy as np
import pytest

from core.leaf_condition import analyze_leaf_condition


def test_green_leaf_is_normal():
    image = np.zeros((200, 200, 3), dtype=np.uint8)
    image[30:170, 30:170] = (30, 170, 30)
    result = analyze_leaf_condition(image)
    assert result["condition"] == "Normal"
    assert result["green_ratio"] > 0.8


def test_yellow_leaf_is_not_normal():
    image = np.zeros((200, 200, 3), dtype=np.uint8)
    image[30:170, 30:170] = (20, 180, 190)
    result = analyze_leaf_condition(image)
    assert result["condition"] in {"Stres Ringan", "Stres Sedang", "Stres Berat"}
    assert result["yellow_brown_ratio"] > 0.5


def test_background_is_rejected():
    image = np.full((100, 100, 3), (30, 170, 30), dtype=np.uint8)
    with pytest.raises(ValueError):
        analyze_leaf_condition(image)
