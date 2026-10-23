import streamlit as st

from app import get_db
from core.classify import status, stress_index
from core.config import load_file
from core.normalize import normalize

db = get_db()
cfg = load_file(__import__("pathlib").Path("config/settings.yaml"))
st.header("Fingerprint dan Peringatan")
with st.form("fingerprint"):
    bio = st.number_input("Bioelektrik ternormalisasi", 0.0, 1.0, 0.0)
    temp = st.number_input("Suhu ternormalisasi", 0.0, 1.0, 0.0)
    color = st.number_input("Warna ternormalisasi", 0.0, 1.0, 0.0)
    el = st.number_input("EL ternormalisasi", 0.0, 1.0, 0.0)
    run = st.form_submit_button("Hitung status")
if run:
    row = {"norm_bioelectric": bio, "norm_leaf_temp": temp,
           "norm_color": color, "norm_el": el}
    weights = {f"norm_{key}": cfg["parameters"][key]["weight"] for key in cfg["parameters"]}
    si = stress_index(row, weights)
    result = status(si, cfg["thresholds"]["warning"], cfg["thresholds"]["high"])
    st.metric("Stress Index", f"{si:.3f}")
    st.warning(result) if result == "Warning" else st.error(result) if result == "High Stress" else st.success(result)
