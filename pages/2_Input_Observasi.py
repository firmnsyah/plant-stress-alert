from datetime import datetime

import cv2
import numpy as np
import streamlit as st
from pathlib import Path

from app import CONFIG_PATH, get_db
from core.config import load_file
from core.features import electrolyte_leakage
from core.image_analysis import analyze_leaf

db = get_db()
settings = load_file(CONFIG_PATH)
plants = db.list_plants()
st.header("Input Observasi")
if plants.empty:
    st.warning("Tambahkan tanaman terlebih dahulu.")
    st.stop()

with st.form("observation"):
    selected = st.selectbox("Tanaman", plants["code"].tolist())
    observed_at = st.text_input("Tanggal dan jam", datetime.now().replace(second=0, microsecond=0).isoformat(timespec="minutes"))
    bio = st.number_input("Bioelektrik (mV)", value=0.0)
    leaf_temp = st.number_input("Suhu daun (°C)", min_value=10.0, max_value=60.0, value=28.0)
    air_temp = st.number_input("Suhu udara (°C)", min_value=10.0, max_value=60.0, value=27.0)
    ec1 = st.number_input("EC1 (µS/cm)", min_value=0.01, value=100.0)
    ec2 = st.number_input("EC2 (µS/cm)", min_value=0.01, value=200.0)
    wilt_score = st.number_input("Skor layu (0-4)", min_value=0, max_value=4, step=1)
    image_file = st.file_uploader("Foto daun", type=["jpg", "jpeg", "png"])
    notes = st.text_area("Catatan")
    st.caption(f"EL otomatis: {electrolyte_leakage(ec1, ec2):.2f}%")
    submitted = st.form_submit_button("Simpan observasi")

if submitted:
    if image_file is None:
        st.error("Foto daun wajib diunggah.")
        st.stop()
    try:
        raw = np.frombuffer(image_file.getvalue(), dtype=np.uint8)
        image = cv2.imdecode(raw, cv2.IMREAD_COLOR)
        image_stats = analyze_leaf(
            image, settings["image"]["hsv_low"], settings["image"]["hsv_high"],
            settings["image"]["min_leaf_pixels"], settings["image"]["max_side_px"],
        )
        plant_id = int(plants.loc[plants["code"] == selected, "id"].iloc[0])
        observation_id = db.add_observation(plant_id, observed_at, {
            "bioelectric_mv": bio, "leaf_temp_c": leaf_temp, "air_temp_c": air_temp,
            "ec1_us": ec1, "ec2_us": ec2, "el_percent": electrolyte_leakage(ec1, ec2),
            "wilt_score": wilt_score, "notes": notes,
        })
        image_dir = Path("data") / "images"
        image_dir.mkdir(parents=True, exist_ok=True)
        image_path = image_dir / f"observation_{observation_id}_{Path(image_file.name).name}"
        mask_path = image_path.with_name(f"{image_path.stem}_mask.png")
        if not cv2.imwrite(str(image_path), image_stats["image"]) or not cv2.imwrite(
            str(mask_path), image_stats["mask"]
        ):
            raise OSError("Foto atau mask gagal ditulis ke penyimpanan lokal.")
        db.add_image(observation_id, image_stats, str(image_path),
                     settings["image"]["hsv_low"], settings["image"]["hsv_high"])
        st.success(f"Observasi tersimpan dengan ID {observation_id}.")
        st.image(cv2.cvtColor(image_stats["image"], cv2.COLOR_BGR2RGB), caption="Foto daun")
        st.image(image_stats["mask"], caption="Mask segmentasi")
    except Exception as exc:
        st.error(f"Observasi gagal disimpan: {exc}")
