import pandas as pd
import re

def _normalize_cuit(x):
    if pd.isna(x):
        return pd.NA
    s = re.sub(r"\D+", "", str(x))
    return s if s else pd.NA

def _normalize_name(x):
    if pd.isna(x):
        return ""
    return str(x).strip().upper()

def _to_number_locale(x):
    if pd.isna(x) or x == "":
        return pd.NA
    if isinstance(x, (int, float)):
        return float(x)
    s = str(x).strip().replace(".", "").replace(",", ".")
    try:
        return float(s)
    except Exception:
        return pd.NA

# ---------- helpers para mapeo por letra o nombre ----------
def _resolve_col(df, key):
    if key is None:
        return None
    key = str(key).strip()
    if len(key) <= 3 and key.isalpha():         
        def col_letter_to_index(letter):
            letter = letter.upper()
            idx = 0
            for ch in letter:
                idx = idx * 26 + (ord(ch) - ord('A') + 1)
            return idx - 1
        idx = col_letter_to_index(key)
        return df.columns[idx]
    return key                                    

def _tipo_to_letter(v):
    """
    1=A, 6=B, 11=C. Si no se puede extraer código, cae a heurístico textual.
    """
    import re
    s = "" if pd.isna(v) else str(v).strip().upper()
    # intenta extraer el primer número (e.g., "11 - FACTURA C")
    m = re.search(r"\d+", s)
    if m:
        code = int(m.group(0))
        M = {1: "A", 6: "B", 11: "C"}  # extendible: 3/8/13 = NC, 2/7/12 = ND, etc.
        if code in M:
            return M[code]

    # fallback heurístico (por si el archivo viene sin número)
    if "FACTURA A" in s or s.endswith(" A") or s == "A":
        return "A"
    if "FACTURA B" in s or s.endswith(" B") or s == "B":
        return "B"
    if "FACTURA C" in s or s.endswith(" C") or s == "C":
        return "C"
    for ch in ("A", "B", "C"):
        if ch in s:
            return ch
    return "A"

def _normalize_ncomp(x):
    # quita espacios y asegura mayúsculas
    s = "" if pd.isna(x) else str(x).strip().upper()
    # elimina TODOS los espacios internos por si vienen como "C 00002 00000916"
    return re.sub(r"\s+", "", s)


def _to_int_safe(v):
    if pd.isna(v):
        return 0
    s = str(v).strip().replace(".", "").replace(",", ".")
    try:
        return int(float(s))
    except:
        return 0

def _build_ncomp_from_parts(tipo, pv, num, pattern):
    letter = _tipo_to_letter(tipo)
    pv_i   = _to_int_safe(pv)
    num_i  = _to_int_safe(num)
    return pattern.format(letter=letter, pv=pv_i, num=num_i)

def load_afip_with_map(path: str, sheet: str, mp: dict) -> pd.DataFrame:
    # En AFIP la primera fila es un comprobante en texto: los encabezados reales están en la segunda fila
    df = pd.read_excel(path, sheet_name=sheet, header=1)
    amap = mp["afip"]

    c_tipo = _resolve_col(df, amap["tipo"])
    c_pv   = _resolve_col(df, amap["pv"])
    c_num  = _resolve_col(df, amap["num"])
    pattern = amap.get("build_pattern", "{letter}{pv:04d}{num:08d}")
    df["N_COMP"] = df.apply(lambda r: _build_ncomp_from_parts(
        r.get(c_tipo), r.get(c_pv), r.get(c_num), pattern
    ), axis=1)
    df["N_COMP"] = df["N_COMP"].map(_normalize_ncomp)

    # CUIT AFIP (G)
    c_cuit = _resolve_col(df, amap.get("cuit"))
    ident = df[c_cuit].map(_normalize_cuit) if c_cuit in df.columns else pd.NA
    
    # Tipo de cambio (I)
    c_tc = _resolve_col(df, amap.get("exchange_rate"))
    if c_tc and c_tc in df.columns:
        tc = df[c_tc].map(_to_number_locale).fillna(1.0)
    else:
        tc = 1.0

    # Importes AFIP: neto=K, exento=L, iva=N, total=O
    mi = amap.get("importes", {})
    def take_num(colkey):
        ck = _resolve_col(df, mi.get(colkey))
        return df[ck].map(_to_number_locale) if ck in df.columns else pd.NA

    out = pd.DataFrame()
    out["N_COMP"]     = df["N_COMP"]
    out["IDENTIFTRI"] = ident
    out["TC"]         = tc
    out["IMP_EXENTO"] = take_num("exento")
    out["IMP_NETO"]   = take_num("neto")
    out["IMP_IVA"]    = take_num("iva")
    out["IMP_TOTAL"]  = take_num("total")
    return out

def load_tango_with_map(path: str, sheet: str, mp: dict) -> pd.DataFrame:
    df = pd.read_excel(path, sheet_name=sheet, header=0)
    tmap = mp["tango"]

    c_ncomp = tmap["n_comp_column"]
    df["N_COMP"] = df[c_ncomp].map(_normalize_ncomp)

    c_cuit = tmap.get("cuit", "IDENTIFTRI")
    mi     = tmap.get("importes", {})

    out = pd.DataFrame()
    out["N_COMP"]     = df["N_COMP"]
    out["IDENTIFTRI"] = df[c_cuit].map(_normalize_cuit) if c_cuit in df.columns else pd.NA
    def take_num(colname):
        return df[colname].map(_to_number_locale) if colname in df.columns else pd.NA

    out["IMP_EXENTO"] = take_num(mi.get("exento", "IMP_EXENTO"))
    out["IMP_NETO"]   = take_num(mi.get("neto",   "IMP_NETO"))
    out["IMP_IVA"]    = take_num(mi.get("iva",    "IMP_IVA"))
    out["IMP_TOTAL"]  = take_num(mi.get("total",  "IMP_TOTAL"))

    # Agrupar por N_COMP y CUIT, ya que una misma factura puede estar dividida en varias filas
    grouped = (
        out.groupby(["N_COMP", "IDENTIFTRI"], dropna=False)[
            ["IMP_EXENTO", "IMP_NETO", "IMP_IVA", "IMP_TOTAL"]
        ]
        .sum(min_count=1)
        .reset_index()
    )
    return grouped
