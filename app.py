"""Photo-only Plant Stress Alert application."""

import cv2
import numpy as np
import streamlit as st

from core.leaf_condition import analyze_leaf_condition


st.set_page_config(page_title="Plant Stress Alert", page_icon="🌿", layout="centered")
st.title("Plant Stress Alert")
st.caption("Skrining kondisi daun berdasarkan satu foto.")
st.info(
    "Upload satu foto daun. Sistem menilai warna, luas area daun, dan indikator "
    "bentuk tidak normal seperti kemungkinan menggulung."
)

uploaded = st.file_uploader("Upload foto daun", type=["jpg", "jpeg", "png"])
if uploaded is None:
    st.stop()

image = cv2.imdecode(np.frombuffer(uploaded.getvalue(), dtype=np.uint8), cv2.IMREAD_COLOR)
if image is None:
    st.error("File tidak dapat dibaca sebagai gambar.")
    st.stop()

st.image(cv2.cvtColor(image, cv2.COLOR_BGR2RGB), caption="Foto daun", width="stretch")
st.caption("Gunakan crop jika background ikut terseleksi.")
columns = st.columns(4)
left = columns[0].slider("Kiri (%)", 0, 80, 0)
top = columns[1].slider("Atas (%)", 0, 80, 0)
right = columns[2].slider("Kanan (%)", 20, 100, 100)
bottom = columns[3].slider("Bawah (%)", 20, 100, 100)

if left >= right or top >= bottom:
    st.error("Batas crop tidak valid.")
    st.stop()

try:
    result = analyze_leaf_condition(
        image, crop=(left / 100, top / 100, right / 100, bottom / 100)
    )
except ValueError as exc:
    st.error(str(exc))
    st.stop()

st.image(result["mask"], caption="Mask daun", width="stretch")
st.subheader(f"Kondisi: {result['condition']}")
st.metric("Skor kondisi", f"{result['stress_score'] * 100:.0f}/100")

metrics = st.columns(3)
metrics[0].metric("Warna hijau", f"{result['green_ratio']:.1%}")
metrics[1].metric("Kuning/cokelat", f"{result['yellow_brown_ratio']:.1%}")
metrics[2].metric("Indikasi menggulung", f"{result['curl_indicator']:.1%}")

st.subheader("Luas daun")
st.write(
    f"{result['leaf_area_px']:,.0f} piksel "
    f"({result['leaf_area_ratio']:.1%} dari area foto)."
)
st.caption(
    "Luas dihitung dari mask segmentasi dan bersifat relatif terhadap ukuran foto; "
    "bukan luas fisik dalam cm²."
)

if result["condition"] == "Normal":
    st.success("Daun tampak normal pada foto.")
elif result["condition"] == "Stres Ringan":
    st.warning("Terlihat perubahan ringan; pantau dengan foto berikutnya.")
elif result["condition"] == "Stres Sedang":
    st.warning("Terlihat perubahan yang perlu diperiksa lebih lanjut.")
else:
    st.error("Terlihat indikasi perubahan berat pada daun.")

st.caption(
    "Hasil adalah skrining visual, bukan diagnosis penyebab stres. "
    "Pencahayaan, sudut foto, varietas, dan background memengaruhi hasil."
)
