import json

import streamlit as st

from app import CONFIG_PATH, get_db
from core.config import load_file

db = get_db()
settings = load_file(CONFIG_PATH)
st.header("Pengaturan")
st.caption("Perubahan konfigurasi disimpan sebagai versi baru agar hasil dapat direproduksi.")
warning = st.number_input("Ambang Warning", 0.0, 1.0, float(settings["thresholds"]["warning"]))
high = st.number_input("Ambang High Stress", 0.0, 1.0, float(settings["thresholds"]["high"]))
note = st.text_input("Catatan versi")
if st.button("Simpan konfigurasi"):
    if warning >= high:
        st.error("Ambang Warning harus lebih kecil daripada High Stress.")
    else:
        settings["thresholds"]["warning"] = warning
        settings["thresholds"]["high"] = high
        config_id = db.save_config(json.dumps(settings), note)
        st.success(f"Konfigurasi versi {config_id} tersimpan.")
active = db.active_config()
if active:
    st.json(json.loads(active["settings_json"]))
