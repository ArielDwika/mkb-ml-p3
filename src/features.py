"""Fitur fisika. Dipakai saat training dan saat model dipakai, jadi jangan diubah di satu tempat saja."""
import numpy as np
import pandas as pd


def tambah_fitur(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    # TODO 4: lengkapi tiga fitur di bawah (lihat tabel rumus di atas)
    df["daya_W"] = df["torsi_Nm"] * 2 * np.pi * df["kecepatank_rpm"] / 60 if "kecepatank_rpm" in df.columns else df["torsi_Nm"] * 2 * np.pi * df["kecepatan_rpm"] / 60
    df["delta_suhu_K"] = df["suhu_proses_K"] - df["suhu_udara_K"]
    df["strain_tool"] = df["keausan_tool_menit"] * df["torsi_Nm"]
    return df
