from datetime import datetime
from pathlib import Path

import cv2
import numpy as np
import pandas as pd
import streamlit as st

from app import get_db, get_settings
from core.classify import status, stress_index
from core.features import compute_features, electrolyte_leakage
from core.image_analysis import analyze_leaf
from core.normalize import normalize

db = get_db()
settings = get_settings(db)
plants = db.list_plants()
st.header("Input Observasi")
if plants.empty:
    st.warning("Tambahkan tanaman terlebih dahulu.")
    st.stop()

image_file = st.file_uploader("Foto daun", type=["jpg", "jpeg", "png"])
crop = (0.0, 0.0, 1.0, 1.0)
if image_file is not None:
    raw_preview = np.frombuffer(image_file.getvalue(), dtype=np.uint8)
    preview = cv2.imdecode(raw_preview, cv2.IMREAD_COLOR)
    if preview is None:
        st.error("File gambar tidak dapat dibaca.")
        st.stop()
    st.image(cv2.cvtColor(preview, cv2.COLOR_BGR2RGB), caption="Pratinjau foto", width="stretch")
    st.caption("Jika latar ikut terseleksi, crop area yang hanya memuat daun target.")
    crop_cols = st.columns(4)
    left = crop_cols[0].slider("Crop kiri (%)", 0, 80, 0, 1)
    top = crop_cols[1].slider("Crop atas (%)", 0, 80, 0, 1)
    right = crop_cols[2].slider("Crop kanan (%)", 20, 100, 100, 1)
    bottom = crop_cols[3].slider("Crop bawah (%)", 20, 100, 100, 1)
    crop = (left / 100, top / 100, right / 100, bottom / 100)
    if left >= right or top >= bottom:
        st.error("Batas crop tidak valid.")
    else:
        try:
            preview_stats = analyze_leaf(
                preview, settings["image"]["hsv_low"], settings["image"]["hsv_high"],
                settings["image"]["min_leaf_pixels"], settings["image"]["max_side_px"],
                crop=crop, max_mask_coverage=settings["image"]["max_mask_coverage"],
            )
            st.image(preview_stats["mask"], caption="Pratinjau mask daun", width="stretch")
            st.caption(
                f"Area terseleksi: {preview_stats['mask_coverage']:.1%}. "
                "Target yang baik biasanya tidak memenuhi hampir seluruh frame."
            )
        except ValueError as exc:
            st.warning(str(exc))

with st.form("observation"):
    selected = st.selectbox("Tanaman", plants["code"].tolist())
    observed_at = st.text_input("Tanggal dan jam", datetime.now().replace(second=0, microsecond=0).isoformat(timespec="minutes"))
    day_after_treatment = st.number_input("Hari setelah mulai cekaman", min_value=0, step=1, value=0)
    bio = st.number_input("Bioelektrik (mV)", value=0.0)
    leaf_temp = st.number_input("Suhu daun (°C)", min_value=10.0, max_value=60.0, value=28.0)
    air_temp = st.number_input("Suhu udara (°C)", min_value=10.0, max_value=60.0, value=27.0)
    ec1 = st.number_input("EC1 (µS/cm)", min_value=0.01, value=100.0)
    ec2 = st.number_input("EC2 (µS/cm)", min_value=0.01, value=200.0)
    wilt_score = st.number_input("Skor layu (0-4)", min_value=0, max_value=4, step=1)
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
            settings["image"]["min_leaf_pixels"], settings["image"]["max_side_px"], crop=crop,
            max_mask_coverage=settings["image"]["max_mask_coverage"],
        )
        plant_id = int(plants.loc[plants["code"] == selected, "id"].iloc[0])
        observation_id = db.add_observation(plant_id, observed_at, {
            "bioelectric_mv": bio, "leaf_temp_c": leaf_temp, "air_temp_c": air_temp,
            "ec1_us": ec1, "ec2_us": ec2, "el_percent": electrolyte_leakage(ec1, ec2),
            "wilt_score": wilt_score, "day_after_treatment": day_after_treatment, "notes": notes,
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
        active_config = db.active_config()
        analysis_result = None
        if active_config is not None:
            features = compute_features(
                {"bioelectric_mv": bio, "leaf_temp_c": leaf_temp, "air_temp_c": air_temp,
                 "ec1_us": ec1, "ec2_us": ec2},
                image_stats,
            )
            normalized = normalize(pd.DataFrame([features]), settings).iloc[0].to_dict()
            weights = {f"norm_{key}": settings["parameters"][key]["weight"]
                       for key in settings["parameters"]}
            si = stress_index(normalized, weights)
            result = {**normalized, "stress_index": si,
                      "status": status(si, settings["thresholds"]["warning"],
                                       settings["thresholds"]["high"])}
            db.save_analysis(observation_id, int(active_config["id"]), result)
            analysis_result = {**features, **result}
        st.success(f"Observasi tersimpan dengan ID {observation_id}.")
        if analysis_result is not None:
            st.subheader("Hasil analisis observasi")
            feature_cols = st.columns(3)
            feature_cols[0].metric("EL", f"{analysis_result['el_pct']:.2f}%")
            feature_cols[1].metric("Delta suhu", f"{analysis_result['delta_t']:.2f} °C")
            feature_cols[2].metric("DGCI", f"{analysis_result['dgci']:.3f}")

            st.write("Nilai ternormalisasi")
            normalized_cols = st.columns(4)
            normalized_cols[0].metric("Bioelektrik", f"{analysis_result['norm_bioelectric']:.3f}")
            normalized_cols[1].metric("Suhu", f"{analysis_result['norm_leaf_temp']:.3f}")
            normalized_cols[2].metric("Warna", f"{analysis_result['norm_color']:.3f}")
            normalized_cols[3].metric("EL", f"{analysis_result['norm_el']:.3f}")

            st.metric("Stress Index", f"{analysis_result['stress_index']:.3f}")
            result_status = analysis_result["status"]
            if result_status == "High Stress":
                st.error(f"Status: {result_status}")
            elif result_status == "Warning":
                st.warning(f"Status: {result_status}")
            else:
                st.success(f"Status: {result_status}")
        st.image(cv2.cvtColor(image_stats["image"], cv2.COLOR_BGR2RGB), caption="Foto daun")
        st.image(image_stats["mask"], caption="Mask segmentasi")
    except Exception as exc:
        st.error(f"Observasi gagal disimpan: {exc}")
