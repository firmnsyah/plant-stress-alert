"""Versioned YAML configuration helpers."""

from __future__ import annotations

import copy
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml


def load_file(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as stream:
        settings = yaml.safe_load(stream) or {}
    return settings


def dump_json(settings: dict[str, Any]) -> str:
    return json.dumps(settings, ensure_ascii=False, sort_keys=True)


def save_new(settings: dict[str, Any], note: str, db: Any) -> int:
    snapshot = copy.deepcopy(settings)
    snapshot["_saved_at"] = datetime.now(UTC).isoformat()
    return db.save_config(dump_json(snapshot), note)
