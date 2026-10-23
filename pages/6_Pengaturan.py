import json

import streamlit as st

from app import get_db, get_settings

db = get_db()
settings = get_settings(db)
st.header("Pengaturan")
st.caption("Perubahan konfigurasi disimpan sebagai versi baru agar hasil dapat direproduksi.")
warning = st.number_input("Ambang Warning", 0.0, 1.0, float(settings["thresholds"]["warning"]))
high = st.number_input("Ambang High Stress", 0.0, 1.0, float(settings["thresholds"]["high"]))
ambiguity = st.number_input("Ambang pola ambigu", 0.0, 1.0,
                            float(settings["thresholds"]["ambiguity_delta"]))
st.subheader("Bobot parameter")
weight_cols = st.columns(4)
weights = {}
for index, parameter in enumerate(("bioelectric", "leaf_temp", "color", "el")):
    weights[parameter] = weight_cols[index].number_input(
        parameter, min_value=0.0, value=float(settings["parameters"][parameter]["weight"]),
    )
note = st.text_input("Catatan versi")
if st.button("Simpan konfigurasi"):
    if warning >= high:
        st.error("Ambang Warning harus lebih kecil daripada High Stress.")
    elif sum(weights.values()) == 0:
        st.error("Setidaknya satu bobot harus lebih besar dari nol.")
    else:
        settings["thresholds"]["warning"] = warning
        settings["thresholds"]["high"] = high
        settings["thresholds"]["ambiguity_delta"] = ambiguity
        for parameter, weight in weights.items():
            settings["parameters"][parameter]["weight"] = weight
        config_id = db.save_config(json.dumps(settings), note)
        st.success(f"Konfigurasi versi {config_id} tersimpan.")
active = db.active_config()
if active:
    st.json(json.loads(active["settings_json"]))
