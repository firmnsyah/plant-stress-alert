from datetime import date

import streamlit as st

from app import get_db

db = get_db()
st.header("Tanaman")
with st.form("plant"):
    code = st.text_input("Kode tanaman")
    treatment = st.selectbox("Perlakuan", ["kontrol", "panas", "salinitas", "kekeringan"])
    planted_at = st.date_input("Tanggal tanam", value=date.today())
    stress_started_at = st.date_input("Mulai cekaman", value=date.today())
    first_wilt_at = st.date_input("Layu pertama (opsional)", value=None)
    notes = st.text_area("Catatan")
    if st.form_submit_button("Simpan tanaman"):
        if not code.strip():
            st.error("Kode tanaman wajib diisi.")
        else:
            try:
                db.add_plant(code.strip(), treatment, planted_at=str(planted_at),
                             stress_started_at=str(stress_started_at),
                             first_wilt_at=str(first_wilt_at) if first_wilt_at else None,
                             notes=notes)
                st.success("Tanaman tersimpan.")
            except Exception as exc:
                st.error(f"Tanaman gagal disimpan: {exc}")
st.dataframe(db.list_plants(), width="stretch", hide_index=True)
