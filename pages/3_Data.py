from pathlib import Path

import streamlit as st

from app import get_db

db = get_db()
st.header("Data dan Ekspor")
treatment = st.selectbox("Filter perlakuan", ["Semua", "kontrol", "panas", "salinitas", "kekeringan"])
selected = None if treatment == "Semua" else treatment
frame = db.list_observations(selected)
st.dataframe(frame, width="stretch", hide_index=True)
csv = frame.to_csv(index=False).encode("utf-8")
st.download_button("Unduh CSV", csv, "observations.csv", "text/csv")
if st.button("Buat XLSX"):
    output = Path("data") / "observations.xlsx"
    db.export(output, selected)
    st.download_button("Unduh XLSX", output.read_bytes(), output.name,
                       "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
