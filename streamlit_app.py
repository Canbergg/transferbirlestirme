import io
import pandas as pd
import streamlit as st

st.set_page_config(page_title="4 Dosya Birleştirici", layout="wide")
st.title("📑 4 Dosya Birleştirici")
st.caption("Pair = Depo Kodu + Madde Kodu. Stok=Envanter, Satış=Toplam, Envanter Gün Sayısı=Miktar>0 olan gün sayısı.")

OUTPUT_COLS = [
    "Pair", "Depo Kodu", "Depo Adı", "Madde Kodu", "Madde Açıklaması",
    "Minimum Miktar", "Stok", "Satış", "Envanter Gün Sayısı"
]

# ----------------- Yardımcılar -----------------
def read_xlsx(file):
    return pd.read_excel(file, sheet_name=0, header=0, dtype=str)

def to_str_strip(s):
    return s.astype(str).str.strip()

def make_pair(df, depo_col="Depo Kodu", madde_col="Madde Kodu"):
    df[depo_col] = to_str_strip(df[depo_col])
    df[madde_col] = to_str_strip(df[madde_col])
    return df[depo_col] + "|" + df[madde_col]

def safe_number_series(s):
    # Nokta/virgül normalize et, sayı olmayanı 0 yap
    s = s.astype(str).str.replace(".", "", regex=False).str.replace(",", ".", regex=False)
    return pd.to_numeric(s, errors="coerce").fillna(0)

# ----------------- UI -----------------
with st.sidebar:
    st.markdown("### 1) Ana Dosya (kimlik + Minimum Miktar)")
    f1 = st.file_uploader("1. Dosya", type=["xlsx", "xls"], key="f1")
    st.markdown("Beklenen sütunlar: **Depo Kodu, Depo Adı, Madde Kodu, Madde Açıklaması, Minimum Miktar**")

    st.markdown("---")
    st.markdown("### 2) Stok Kaynağı (Envanter→Stok)")
    f2 = st.file_uploader("2. Dosya", type=["xlsx", "xls"], key="f2")
    st.markdown("Beklenen sütunlar: **Depo Kodu, Madde Kodu, Envanter**")

    st.markdown("---")
    st.markdown("### 3) Satış Kaynağı (Toplam→Satış)")
    f3 = st.file_uploader("3. Dosya", type=["xlsx", "xls"], key="f3")
    st.markdown("Beklenen sütunlar: **Depo Kodu, Madde Kodu, Toplam**")

    st.markdown("---")
    st.markdown("### 4) Envanter Gün Sayısı (Miktar>0 sayısı)")
    f4 = st.file_uploader("4. Dosya", type=["xlsx", "xls"], key="f4")
    st.markdown("Beklenen sütunlar: **Depo Kodu, Madde Kodu, Miktar**")

    st.markdown("---")
    do_preview = st.checkbox("Ön izleme göster", value=True)
    go = st.button("▶️ İşle")

colL, colR = st.columns([3, 2])

if go:
    # 1) Ana dosya
    if not f1:
        st.error("1. dosyayı yüklemeden işlem yapılamaz.")
        st.stop()

    df1 = read_xlsx(f1)
    need_cols1 = ["Depo Kodu", "Depo Adı", "Madde Kodu", "Madde Açıklaması", "Minimum Miktar"]
    for c in need_cols1:
        if c not in df1.columns:
            st.error(f"1. Dosyada '{c}' kolonu eksik.")
            st.stop()

    df1 = df1[need_cols1].copy()
    df1["Pair"] = make_pair(df1, "Depo Kodu", "Madde Kodu")
    df1["Minimum Miktar"] = safe_number_series(df1["Minimum Miktar"])  # sayısal

    # 2) Stok: Envanter -> Stok (birden fazla satır yok; ilk değer)
    stok_map = {}
    if f2:
        df2 = read_xlsx(f2)
        need_cols2 = ["Depo Kodu", "Madde Kodu", "Envanter"]
        for c in need_cols2:
            if c not in df2.columns:
                st.error(f"2. Dosyada '{c}' kolonu eksik.")
                st.stop()
        df2 = df2[need_cols2].copy()
        df2["Pair"] = make_pair(df2, "Depo Kodu", "Madde Kodu")
        df2["Envanter"] = safe_number_series(df2["Envanter"])
        stok_map = df2.drop_duplicates("Pair").set_index("Pair")["Envanter"].to_dict()

    # 3) Satış: Toplam -> Satış (birden fazla satır yok; ilk değer)
    satis_map = {}
    if f3:
        df3 = read_xlsx(f3)
        need_cols3 = ["Depo Kodu", "Madde Kodu", "Toplam"]
        for c in need_cols3:
            if c not in df3.columns:
                st.error(f"3. Dosyada '{c}' kolonu eksik.")
                st.stop()
        df3 = df3[need_cols3].copy()
        df3["Pair"] = make_pair(df3, "Depo Kodu", "Madde Kodu")
        df3["Toplam"] = safe_number_series(df3["Toplam"])
        satis_map = df3.drop_duplicates("Pair").set_index("Pair")["Toplam"].to_dict()

    # 4) Envanter Gün Sayısı: Miktar > 0 sayısı (Pair bazında)
    gun_map = {}
    if f4:
        df4 = read_xlsx(f4)
        need_cols4 = ["Depo Kodu", "Madde Kodu", "Miktar"]
        for c in need_cols4:
            if c not in df4.columns:
                st.error(f"4. Dosyada '{c}' kolonu eksik.")
                st.stop()
        df4 = df4[need_cols4].copy()
        df4["Pair"] = make_pair(df4, "Depo Kodu", "Madde Kodu")
        miktar_num = safe_number_series(df4["Miktar"])
        df4["_POS"] = (miktar_num > 0).astype(int)
        gun_map = df4.groupby("Pair", as_index=True)["_POS"].sum().astype(int).to_dict()

    # Çıkış tablosu
    out = df1[["Pair", "Depo Kodu", "Depo Adı", "Madde Kodu", "Madde Açıklaması", "Minimum Miktar"]].copy()
    out["Stok"] = out["Pair"].map(stok_map).fillna(0)
    out["Satış"] = out["Pair"].map(satis_map).fillna(0)
    out["Envanter Gün Sayısı"] = out["Pair"].map(gun_map).fillna(0).astype(int)

    out["Stok"] = pd.to_numeric(out["Stok"], errors="coerce").fillna(0)
    out["Satış"] = pd.to_numeric(out["Satış"], errors="coerce").fillna(0)

    out = out.reindex(columns=OUTPUT_COLS)

    if do_preview:
        colL.markdown("### Ön İzleme")
        colL.dataframe(out.head(200), use_container_width=True)

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as wr:
        out.to_excel(wr, index=False, sheet_name="Output")
    buffer.seek(0)

    colR.download_button(
        label="💾 Çıktıyı İndir (Excel)",
        data=buffer.getvalue(),
        file_name="cikti_birlesik.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

else:
    colL.info("Sol taraftan dosyaları yükleyip **İşle** butonuna basın.")
