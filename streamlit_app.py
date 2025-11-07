import io
import pandas as pd
import streamlit as st

st.set_page_config(page_title="4 Dosya Birleştirici", layout="wide")
st.title("📑 4 Dosya Birleştirici")
st.caption("Kolonları her dosya için elle seç. Pair = Depo Kodu + Madde Kodu. Toplama yok.")

OUTPUT_COLS = [
    "Pair", "Depo Kodu", "Depo Adı", "Madde Kodu", "Madde Açıklaması",
    "Minimum Miktar", "Stok", "Satış", "Envanter Gün Sayısı"
]

def read_xlsx(file):
    return pd.read_excel(file, sheet_name=0, header=0, dtype=str)

def to_str_strip(s):
    return s.astype(str).str.strip()

def make_pair_from_cols(df, depo_col, madde_col):
    df[depo_col]  = to_str_strip(df[depo_col])
    df[madde_col] = to_str_strip(df[madde_col])
    return df[depo_col] + "|" + df[madde_col]

def safe_number_series(s):
    # Nokta/virgül normalize et, sayı olmayanı 0 yap
    s = s.astype(str).str.replace(".", "", regex=False).str.replace(",", ".", regex=False)
    return pd.to_numeric(s, errors="coerce").fillna(0)

with st.sidebar:
    st.markdown("### 1) Ana Dosya (kimlik + Minimum Miktar)")
    f1 = st.file_uploader("1. Dosya", type=["xlsx","xls"], key="f1")

    st.markdown("---")
    st.markdown("### 2) Stok Kaynağı (Envanter→Stok)")
    f2 = st.file_uploader("2. Dosya", type=["xlsx","xls"], key="f2")

    st.markdown("---")
    st.markdown("### 3) Satış Kaynağı (Toplam→Satış)")
    f3 = st.file_uploader("3. Dosya", type=["xlsx","xls"], key="f3")

    st.markdown("---")
    st.markdown("### 4) Envanter Gün Sayısı (Miktar>0 sayısı)")
    f4 = st.file_uploader("4. Dosya", type=["xlsx","xls"], key="f4")

    st.markdown("---")
    do_preview = st.checkbox("Ön izleme göster", value=True)
    go = st.button("▶️ İşle")

colL, colR = st.columns([3,2])

# --- 1. dosya yüklendiyse kolon seçimleri ---
if f1:
    df1_tmp = read_xlsx(f1)
    cols1 = list(df1_tmp.columns)

    st.subheader("1) Ana Dosya Kolon Eşlemesi")
    c1a, c1b, c1c = st.columns(3)
    depo_kodu_1  = c1a.selectbox("Depo Kodu (1.dosya)", cols1, key="depokodu1")
    depo_adi_1   = c1b.selectbox("Depo Adı (1.dosya)", cols1, key="depoadi1")
    madde_kodu_1 = c1c.selectbox("Madde Kodu (1.dosya)", cols1, key="maddekodu1")
    c1d, c1e = st.columns(2)
    madde_acik_1 = c1d.selectbox("Madde Açıklaması (1.dosya)", cols1, key="maddeacik1")
    min_miktar_1 = c1e.selectbox("Minimum Miktar (1.dosya)", cols1, key="minmiktar1")
else:
    df1_tmp = None

# --- 2. dosya kolon seçimleri ---
if f2:
    df2_tmp = read_xlsx(f2)
    cols2 = list(df2_tmp.columns)

    st.subheader("2) Stok Kaynağı Kolon Eşlemesi")
    c2a, c2b, c2c = st.columns(3)
    depo_kodu_2  = c2a.selectbox("Depo Kodu (2.dosya)", cols2, key="depokodu2")
    madde_kodu_2 = c2b.selectbox("Madde Kodu (2.dosya)", cols2, key="maddekodu2")
    envanter_2   = c2c.selectbox("Envanter→Stok (2.dosya)", cols2, key="envanter2")
else:
    df2_tmp = None

# --- 3. dosya kolon seçimleri ---
if f3:
    df3_tmp = read_xlsx(f3)
    cols3 = list(df3_tmp.columns)

    st.subheader("3) Satış Kaynağı Kolon Eşlemesi")
    c3a, c3b, c3c = st.columns(3)
    depo_kodu_3  = c3a.selectbox("Depo Kodu (3.dosya)", cols3, key="depokodu3")
    madde_kodu_3 = c3b.selectbox("Madde Kodu (3.dosya)", cols3, key="maddekodu3")
    toplam_3     = c3c.selectbox("Toplam→Satış (3.dosya)", cols3, key="toplam3")
else:
    df3_tmp = None

# --- 4. dosya kolon seçimleri ---
if f4:
    df4_tmp = read_xlsx(f4)
    cols4 = list(df4_tmp.columns)

    st.subheader("4) Envanter Gün Sayısı Kaynağı Kolon Eşlemesi")
    c4a, c4b, c4c = st.columns(3)
    depo_kodu_4  = c4a.selectbox("Depo Kodu (4.dosya)", cols4, key="depokodu4")
    madde_kodu_4 = c4b.selectbox("Madde Kodu (4.dosya)", cols4, key="maddekodu4")
    miktar_4     = c4c.selectbox("Miktar (4.dosya)", cols4, key="miktar4")
else:
    df4_tmp = None

if go:
    # 1) Ana tablo zorunlu
    if df1_tmp is None:
        st.error("1. dosyayı yüklemeden işlem yapılamaz.")
        st.stop()

    # Ana tablo çek
    df1 = df1_tmp[[depo_kodu_1, depo_adi_1, madde_kodu_1, madde_acik_1, min_miktar_1]].copy()
    df1.columns = ["Depo Kodu", "Depo Adı", "Madde Kodu", "Madde Açıklaması", "Minimum Miktar"]
    df1["Pair"] = make_pair_from_cols(df1, "Depo Kodu", "Madde Kodu")
    df1["Minimum Miktar"] = safe_number_series(df1["Minimum Miktar"])

    # 2) Stok
    stok_map = {}
    if df2_tmp is not None:
        df2 = df2_tmp[[depo_kodu_2, madde_kodu_2, envanter_2]].copy()
        df2.columns = ["Depo Kodu", "Madde Kodu", "Envanter"]
        df2["Pair"] = make_pair_from_cols(df2, "Depo Kodu", "Madde Kodu")
        df2["Envanter"] = safe_number_series(df2["Envanter"])
        # aynı key tekrarı yok varsayımı: ilk değer
        df2 = df2.drop_duplicates("Pair")
        stok_map = df2.set_index("Pair")["Envanter"].to_dict()

    # 3) Satış
    satis_map = {}
    if df3_tmp is not None:
        df3 = df3_tmp[[depo_kodu_3, madde_kodu_3, toplam_3]].copy()
        df3.columns = ["Depo Kodu", "Madde Kodu", "Toplam"]
        df3["Pair"] = make_pair_from_cols(df3, "Depo Kodu", "Madde Kodu")
        df3["Toplam"] = safe_number_series(df3["Toplam"])
        df3 = df3.drop_duplicates("Pair")
        satis_map = df3.set_index("Pair")["Toplam"].to_dict()

    # 4) Envanter Gün Sayısı
    gun_map = {}
    if df4_tmp is not None:
        df4 = df4_tmp[[depo_kodu_4, madde_kodu_4, miktar_4]].copy()
        df4.columns = ["Depo Kodu", "Madde Kodu", "Miktar"]
        df4["Pair"] = make_pair_from_cols(df4, "Depo Kodu", "Madde Kodu")
        miktar_num = safe_number_series(df4["Miktar"])
        df4["_POS"] = (miktar_num > 0).astype(int)
        gun_map = df4.groupby("Pair", as_index=True)["_POS"].sum().astype(int).to_dict()

    # Çıkış
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
    colL.info("Sol taraftan dosyaları yükleyip kolonları seçin ve **İşle** butonuna basın.")
