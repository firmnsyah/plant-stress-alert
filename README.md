# Plant Stress Fingerprint

Aplikasi Streamlit untuk mencatat empat pengukuran murah pada cabai, menganalisis warna daun, dan merangkum pola cekaman.

## Menjalankan

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

Data lokal disimpan di `data/plant.db`. Jangan memasukkan database, foto, atau hasil eksperimen ke Git. Google Sheets/Supabase belum termasuk v1.0.

## Batas klaim

Model v1.0 menggunakan Stress Index dan centroid fingerprint. Ambang contoh harus dikalibrasi dari data pilot. Klaim deteksi sebelum layu hanya boleh dibuat bila analisis waktu menunjukkan peringatan lebih awal pada data validasi independen.
