import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from app import get_db, get_settings
from core.fingerprint import centroids, classify_fingerprint

db = get_db()
cfg = get_settings(db)
st.header("Fingerprint dan Peringatan")
data = db.fingerprint_data()
if data.empty:
    st.info("Belum ada hasil observasi lengkap untuk membangun fingerprint.")
    st.stop()

reference = centroids(data)
st.subheader("Fingerprint perlakuan dari observasi")
centroid_frame = pd.DataFrame.from_dict(reference, orient="index")
st.dataframe(centroid_frame, width="stretch")

selected_mode = st.radio("Sumber yang dianalisis", ["Observasi tersimpan", "Input manual"], horizontal=True)
if selected_mode == "Observasi tersimpan":
    labels = data.apply(lambda row: f"{row['code']} — {row['observed_at']}", axis=1)
    selected_index = st.selectbox("Pilih observasi", data.index, format_func=lambda index: labels[index])
    selected = data.loc[selected_index]
    row = {
        "norm_bioelectric": selected["norm_bio"],
        "norm_leaf_temp": selected["norm_temp"],
        "norm_color": selected["norm_color"],
        "norm_el": selected["norm_el"],
    }
else:
    with st.form("fingerprint"):
        row = {
            "norm_bioelectric": st.number_input("Bioelektrik ternormalisasi", 0.0, 1.0, 0.0),
            "norm_leaf_temp": st.number_input("Suhu ternormalisasi", 0.0, 1.0, 0.0),
            "norm_color": st.number_input("Warna ternormalisasi", 0.0, 1.0, 0.0),
            "norm_el": st.number_input("EL ternormalisasi", 0.0, 1.0, 0.0),
        }
        if not st.form_submit_button("Hitung fingerprint"):
            st.stop()

result = classify_fingerprint(row, cfg, reference)
result_cols = st.columns(4)
result_cols[0].metric("Stress Index", f"{result['stress_index']:.3f}")
result_cols[1].metric("Status", str(result["status"]))
result_cols[2].metric("Terdekat", str(result.get("nearest_treatment", "Belum tersedia")))
result_cols[3].metric("Jarak", f"{result['nearest_distance']:.3f}" if result.get("nearest_distance") is not None else "-")
if result["status"] == "High Stress":
    st.error("High Stress")
elif result["status"] == "Warning":
    st.warning("Warning")
else:
    st.success("Normal")
if result.get("ambiguous"):
    st.warning("Pola ambigu: perlakuan terdekat belum cukup berbeda.")

plot_data = pd.DataFrame({"Parameter": list(row.keys()), "Observasi": list(row.values())})
figure = go.Figure()
figure.add_trace(go.Scatterpolar(r=plot_data["Observasi"], theta=plot_data["Parameter"],
                                 fill="toself", name="Observasi"))
if result.get("nearest_treatment"):
    reference_row = reference[str(result["nearest_treatment"])]
    figure.add_trace(go.Scatterpolar(r=[reference_row[key] for key in row],
                                     theta=list(row.keys()), fill="toself",
                                     name=str(result["nearest_treatment"])))
figure.update_layout(polar={"radialaxis": {"visible": True, "range": [0, 1]}},
                     title="Fingerprint observasi dan referensi")
st.plotly_chart(figure, width="stretch")
