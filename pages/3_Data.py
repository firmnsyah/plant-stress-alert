from pathlib import Path

import streamlit as st
import pandas as pd

from app import get_db

db = get_db()
st.header("Data dan Ekspor")
with st.expander("Impor CSV data logger"):
    uploaded_csv = st.file_uploader("CSV observasi", type=["csv"])
    if uploaded_csv is not None and st.button("Impor observasi CSV"):
        try:
            imported, errors = db.import_observations(pd.read_csv(uploaded_csv))
            st.success(f"{imported} baris berhasil diimpor.")
            if errors:
                st.warning("Sebagian baris gagal:")
                st.code("\n".join(errors))
        except ValueError as exc:
            st.error(str(exc))
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
if not frame.empty:
    delete_id = st.selectbox("ID observasi untuk hapus lunak", [None, *frame["id"].astype(int).tolist()])
    if delete_id is not None and st.button("Hapus observasi terpilih"):
        db.soft_delete_observation(int(delete_id))
        st.success("Observasi dihapus secara lunak. Muat ulang halaman untuk melihat hasilnya.")
