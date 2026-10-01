import re
from numbers import Number

import pandas as pd


def _normalize_cuit(x):
    if pd.isna(x):
        return pd.NA
    value = re.sub(r"\D+", "", str(x))
    return value if value else pd.NA


def _normalize_name(x):
    return "" if pd.isna(x) else str(x).strip().upper()


def _to_number_locale(x):
    if pd.isna(x) or x == "":
        return pd.NA
    if isinstance(x, (int, float)):
        return float(x)
    value = str(x).strip().replace(".", "").replace(",", ".")
    try:
        return float(value)
    except (TypeError, ValueError):
        return pd.NA


def _excel_col_to_index(letter: str) -> int:
    index = 0
    for char in letter.upper():
        index = index * 26 + ord(char) - ord("A") + 1
    return index - 1


def _resolve_col(df, key):
    """Resuelve primero por encabezado y luego por letra de columna Excel."""
    if key is None:
        return None
    key = str(key).strip()
    if key in df.columns:
        return key
    if len(key) <= 3 and key.isalpha():
        index = _excel_col_to_index(key)
        if index < len(df.columns):
            return df.columns[index]
    return key


_DOC_CODES = {
    1: ("FA", "A"), 6: ("FA", "B"), 11: ("FA", "C"),
    2: ("ND", "A"), 7: ("ND", "B"), 12: ("ND", "C"),
    3: ("NC", "A"), 8: ("NC", "B"), 13: ("NC", "C"),
    201: ("FA", "A"), 206: ("FA", "B"), 211: ("FA", "C"),
    202: ("ND", "A"), 207: ("ND", "B"), 212: ("ND", "C"),
    203: ("NC", "A"), 208: ("NC", "B"), 213: ("NC", "C"),
}


def _tipo_to_doc_letter(value):
    text = "" if pd.isna(value) else str(value).strip().upper()
    match = re.search(r"\d+", text)
    if match and int(match.group(0)) in _DOC_CODES:
        return _DOC_CODES[int(match.group(0))]

    doc_type = "NC" if ("CRÉDITO" in text or "CREDITO" in text or text.startswith("NC")) else (
        "ND" if ("DÉBITO" in text or "DEBITO" in text or text.startswith("ND")) else "FA"
    )
    letter_match = re.search(r"(?:^|[\s-])([ABC])(?:$|[\s-])", text)
    return doc_type, letter_match.group(1) if letter_match else "A"


def _tipo_to_letter(value):
    """Compatibilidad con el código anterior."""
    return _tipo_to_doc_letter(value)[1]


def _normalize_ncomp(value):
    """Convierte formatos de ARCA y Odoo a ``FA-A00001-00001822``."""
    text = "" if pd.isna(value) else re.sub(r"\s+", "", str(value).strip().upper())
    match = re.fullmatch(r"(FA|FC|NC|ND)?-?([ABC])-?(\d+)-(\d+)", text)
    if match:
        doc_type = "FA" if match.group(1) in (None, "FC") else match.group(1)
        return f"{doc_type}-{match.group(2)}{int(match.group(3)):05d}-{int(match.group(4)):08d}"

    # Formato construido por ARCA o usado por el validador anterior, sin guion
    # entre punto de venta y número. Los últimos ocho dígitos son el número.
    match = re.fullmatch(r"(FA|FC|NC|ND)?-?([ABC])(\d{4,5})(\d{8})", text)
    if match:
        doc_type = "FA" if match.group(1) in (None, "FC") else match.group(1)
        return f"{doc_type}-{match.group(2)}{int(match.group(3)):05d}-{int(match.group(4)):08d}"
    return text


def _invoice_letter(ncomp) -> str:
    match = re.search(r"-([ABC])", str(ncomp or "").upper())
    return match.group(1) if match else ""


def _to_int_safe(value):
    if pd.isna(value):
        return 0
    if isinstance(value, Number):
        return int(value)
    text = str(value).strip().replace(".", "").replace(",", ".")
    try:
        return int(float(text))
    except (TypeError, ValueError):
        return 0


def _build_ncomp_from_parts(tipo, pv, num, pattern):
    doc_type, letter = _tipo_to_doc_letter(tipo)
    result = pattern.format(
        doc_type=doc_type,
        letter=letter,
        pv=_to_int_safe(pv),
        num=_to_int_safe(num),
    )
    return _normalize_ncomp(result)


def _header_index(mapping: dict, default_excel_row: int) -> int:
    return int(mapping.get("header_row", default_excel_row)) - 1


def _as_list(spec) -> list:
    if spec is None:
        return []
    return list(spec) if isinstance(spec, (list, tuple)) else [spec]


def _take_amount(df: pd.DataFrame, spec, *, optional_missing=False) -> pd.Series:
    values = []
    for key in _as_list(spec):
        column = _resolve_col(df, key)
        if column not in df.columns:
            if optional_missing:
                continue
            raise KeyError(f"No se encontró la columna requerida '{key}'.")
        values.append(df[column].map(_to_number_locale))
    if not values:
        return pd.Series(pd.NA, index=df.index, dtype="object")
    return pd.concat(values, axis=1).sum(axis=1, min_count=1)


def load_afip_with_map(path: str, sheet: str, mp: dict) -> pd.DataFrame:
    amap = mp["afip"]
    df = pd.read_excel(path, sheet_name=sheet, header=_header_index(amap, 2))

    c_tipo = _resolve_col(df, amap["tipo"])
    c_pv = _resolve_col(df, amap["pv"])
    c_num = _resolve_col(df, amap["num"])
    for configured, column in ((amap["tipo"], c_tipo), (amap["pv"], c_pv), (amap["num"], c_num)):
        if column not in df.columns:
            raise KeyError(f"No se encontró la columna requerida de ARCA '{configured}'.")

    pattern = amap.get("build_pattern", "{doc_type}-{letter}{pv:05d}{num:08d}")
    ncomp = df.apply(
        lambda row: _build_ncomp_from_parts(row[c_tipo], row[c_pv], row[c_num], pattern), axis=1
    )
    c_cuit = _resolve_col(df, amap.get("cuit"))
    if c_cuit not in df.columns:
        raise KeyError(f"No se encontró la columna de CUIT de ARCA '{amap.get('cuit')}'.")

    c_tc = _resolve_col(df, amap.get("exchange_rate"))
    tc = df[c_tc].map(_to_number_locale).fillna(1.0) if c_tc in df.columns else 1.0
    amounts = amap.get("importes", {})

    out = pd.DataFrame(index=df.index)
    out["N_COMP"] = ncomp
    out["IDENTIFTRI"] = df[c_cuit].map(_normalize_cuit)
    out["TC"] = tc
    out["IMP_EXENTO"] = _take_amount(df, amounts.get("exento"))
    out["IMP_NETO"] = _take_amount(df, amounts.get("neto"))
    out["IMP_IVA"] = _take_amount(df, amounts.get("iva"))
    out["IMP_TOTAL"] = _take_amount(df, amounts.get("total"))

    # ARCA informa NC positivas; Odoo las contabiliza con signo negativo.
    credit_mask = out["N_COMP"].str.startswith("NC-")
    amount_columns = ["IMP_EXENTO", "IMP_NETO", "IMP_IVA", "IMP_TOTAL"]
    out.loc[credit_mask, amount_columns] = out.loc[credit_mask, amount_columns] * -1
    return out.reset_index(drop=True)


def load_odoo_with_map(path: str, sheet: str, mp: dict) -> pd.DataFrame:
    omap = mp.get("odoo") or mp.get("tango")
    if not omap:
        raise KeyError("Falta 'mapping.odoo' en config.yaml.")
    df = pd.read_excel(path, sheet_name=sheet, header=_header_index(omap, 3))

    c_ncomp = _resolve_col(df, omap["n_comp_column"])
    c_cuit = _resolve_col(df, omap.get("cuit", "CUIT"))
    for configured, column in ((omap["n_comp_column"], c_ncomp), (omap.get("cuit", "CUIT"), c_cuit)):
        if column not in df.columns:
            raise KeyError(f"No se encontró la columna requerida de Odoo '{configured}'.")

    amounts = omap.get("importes", {})
    out = pd.DataFrame(index=df.index)
    out["N_COMP"] = df[c_ncomp].map(_normalize_ncomp)
    out["IDENTIFTRI"] = df[c_cuit].map(_normalize_cuit)
    out["IMP_EXENTO"] = _take_amount(df, amounts.get("exento"), optional_missing=True)
    out["IMP_NETO"] = _take_amount(df, amounts.get("neto"))
    out["IMP_IVA"] = _take_amount(df, amounts.get("iva"), optional_missing=True)
    out["IMP_TOTAL"] = _take_amount(df, amounts.get("total"))

    out = out[out["N_COMP"].astype(str).str.len().gt(0)]
    return (
        out.groupby(["N_COMP", "IDENTIFTRI"], dropna=False)[
            ["IMP_EXENTO", "IMP_NETO", "IMP_IVA", "IMP_TOTAL"]
        ]
        .sum(min_count=1)
        .reset_index()
    )


def load_tango_with_map(path: str, sheet: str, mp: dict) -> pd.DataFrame:
    """Alias temporal para integraciones que usaban el nombre anterior."""
    return load_odoo_with_map(path, sheet, mp)
