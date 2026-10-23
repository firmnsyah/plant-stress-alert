"""Plant Stress Fingerprint Streamlit application."""

from pathlib import Path

import streamlit as st

from core.config import load_file
from core.db import Database

ROOT = Path(__file__).parent
DB_PATH = ROOT / "data" / "plant.db"
CONFIG_PATH = ROOT / "config" / "settings.yaml"
MIGRATION_PATH = ROOT / "migrations" / "001_init.sql"


@st.cache_resource
def get_db() -> Database:
    database = Database(DB_PATH)
    database.migrate(MIGRATION_PATH)
    if database.active_config() is None:
        database.save_config(__import__("json").dumps(load_file(CONFIG_PATH)), "Konfigurasi awal")
    return database


st.set_page_config(page_title="Plant Stress Fingerprint", page_icon="🌿", layout="wide")
db = get_db()
st.title("Plant Stress Fingerprint")
st.caption("Deteksi pola cekaman cabai berbasis pengukuran fisiologis dan foto daun.")
plants = db.list_plants()
observations = db.list_observations()
col1, col2, col3 = st.columns(3)
col1.metric("Tanaman", len(plants))
col2.metric("Observasi", len(observations))
col3.metric("Status Warning+", int((observations["status"].isin(["Warning", "High Stress"])).sum()) if "status" in observations else 0)
st.info("Gunakan halaman di panel kiri untuk menambah tanaman, menyimpan observasi, dan menjalankan analisis.")
