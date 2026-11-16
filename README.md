# Plant Stress Alert

Aplikasi Streamlit untuk skrining kondisi visual daun dari satu foto.

## Menjalankan

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

## Alur penggunaan

1. Upload satu foto daun.
2. Crop jika background ikut terseleksi.
3. Periksa mask daun.
4. Baca warna, luas relatif, indikator bentuk menggulung, skor, dan kondisi.

Output kondisi:

- Normal
- Stres Ringan
- Stres Sedang
- Stres Berat

Luas daun dihitung sebagai luas mask dalam piksel dan persentase area foto; luas fisik cm² tidak dapat diketahui tanpa skala referensi.

## Batas klaim

Hasil adalah skrining visual, bukan diagnosis penyebab stres. Pencahayaan, sudut kamera, varietas, background, dan kualitas segmentasi dapat memengaruhi hasil.
