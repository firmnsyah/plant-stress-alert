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
            if cursor.lastrowid is None:
                raise RuntimeError("ID konfigurasi tidak tersedia setelah penyimpanan.")
            return int(cursor.lastrowid)

    def active_config(self) -> sqlite3.Row | None:
        with self._lock:
            return self.connection.execute(
                "SELECT * FROM config_versions ORDER BY id DESC LIMIT 1"
            ).fetchone()

    def active_config_json(self) -> dict[str, Any] | None:
        row = self.active_config()
        return json.loads(row["settings_json"]) if row else None

    def add_plant(self, code: str, treatment: str, **fields: Any) -> int:
        with self._lock:
            cursor = self.connection.execute(
                """INSERT INTO plants(code, treatment, planted_at, stress_started_at, first_wilt_at, notes)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (code, treatment, fields.get("planted_at"), fields.get("stress_started_at"),
                 fields.get("first_wilt_at"), fields.get("notes")),
            )
            self.connection.commit()
            if cursor.lastrowid is None:
                raise RuntimeError("ID tanaman tidak tersedia setelah penyimpanan.")
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
            if cursor.lastrowid is None:
                raise RuntimeError("ID observasi tidak tersedia setelah penyimpanan.")
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
            if cursor.lastrowid is None:
                raise RuntimeError("ID foto tidak tersedia setelah penyimpanan.")
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
            if cursor.lastrowid is None:
                raise RuntimeError("ID analisis tidak tersedia setelah penyimpanan.")
            return int(cursor.lastrowid)

    def list_observations(self, treatment: str | None = None) -> pd.DataFrame:
        query = """SELECT o.*, p.code, p.treatment, li.file_path, li.r, li.g, li.b,
                          li.h, li.s, li.v, li.dgci, li.exg, li.leaf_pixels,
                          ar.stress_index, ar.status, ar.norm_bio, ar.norm_temp,
                          ar.norm_color, ar.norm_el, ar.nearest_treatment,
                          ar.nearest_distance, ar.second_treatment, ar.second_distance,
                          ar.ambiguous
                   FROM observations o JOIN plants p ON p.id=o.plant_id
                   LEFT JOIN leaf_images li ON li.observation_id=o.id
                   LEFT JOIN analysis_results ar ON ar.id = (
                     SELECT latest.id FROM analysis_results latest
                     WHERE latest.observation_id=o.id ORDER BY latest.id DESC LIMIT 1
                   )
                   WHERE o.deleted_at IS NULL"""
        params: tuple[Any, ...] = ()
        if treatment:
            query += " AND p.treatment = ?"
            params = (treatment,)
        query += " ORDER BY o.observed_at"
        with self._lock:
            return pd.read_sql_query(query, self.connection, params=params)

    def fingerprint_data(self, treatment: str | None = None) -> pd.DataFrame:
        frame = self.list_observations(treatment)
        columns = ["code", "treatment", "observed_at", "norm_bio", "norm_temp",
                   "norm_color", "norm_el", "stress_index", "status"]
        available = [column for column in columns if column in frame.columns]
        return frame[available].dropna(subset=["norm_bio", "norm_temp", "norm_color", "norm_el"])

    def soft_delete_observation(self, observation_id: int) -> None:
        with self._lock:
            self.connection.execute(
                "UPDATE observations SET deleted_at=? WHERE id=?",
                (datetime.now(UTC).isoformat(), observation_id),
            )
            self.connection.commit()

    def import_observations(self, frame: pd.DataFrame) -> tuple[int, list[str]]:
        required = {
            "plant_code", "observed_at", "bioelectric_mv", "leaf_temp_c",
            "air_temp_c", "ec1_us", "ec2_us", "wilt_score",
        }
        missing = sorted(required - set(frame.columns))
        if missing:
            raise ValueError(f"Kolom CSV wajib belum ada: {', '.join(missing)}.")
        imported = 0
        errors: list[str] = []
        plants = {
            str(row["code"]): int(row["id"])
            for _, row in self.list_plants().iterrows()
        }
        for index, row in frame.iterrows():
            try:
                code = str(row["plant_code"])
                if code not in plants:
                    raise ValueError(f"tanaman {code} belum terdaftar")
                ec1, ec2 = float(row["ec1_us"]), float(row["ec2_us"])
                self.add_observation(plants[code], str(row["observed_at"]), {
                    "bioelectric_mv": float(row["bioelectric_mv"]),
                    "leaf_temp_c": float(row["leaf_temp_c"]),
                    "air_temp_c": float(row["air_temp_c"]),
                    "ec1_us": ec1,
                    "ec2_us": ec2,
                    "el_percent": ec1 / ec2 * 100,
                    "wilt_score": int(row["wilt_score"]),
                    "day_after_treatment": int(row.get("day_after_treatment", 0)),
                    "notes": str(row.get("notes", "")),
                })
                imported += 1
            except (TypeError, ValueError, sqlite3.IntegrityError) as exc:
                errors.append(f"baris {index + 2}: {exc}")
        return imported, errors

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
