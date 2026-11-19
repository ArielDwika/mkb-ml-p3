"""UI Streamlit untuk teknisi pabrik.

Jalankan dari root repo:
    streamlit run app/ui/streamlit_app.py
"""
import os
import sys
from pathlib import Path

import pandas as pd
import requests
import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from app import predictor  # noqa: E402


def _api_url() -> str:
    try:
        url = st.secrets.get("API_URL", "")
    except Exception:
        url = ""
    return (url or os.getenv("API_URL", "")).rstrip("/")


API_URL = _api_url()
TIMEOUT = 60  


def prediksi(rows: list[dict]) -> list[dict]:
    if not API_URL:
        return predictor.predict_rows(rows)
    path = "/predict" if len(rows) == 1 else "/predict/batch"
    r = requests.post(API_URL + path, json=rows[0] if len(rows) == 1 else rows, timeout=TIMEOUT)
    if r.status_code == 422:
        raise ValueError(f"Input ditolak API (422): {r.json().get('detail')}")
    r.raise_for_status()
    hasil = r.json()
    return [hasil] if len(rows) == 1 else hasil


def info_model() -> dict:
    if not API_URL:
        return predictor.load()[1]
    r = requests.get(API_URL + "/health", timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()


# Konfigurasi Halaman (Lebih lebar)
st.set_page_config(page_title="Dashboard Mesin CNC", page_icon="⚙️", layout="centered")

try:
    META = info_model()
except Exception as e:
    st.error(f"Koneksi model terputus: {e}")
    st.stop()

FITUR = META["fitur_input"]

# --- SIDEBAR (Informasi Sistem) ---
with st.sidebar:
    st.title("⚙️ Panel Sistem")
    st.caption("Monitoring Prediktif Mesin CNC")
    st.divider()
    st.markdown("**Status Koneksi:**")
    if API_URL:
        st.success(f"🌐 Terhubung (Mode B)\n\nAPI: `{API_URL}`")
    else:
        st.info("💻 Lokal (Mode A)\n\nModel berjalan langsung di memori.")
    
    st.markdown("**Spesifikasi Model:**")
    st.code(f"Versi  : {META['versi_model']}\nBatas  : {META['threshold']}", language="text")

# --- HALAMAN UTAMA ---
st.title("Prediksi Kegagalan Mesin")
st.markdown("Masukkan parameter operasional saat ini untuk menganalisis risiko kegagalan *(downtime)* dalam 24 jam ke depan.")
st.write("") # Jarak

tab_satu, tab_batch = st.tabs(["🎛️ Input Manual", "📂 Analisis Batch (CSV)"])

# --- TAB 1: INPUT MANUAL ---
with tab_satu:
    with st.form("input_form", border=True):
        st.markdown("### 📋 Parameter Operasional")
        
        # Kelompok 1
        st.markdown("##### 🏭 Profil Pekerjaan")
        c1, c2 = st.columns(2)
        tipe = c1.selectbox("Tipe Kualitas Produk", ["L", "M", "H"], help="L: Rendah, M: Menengah, H: Tinggi")
        shift = c2.selectbox("Jadwal Shift", ["pagi", "siang", "malam"], index=2)
        
        st.divider()
        
        # Kelompok 2
        st.markdown("##### 🌡️ Kondisi Suhu & Lingkungan")
        c3, c4 = st.columns(2)
        suhu_udara = c3.number_input("Suhu Udara (K)", 250.0, 350.0, 301.2, 0.1)
        suhu_proses = c4.number_input("Suhu Proses (K)", 250.1, 400.0, 310.8, 0.1)
        
        st.divider()

        # Kelompok 3
        st.markdown("##### ⚙️ Sensor Mekanis & Pemeliharaan")
        c5, c6 = st.columns(2)
        rpm = c5.number_input("Kecepatan Putar (rpm)", 500.0, 4000.0, 1290.0, 10.0)
        torsi = c6.number_input("Torsi (Nm)", 0.0, 150.0, 62.5, 0.5)
        aus = c5.number_input("Keausan Tool (menit)", 0.0, 500.0, 228.0, 1.0)
        getar = c6.number_input("Tingkat Getaran (mm/s)", 0.0, 50.0, 4.1, 0.1)
        jam = st.number_input("Durasi Sejak Servis Terakhir (Jam)", 0.0, 10_000.0, 410.0, 1.0)
        
        st.write("")
        kirim = st.form_submit_button("🔍 Jalankan Analisis")

    if kirim:
        row = {"tipe_produk": tipe, "suhu_udara_K": suhu_udara, "suhu_proses_K": suhu_proses,
               "kecepatan_rpm": rpm, "torsi_Nm": torsi, "keausan_tool_menit": aus,
               "getaran_mm_s": getar, "jam_sejak_servis": jam, "shift_operator": shift}
        
        st.markdown("### 📊 Hasil Analisis")
        try:
            hasil = prediksi([row])[0]
        except Exception as e:
            st.error(f"Gagal memprediksi: {e}")
        else:
            p = hasil["probabilitas_gagal"]
            
            mc1, mc2 = st.columns(2)
            if hasil["status"] == "SEGERA SERVIS":
                mc1.metric("Rekomendasi Tindakan", "⚠️ SEGERA SERVIS", delta="Kritis", delta_color="inverse")
                mc2.metric("Peluang Gagal", f"{p:.1%}")
                st.error("**Tindakan Diperlukan:** Parameter menunjukkan anomali risiko tinggi. Hentikan operasi atau jadwalkan pemeriksaan teknis segera.")
            else:
                mc1.metric("Rekomendasi Tindakan", "✅ AMAN", delta="Normal", delta_color="normal")
                mc2.metric("Peluang Gagal", f"{p:.1%}")
                st.success("**Status Operasional:** Mesin beroperasi dalam batas parameter yang aman. Lanjutkan proses produksi.")
            
            st.progress(min(p, 1.0))
            
            with st.expander("🛠️ Log Data (JSON)"):
                st.json({"request": row, "response": hasil})

# --- TAB 2: ANALISIS BATCH ---
with tab_batch:
    st.markdown("### 📂 Unggah Data Historis (CSV)")
    st.write("Analisis puluhan mesin secara bersamaan menggunakan file CSV. Pastikan kolom sesuai format sistem.")
    
    contoh = ROOT / "data" / "contoh_batch.csv"
    if contoh.exists():
        st.download_button("📥 Unduh Format CSV Contoh", contoh.read_bytes(), "contoh_batch.csv", "text/csv")
    
    st.write("")
    up = st.file_uploader("Seret dan lepas file CSV di sini", type="csv")
    
    if up is not None:
        df = pd.read_csv(up)
        kurang = [k for k in FITUR if k not in df.columns]
        if kurang:
            st.error(f"Format tidak valid! Kolom berikut hilang: {kurang}")
        else:
            df["shift_operator"] = df["shift_operator"].astype(str).str.strip().str.lower()
            X = df[FITUR]
            rows = X.astype(object).where(X.notna(), None).to_dict("records")
            
            with st.spinner('Menganalisis data...'):
                try:
                    hasil = pd.DataFrame(prediksi(rows))
                except Exception as e:
                    st.error(f"Gagal memprediksi: {e}")
                else:
                    out = pd.concat([df.reset_index(drop=True), hasil[["probabilitas_gagal", "status"]]], axis=1)
                    out = out.sort_values("probabilitas_gagal", ascending=False)
                    n = int((out["status"] == "SEGERA SERVIS").sum())
                    
                    st.divider()
                    st.markdown("### 📑 Ringkasan Batch")
                    
                    # Highlight baris kritis
                    def highlight_status(s):
                        return ['background-color: #ffcccc; color: black; font-weight: bold' if v == 'SEGERA SERVIS' else '' for v in s]
                    
                    styled_df = out.style.apply(highlight_status, subset=['status'])
                    
                    if n > 0:
                        st.warning(f"**Peringatan:** Ditemukan **{n} mesin** dengan risiko kerusakan tinggi dari total {len(out)} mesin.")
                    else:
                        st.success(f"Seluruh {len(out)} mesin dalam kondisi aman.")
                        
                    st.dataframe(styled_df, hide_index=True)
                    st.download_button("📤 Ekspor Hasil Laporan (CSV)", out.to_csv(index=False).encode(), "laporan_prediksi.csv", "text/csv")