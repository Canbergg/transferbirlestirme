import io
import re
import pandas as pd
import streamlit as st

st.set_page_config(page_title="4 Dosya Birleştirici", layout="wide")
st.title("📑 4 Dosya Birleştirici")
st.caption("Önce otomatik eşleştirir; bulunamazsa seçim kutusu açar. Pair = Depo Kodu + Madde Kodu.")

OUTPUT_COLS = [
    "Pair", "Depo Kodu", "Depo Adı", "Madde Kodu", "Madde Açıklaması",
    "Minimum Miktar", "Stok", "Satış", "Envanter Gün Sayısı"
]

# ----------------- Alias listeleri -----------------
ALIASES = {
    "depo_kodu": [
        "depo kodu", "depo_kodu", "magaza kodu", "mağaza kodu",
        "warehouse code", "store code", "site code", "dc code", "location code"
    ],
    "depo_adi": [
        "depo adı", "depo adi", "magaza adı", "mağaza adı",
        "warehouse name", "store name", "location name"
    ],
    "madde_kodu": [
        "madde kodu", "urun kodu", "ürün kodu", "sku",
        "item code", "product code", "stok kodu"
    ],
    "madde_aciklamasi": [
        "madde açıklaması", "urun adi", "ürün adı",
        "aciklama", "açıklama", "item name", "product name", "description"
    ],
    "minimum_miktar": [
        "minimum miktar", "min miktar", "min. miktar",
        "min stok", "minimum", "minimummiktar",
        "emniyet stoğu", "emniyet stogu",
        "min qty", "minimum qty", "safety stock", "safety stock qty",
        # yazım hataları / varyasyonlar
        "minumum miktar", "minumum_miktar", "minumum"
    ],
    "envanter": [
        "envanter", "stok", "qty on hand", "quantity on hand", "on hand"
    ],
    # 'satış/sales' bilinçli olarak yok
    "toplam": [
        "toplam", "total", "genel toplam", "sum"
    ],
    "miktar": [
        "miktar", "adet", "quantity", "qty"
    ],
}

# ----------------- Yardımcılar -----------------
def read_xlsx(file):
    return pd.read_excel(file, sheet_name=0, header=0, dtype=str)

def normalize_text(s: str) -> str:
    if s is None:
        return ""
    s = str(s)
    tr_map = str.maketrans({
        "İ": "i", "I": "i", "ı": "i",
        "Ş": "s", "ş": "s",
        "Ğ": "g", "ğ": "g",
        "Ç": "c", "ç": "c",
        "Ö": "o", "ö": "o",
        "Ü": "u", "ü": "u",
    })
    s = s.translate(tr_map).lower()
    s = s.replace("\u00A0", " ").replace("\u2007", " ").replace("\u202F", " ")
    s = re.sub(r"[_\-]+", " ", s)
    s = re.sub(r"[^a-z0-9 ]+", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def _tokenize(norm: str):
    return [t for t in norm.split(" ") if t]

def try_find_col(df: pd.DataFrame, alias_keys: list):
    """Bulursa kolon adını döndürür; bulamazsa None döndürür."""
    wanted = set()
    for key in alias_keys:
        wanted.update(ALIASES.get(key, []))
    wanted_norm = [normalize_text(x) for x in wanted]

    norm_map = {}
    for c in df.columns:
        norm_map[normalize_text(c)] = c

    # Tam eşleşme
    for norm in wanted_norm:
        if norm in norm_map:
            return norm_map[norm]
    # İçerir
    for norm_col, orig in norm_map.items():
        for w in wanted_norm:
            if w and w in norm_col:
                return orig
    # Heuristik: tüm tokenlar
    for norm_col, orig in norm_map.items():
        for w in wanted_norm:
            tokens = _tokenize(w)
            if tokens and all(tok in norm_col for tok in tokens):
                return orig
    return None

def to_str_strip(s):
    return s.astype(str).str.strip()

def make_pair_from_cols(df, depo_col, madde_col):
    df[depo_col]  = to_str_strip(df[depo_col])
    df[madde_col] = to_str_strip(df[madde_col])
    return df[depo_col] + "|" + df[madde_col]

def safe_number_series(s):
    s = s.astype(str).str.replace(".", "", regex=False).str.replace(",", ".", regex=False)
    return pd.to_numeric(s, errors="coerce").fillna(0)

def choose_or_auto(df, alias_keys, label, key):
    """Önce otomatik bul; yoksa kullanıcıya selectbox aç. Seçimi döndür."""
    auto = try_find_col(df, alias_keys)
    cols = list(df.columns)
    default_idx = cols.index(auto) if (auto in cols) else 0
    return st.selectbox(label, cols, index=default_idx, key=key)

# ----------------- Yüklemeler -----------------
with st.sidebar:
    st.markdown("### 1) Ana Dosya (kimlik + Minimum Miktar)")
    f1 = st.file_uploader("1. Dosya", type=["xlsx", "xls"], key="f1")

    st.markdown("---")
    st.markdown("### 2) Stok Kaynağı (Envanter→Stok)")
    f2 = st.file_uploader("2. Dosya", type=["xlsx", "xls"], key="f2")

    st.markdown("---")
    st.markdown("### 3) Satış Kaynağı (Toplam→Satış)")
    f3 = st.file_uploader("3. Dosya", type=["xlsx", "xls"], key="f3")

    st.markdown("---")
    st.markdown("### 4) Envanter Gün Sayısı (Miktar>0 sayısı)")
    f4 = st.file_uploader("4. Dosya", type=["xlsx", "xls"], key="f4")

    st.markdown("---")
    do_preview = st.checkbox("Ön izleme göster", value=True)
    go = st.button("▶️ İşle")

colL, colR = st.columns([3, 2])

# -------- Kolon eşlemesi (otomatik + gerekirse manuel) --------
# 1) Ana Dosya
if f1:
    df1_tmp = read_xlsx(f1)
    st.subheader("1) Ana Dosya Kolon Eşlemesi")
    c1a, c1b, c1c = st.columns(3)
    depo_kodu_1  = c1a.selectbox("Depo Kodu (1.dosya)", df1_tmp.columns,
                                 index=list(df1_tmp.columns).index(try_find_col(df1_tmp, ["depo_kodu"])) if try_find_col(df1_tmp, ["depo_kodu"]) in df1_tmp.columns else 0,
                                 key="depokodu1")
    depo_adi_1   = c1b.selectbox("Depo Adı (1.dosya)", df1_tmp.columns,
                                 index=list(df1_tmp.columns).index(try_find_col(df1_tmp, ["depo_adi"])) if try_find_col(df1_tmp, ["depo_adi"]) in df1_tmp.columns else 0,
                                 key="depoadi1")
    madde_kodu_1 = c1c.selectbox("Madde Kodu (1.dosya)", df1_tmp.columns,
                                 index=list(df1_tmp.columns).index(try_find_col(df1_tmp, ["madde_kodu"])) if try_find_col(df1_tmp, ["madde_kodu"]) in df1_tmp.columns else 0,
                                 key="maddekodu1")
    c1d, c1e = st.columns(2)
    madde_acik_1 = c1d.selectbox("Madde Açıklaması (1.dosya)", df1_tmp.columns,
                                 index=list(df1_tmp.columns).index(try_find_col(df1_tmp, ["madde_aciklamasi"])) if try_find_col(df1_tmp, ["madde_aciklamasi"]) in df1_tmp.columns else 0,
                                 key="maddeacik1")
    min_miktar_1 = c1e.selectbox("Minimum Miktar (1.dosya)", df1_tmp.columns,
                                 index=list(df1_tmp.columns).index(try_find_col(df1_tmp, ["minimum_miktar"])) if try_find_col(df1_tmp, ["minimum_miktar"]) in df1_tmp.columns else 0,
                                 key="minmiktar1")
else:
    df1_tmp = None

# 2) Stok dosyası
if f2:
    df2_tmp = read_xlsx(f2)
    st.subheader("2) Stok Kaynağı Kolon Eşlemesi")
    c2a, c2b, c2c = st.columns(3)
    depo_kodu_2  = c2a.selectbox("Depo Kodu (2.dosya)", df2_tmp.columns,
                                 index=list(df2_tmp.columns).index(try_find_col(df2_tmp, ["depo_kodu"])) if try_find_col(df2_tmp, ["depo_kodu"]) in df2_tmp.columns else 0,
                                 key="depokodu2")
    madde_kodu_2 = c2b.selectbox("Madde Kodu (2.dosya)", df2_tmp.columns,
                                 index=list(df2_tmp.columns).index(try_find_col(df2_tmp, ["madde_kodu"])) if try_find_col(df2_tmp, ["madde_kodu"]) in df2_tmp.columns else 0,
                                 key="maddekodu2")
    envanter_2   = c2c.selectbox("Envanter→Stok (2.dosya)", df2_tmp.columns,
                                 index=list(df2_tmp.columns).index(try_find_col(df2_tmp, ["envanter"])) if try_find_col(df2_tmp, ["envanter"]) in df2_tmp.columns else 0,
                                 key="envanter2")
else:
    df2_tmp = None

# 3) Satış dosyası
if f3:
    df3_tmp = read_xlsx(f3)
    st.subheader("3) Satış Kaynağı Kolon Eşlemesi")
    c3a, c3b, c3c = st.columns(3)
    depo_kodu_3  = c3a.selectbox("Depo Kodu (3.dosya)", df3_tmp.columns,
                                 index=list(df3_tmp.columns).index(try_find_col(df3_tmp, ["depo_kodu"])) if try_find_col(df3_tmp, ["depo_kodu"]) in df3_tmp.columns else 0,
                                 key="depokodu3")
    madde_kodu_3 = c3b.selectbox("Madde Kodu (3.dosya)", df3_tmp.columns,
                                 index=list(df3_tmp.columns).index(try_find_col(df3_tmp, ["madde_kodu"])) if try_find_col(df3_tmp, ["madde_kodu"]) in df3_tmp.columns else 0,
                                 key="maddekodu3")
    toplam_3     = c3c.selectbox("Toplam→Satış (3.dosya)", df3_tmp.columns,
                                 index=list(df3_tmp.columns).index(try_find_col(df3_tmp, ["toplam"])) if try_find_col(df3_tmp, ["toplam"]) in df3_tmp.columns else 0,
                                 key="toplam3")
else:
    df3_tmp = None

# 4) Gün sayısı dosyası
if f4:
    df4_tmp = read_xlsx(f4)
    st.subheader("4) Envanter Gün Sayısı Kolon Eşlemesi")
    c4a, c4b, c4c = st.columns(3)
    depo_kodu_4  = c4a.selectbox("Depo Kodu (4.dosya)", df4_tmp.columns,
                                 index=list(df4_tmp.columns).index(try_find_col(df4_tmp, ["depo_kodu"])) if try_find_col(df4_tmp, ["depo_kodu"]) in df4_tmp.columns else 0,
                                 key="depokodu4")
    madde_kodu_4 = c4b.selectbox("Madde Kodu (4.dosya)", df4_tmp.columns,
                                 index=list(df4_tmp.columns).index(try_find_col(df4_tmp, ["madde_kodu"])) if try_find_col(df4_tmp, ["madde_kodu"]) in df4_tmp.columns else 0,
                                 key="maddekodu4")
    miktar_4     = c4c.selectbox("Miktar (4.dosya)", df4_tmp.columns,
                                 index=list(df4_tmp.columns).index(try_find_col(df4_tmp, ["miktar"])) if try_find_col(df4_tmp, ["miktar"]) in df4_tmp.columns else 0,
                                 key="miktar4")
else:
    df4_tmp = None

# ----------------- İşle -----------------
if go:
    if df1_tmp is None:
        st.error("1. dosyayı yüklemeden işlem yapılamaz.")
        st.stop()

    # 1) Ana tablo
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

    # 4) Gün sayısı
    gun_map = {}
    if df4_tmp is not None:
        df4 = df4_tmp[[depo_kodu_4, madde_kodu_4, miktar_4]].copy()
        df4.columns = ["Depo Kodu", "Madde Kodu", "Miktar"]
        df4["Pair"] = make_pair_from_cols(df4, "Depo Kodu", "Madde Kodu")
        miktar_num = safe_number_series(df4["Miktar"])
        df4["_POS"] = (miktar_num > 0).astype(int)
        gun_map = df4.groupby("Pair", as_index=True)["_POS"].sum().astype(int).to_dict()

    # Çıktı
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
    colL.info("4 dosyayı yükleyin, otomatik/manuel kolonu kontrol edin ve **İşle**'ye basın.")
