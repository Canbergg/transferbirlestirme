import io
import re
import pandas as pd
import streamlit as st

st.set_page_config(page_title="4 Dosya Birleştirici", layout="wide")
st.title("📑 4 Dosya Birleştirici")
st.caption("Kolonlar başlık adına göre bulunur (konumdan bağımsız). Pair = Depo Kodu + Madde Kodu.")

OUTPUT_COLS = [
    "Pair", "Depo Kodu", "Depo Adı", "Madde Kodu", "Madde Açıklaması",
    "Minimum Miktar", "Stok", "Satış", "Envanter Gün Sayısı"
]

# ----------------- Başlık eşleme: alias listeleri -----------------
# Not: 'toplam' listesinden 'satış/sales' bilerek çıkarıldı.
ALIASES = {
    "depo_kodu": [
        "depo kodu", "depo_kodu", "magaza kodu", "mağaza kodu",
        "warehouse code", "store code", "site code"
    ],
    "depo_adi": [
        "depo adı", "depo adi", "magaza adı", "mağaza adı",
        "warehouse name", "store name"
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
        "min qty", "minimum qty", "safety stock", "safety stock qty"
    ],
    "envanter": [
        "envanter", "stok", "qty on hand", "quantity on hand", "on hand"
    ],
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
    """Türkçe harf düzeltmesi + NBSP temizleme + noktalama/underscore temizleme + çoklu boşlukları tek boşluk yapma."""
    if s is None:
        return ""
    s = str(s)

    # Türkçe karakter haritalaması
    tr_map = str.maketrans({
        "İ": "i", "I": "i", "ı": "i",
        "Ş": "s", "ş": "s",
        "Ğ": "g", "ğ": "g",
        "Ç": "c", "ç": "c",
        "Ö": "o", "ö": "o",
        "Ü": "u", "ü": "u",
    })
    s = s.translate(tr_map).lower()

    # NBSP ve benzeri boşluk karakterlerini normal boşluğa çevir
    s = s.replace("\u00A0", " ").replace("\u2007", " ").replace("\u202F", " ")

    # Alt çizgi ve tire gibi ayraçları boşluğa çevir
    s = re.sub(r"[_\-]+", " ", s)

    # Noktalama işaretlerini sil (harf/rakam ve boşluk dışını kaldır)
    s = re.sub(r"[^a-z0-9 ]+", "", s)

    # Çoklu boşlukları tek boşluğa indir ve kırp
    s = re.sub(r"\s+", " ", s).strip()

    return s

def _tokenize(norm: str):
    return [t for t in norm.split(" ") if t]

def find_col(df: pd.DataFrame, alias_keys: list) -> str:
    """
    1) Tam eşleşme (normalize)
    2) İçerir (contains) eşleşmesi
    3) Heuristik: alias ifadelerindeki tüm token'ları içeren kolon adını bul
    Bulamazsa açıklayıcı hata ve mevcut başlıkları göster.
    """
    # hedef alias'ları topla ve normalize et
    wanted = set()
    for key in alias_keys:
        wanted.update(ALIASES.get(key, []))
    wanted_norm = [normalize_text(x) for x in wanted]

    # mevcut kolonları normalize et -> orijinal ad
    norm_map = {}  # normalize_ad -> orijinal_ad
    for c in df.columns:
        norm_map[normalize_text(c)] = c

    # 1) Tam eşleşme
    for norm in wanted_norm:
        if norm in norm_map:
            return norm_map[norm]

    # 2) İçerir eşleşmesi
    for norm_col, orig in norm_map.items():
        for w in wanted_norm:
            if w and w in norm_col:
                return orig

    # 3) Heuristik: tüm token'lar kolon adında geçiyor mu?
    for norm_col, orig in norm_map.items():
        for w in wanted_norm:
            tokens = _tokenize(w)
            if tokens and all(tok in norm_col for tok in tokens):
                return orig

    # Hata: mevcut başlıkları kullanıcıya göster
    cols_list = ", ".join([str(c) for c in df.columns])
    raise KeyError(
        "Aranan başlık bulunamadı. Aranan varyasyonlar: "
        f"{sorted(wanted)} | Mevcut başlıklar: {cols_list}"
    )

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

# ----------------- UI -----------------
with st.sidebar:
    st.markdown("### 1) Ana Dosya (kimlik + Minimum Miktar)")
    f1 = st.file_uploader("1. Dosya", type=["xlsx", "xls"], key="f1")
    st.markdown("İçermesi gereken başlıklar: Depo Kodu, Depo Adı, Madde Kodu, Madde Açıklaması, Minimum Miktar")

    st.markdown("---")
    st.markdown("### 2) Stok Kaynağı (Envanter→Stok)")
    f2 = st.file_uploader("2. Dosya", type=["xlsx", "xls"], key="f2")
    st.markdown("İçermesi gereken başlıklar: Depo Kodu, Madde Kodu, Envanter")

    st.markdown("---")
    st.markdown("### 3) Satış Kaynağı (Toplam→Satış)")
    f3 = st.file_uploader("3. Dosya", type=["xlsx", "xls"], key="f3")
    st.markdown("İçermesi gereken başlıklar: Depo Kodu, Madde Kodu, Toplam")

    st.markdown("---")
    st.markdown("### 4) Envanter Gün Sayısı (Miktar>0 sayısı)")
    f4 = st.file_uploader("4. Dosya", type=["xlsx", "xls"], key="f4")
    st.markdown("İçermesi gereken başlıklar: Depo Kodu, Madde Kodu, Miktar")

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

    depo_kodu_col  = find_col(df1, ["depo_kodu"])
    depo_adi_col   = find_col(df1, ["depo_adi"])
    madde_kodu_col = find_col(df1, ["madde_kodu"])
    madde_acik_col = find_col(df1, ["madde_aciklamasi"])
    min_miktar_col = find_col(df1, ["minimum_miktar"])

    df1 = df1[[depo_kodu_col, depo_adi_col, madde_kodu_col, madde_acik_col, min_miktar_col]].copy()
    df1.columns = ["Depo Kodu", "Depo Adı", "Madde Kodu", "Madde Açıklaması", "Minimum Miktar"]

    df1["Pair"] = make_pair_from_cols(df1, "Depo Kodu", "Madde Kodu")
    df1["Minimum Miktar"] = safe_number_series(df1["Minimum Miktar"])

    # 2) Stok: Envanter -> Stok (birden fazla satır yok; ilk değer)
    stok_map = {}
    if f2:
        df2 = read_xlsx(f2)
        depo_kodu_2  = find_col(df2, ["depo_kodu"])
        madde_kodu_2 = find_col(df2, ["madde_kodu"])
        envanter_col = find_col(df2, ["envanter"])
        df2 = df2[[depo_kodu_2, madde_kodu_2, envanter_col]].copy()
        df2.columns = ["Depo Kodu", "Madde Kodu", "Envanter"]
        df2["Pair"] = make_pair_from_cols(df2, "Depo Kodu", "Madde Kodu")
        df2["Envanter"] = safe_number_series(df2["Envanter"])
        stok_map = df2.drop_duplicates("Pair").set_index("Pair")["Envanter"].to_dict()

    # 3) Satış: Toplam -> Satış (birden fazla satır yok; ilk değer)
    satis_map = {}
    if f3:
        df3 = read_xlsx(f3)
        depo_kodu_3  = find_col(df3, ["depo_kodu"])
        madde_kodu_3 = find_col(df3, ["madde_kodu"])
        toplam_col   = find_col(df3, ["toplam"])  # 'satış/sales' yok
        df3 = df3[[depo_kodu_3, madde_kodu_3, toplam_col]].copy()
        df3.columns = ["Depo Kodu", "Madde Kodu", "Toplam"]
        df3["Pair"] = make_pair_from_cols(df3, "Depo Kodu", "Madde Kodu")
        df3["Toplam"] = safe_number_series(df3["Toplam"])
        satis_map = df3.drop_duplicates("Pair").set_index("Pair")["Toplam"].to_dict()

    # 4) Envanter Gün Sayısı: Miktar > 0 sayısı (Pair bazında)
    gun_map = {}
    if f4:
        df4 = read_xlsx(f4)
        depo_kodu_4  = find_col(df4, ["depo_kodu"])
        madde_kodu_4 = find_col(df4, ["madde_kodu"])
        miktar_col   = find_col(df4, ["miktar"])
        df4 = df4[[depo_kodu_4, madde_kodu_4, miktar_col]].copy()
        df4.columns = ["Depo Kodu", "Madde Kodu", "Miktar"]
        df4["Pair"] = make_pair_from_cols(df4, "Depo Kodu", "Madde Kodu")
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
