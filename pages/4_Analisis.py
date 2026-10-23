import plotly.express as px
import streamlit as st

from app import get_db

db = get_db()
st.header("Analisis")
frame = db.list_observations()
if frame.empty:
    st.info("Belum ada observasi.")
    st.stop()
if "stress_index" in frame and frame["stress_index"].notna().any():
    st.plotly_chart(px.line(frame, x="observed_at", y="stress_index", color="treatment",
                            markers=True, title="Stress Index terhadap waktu"),
                    width="stretch")
st.subheader("Ringkasan per perlakuan")
st.dataframe(frame.groupby("treatment", as_index=False).agg(
    observasi=("id", "count"), rata_stress=("stress_index", "mean")),
    width="stretch", hide_index=True)
