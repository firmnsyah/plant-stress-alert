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

## Alur penggunaan

1. Daftarkan tanaman dan perlakuan di halaman **Tanaman**.
2. Masukkan pengukuran dan foto di **Input Observasi**.
3. Periksa mask foto sebelum menyimpan.
4. Setelah disimpan, aplikasi menampilkan EL, ΔT, DGCI, nilai normalisasi, Stress Index, dan status.
5. Gunakan **Data** untuk filter, impor CSV data logger, ekspor CSV/XLSX, dan hapus lunak.
6. Gunakan **Analisis** untuk grafik waktu, ANOVA/Tukey, dan PCA.
7. Gunakan **Fingerprint** untuk membangun centroid dari hasil observasi berlabel dan membandingkan observasi.
8. Gunakan **Pengaturan** untuk membuat versi ambang dan bobot yang dapat direproduksi.

## Batas klaim

Model v1.0 menggunakan Stress Index dan centroid fingerprint. Ambang contoh harus dikalibrasi dari data pilot. Klaim deteksi sebelum layu hanya boleh dibuat bila analisis waktu menunjukkan peringatan lebih awal pada data validasi independen.
