"""SQLite persistence boundary for the application."""

from __future__ import annotations

import json
import shutil
import sqlite3
from threading import RLock
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd


class Database:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # Streamlit reruns pages in different threads while sharing cached resources.
        self.connection = sqlite3.connect(path, check_same_thread=False)
        self._lock = RLock()
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")

    def close(self) -> None:
        with self._lock:
            self.connection.close()

    def migrate(self, migration_path: Path) -> None:
        with self._lock:
            self.connection.executescript(migration_path.read_text(encoding="utf-8"))
            self.connection.commit()

    def save_config(self, settings_json: str, note: str = "") -> int:
        with self._lock:
            cursor = self.connection.execute(
                "INSERT INTO config_versions(created_at, note, settings_json) VALUES (?, ?, ?)",
                (datetime.now(UTC).isoformat(), note, settings_json),
            )
            self.connection.commit()
            return int(cursor.lastrowid)

    def active_config(self) -> sqlite3.Row | None:
        with self._lock:
            return self.connection.execute(
                "SELECT * FROM config_versions ORDER BY id DESC LIMIT 1"
            ).fetchone()

    def add_plant(self, code: str, treatment: str, **fields: Any) -> int:
        with self._lock:
            cursor = self.connection.execute(
                """INSERT INTO plants(code, treatment, planted_at, stress_started_at, first_wilt_at, notes)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (code, treatment, fields.get("planted_at"), fields.get("stress_started_at"),
                 fields.get("first_wilt_at"), fields.get("notes")),
            )
            self.connection.commit()
            return int(cursor.lastrowid)

    def list_plants(self) -> pd.DataFrame:
        with self._lock:
            return pd.read_sql_query("SELECT * FROM plants ORDER BY code", self.connection)

    def add_observation(self, plant_id: int, observed_at: str, values: dict[str, Any]) -> int:
        with self._lock:
            cursor = self.connection.execute(
                """INSERT INTO observations(
                     plant_id, observed_at, day_after_treatment, bioelectric_mv, leaf_temp_c,
                     air_temp_c, ec1_us, ec2_us, el_percent, wilt_score, notes)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (plant_id, observed_at, values.get("day_after_treatment"), values.get("bioelectric_mv"),
                 values["leaf_temp_c"], values["air_temp_c"], values["ec1_us"], values["ec2_us"],
                 values["el_percent"], values["wilt_score"], values.get("notes")),
            )
            self.connection.commit()
            return int(cursor.lastrowid)

    def add_image(self, observation_id: int, image: dict[str, Any], file_path: str,
                  hsv_low: list[int], hsv_high: list[int], has_gray_card: bool = False) -> int:
        with self._lock:
            cursor = self.connection.execute(
                """INSERT INTO leaf_images(
                     observation_id, file_path, r, g, b, h, s, v, dgci, exg, leaf_pixels,
                     hsv_low, hsv_high, has_gray_card)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (observation_id, file_path, image["r"], image["g"], image["b"], image["h"],
                 image["s"], image["v"], image["dgci"], image["exg"], image["leaf_pixels"],
                 json.dumps(hsv_low), json.dumps(hsv_high), int(has_gray_card)),
            )
            self.connection.commit()
            return int(cursor.lastrowid)

    def save_analysis(self, observation_id: int, config_id: int, result: dict[str, Any]) -> int:
        with self._lock:
            cursor = self.connection.execute(
                """INSERT INTO analysis_results(
                     observation_id, config_id, norm_bio, norm_temp, norm_color, norm_el,
                     stress_index, status, nearest_treatment, nearest_distance,
                     second_treatment, second_distance, ambiguous)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (observation_id, config_id, result["norm_bioelectric"], result["norm_leaf_temp"],
                 result["norm_color"], result["norm_el"], result["stress_index"], result["status"],
                 result.get("nearest_treatment"), result.get("nearest_distance"),
                 result.get("second_treatment"), result.get("second_distance"),
                 int(result.get("ambiguous", False))),
            )
            self.connection.commit()
            return int(cursor.lastrowid)

    def list_observations(self, treatment: str | None = None) -> pd.DataFrame:
        query = """SELECT o.*, p.code, p.treatment, ar.stress_index, ar.status
                   FROM observations o JOIN plants p ON p.id=o.plant_id
                   LEFT JOIN analysis_results ar ON ar.observation_id=o.id
                   WHERE o.deleted_at IS NULL"""
        params: tuple[Any, ...] = ()
        if treatment:
            query += " AND p.treatment = ?"
            params = (treatment,)
        query += " ORDER BY o.observed_at"
        with self._lock:
            return pd.read_sql_query(query, self.connection, params=params)

    def export(self, output: Path, treatment: str | None = None) -> Path:
        frame = self.list_observations(treatment)
        if output.suffix.lower() == ".xlsx":
            frame.to_excel(output, index=False)
        else:
            frame.to_csv(output, index=False)
        return output

    def backup(self, destination: Path) -> Path:
        with self._lock:
            self.connection.commit()
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(self.path, destination)
            return destination
