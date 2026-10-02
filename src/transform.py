import re
from dataclasses import dataclass
from numbers import Number

import pandas as pd


AMOUNT_COLUMNS = ("IMP_EXENTO", "IMP_NETO", "IMP_IVA", "IMP_TOTAL")
PESO_ALIASES = {"$", "ARS", "PES", "PESO", "PESOS"}


@dataclass
class LoadResult:
    records: pd.DataFrame
    issues: pd.DataFrame


def _empty_issues() -> pd.DataFrame:
    return pd.DataFrame(columns=["FUENTE", "FILA_EXCEL", "MOTIVO", "N_COMP", "CUIT"])


def _normalize_cuit(value):
    if pd.isna(value):
        return pd.NA
    if isinstance(value, Number):
        text = str(int(value))
    else:
        text = re.sub(r"\D+", "", str(value))
    return text if text else pd.NA


def _valid_cuit(value) -> str | None:
    normalized = _normalize_cuit(value)
    if pd.isna(normalized) or len(str(normalized)) != 11:
        return None
    return str(normalized)


def _parse_number(value, decimal_separator=None, thousands_separator=None):
    if pd.isna(value) or value == "":
        return pd.NA
    if isinstance(value, Number):
        return float(value)
    text = str(value).strip().replace(" ", "")
    if not text:
        return pd.NA

    if decimal_separator:
        if thousands_separator:
            text = text.replace(thousands_separator, "")
        text = text.replace(decimal_separator, ".")
    elif "," in text and "." in text:
        decimal = "," if text.rfind(",") > text.rfind(".") else "."
        thousands = "." if decimal == "," else ","
        text = text.replace(thousands, "").replace(decimal, ".")
    elif "," in text or "." in text:
        separator = "," if "," in text else "."
        decimals = len(text.rsplit(separator, 1)[1])
        text = text.replace(separator, "." if decimals in (1, 2) else "")
    try:
        return float(text)
    except (TypeError, ValueError):
        return pd.NA


def _to_number_locale(value):
    """Parser compatible para valores textuales españoles o ingleses."""
    return _parse_number(value)


def _excel_col_to_index(letter: str) -> int:
    index = 0
    for char in letter.upper():
        index = index * 26 + ord(char) - ord("A") + 1
    return index - 1


def _resolve_col(df, key):
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
    15: ("RE", "C"), 81: ("TF", "A"),
    201: ("FA", "A"), 206: ("FA", "B"), 211: ("FA", "C"),
    202: ("ND", "A"), 207: ("ND", "B"), 212: ("ND", "C"),
    203: ("NC", "A"), 208: ("NC", "B"), 213: ("NC", "C"),
}


def _tipo_to_doc_letter(value, *, strict=False):
    text = "" if pd.isna(value) else str(value).strip().upper()
    code_match = re.match(r"\s*(\d+)", text)
    if code_match:
        code = int(code_match.group(1))
        if code in _DOC_CODES:
            return _DOC_CODES[code]
        if strict:
            raise ValueError(f"tipo de comprobante no soportado: {value}")

    doc_type = None
    if "CRÉDITO" in text or "CREDITO" in text or text.startswith("NC"):
        doc_type = "NC"
    elif "DÉBITO" in text or "DEBITO" in text or text.startswith("ND"):
        doc_type = "ND"
    elif "FACTURA" in text or text.startswith(("FA", "FC")):
        doc_type = "FA"
    letter_match = re.search(r"(?:^|[\s-])([ABC])(?:$|[\s-])", text)
    if doc_type and letter_match:
        return doc_type, letter_match.group(1)
    if strict:
        raise ValueError(f"tipo de comprobante no reconocido: {value}")
    return "FA", letter_match.group(1) if letter_match else "A"


def _normalize_ncomp(value):
    text = "" if pd.isna(value) else re.sub(r"\s+", "", str(value).strip().upper())
    match = re.fullmatch(r"(FA|FC|NC|ND|RE|TF)?-?([ABC])-?(\d+)-(\d+)", text)
    if match:
        doc_type = "FA" if match.group(1) in (None, "FC") else match.group(1)
        pv, number = int(match.group(3)), int(match.group(4))
        if 1 <= pv <= 99999 and 1 <= number <= 99999999:
            return f"{doc_type}-{match.group(2)}{pv:05d}-{number:08d}"
        return ""
    match = re.fullmatch(r"(FA|FC|NC|ND|RE|TF)?-?([ABC])(\d{4,5})(\d{8})", text)
    if match:
        doc_type = "FA" if match.group(1) in (None, "FC") else match.group(1)
        pv, number = int(match.group(3)), int(match.group(4))
        if pv and number:
            return f"{doc_type}-{match.group(2)}{pv:05d}-{number:08d}"
    return ""


def _invoice_letter(ncomp) -> str:
    match = re.search(r"-([ABC])", str(ncomp or "").upper())
    return match.group(1) if match else ""


def _strict_positive_int(value, label):
    if pd.isna(value):
        raise ValueError(f"{label} vacío")
    if isinstance(value, Number):
        numeric = float(value)
    else:
        try:
            numeric = float(str(value).strip().replace(",", "."))
        except ValueError as error:
            raise ValueError(f"{label} inválido: {value}") from error
    if not numeric.is_integer() or numeric <= 0:
        raise ValueError(f"{label} inválido: {value}")
    return int(numeric)


def _build_ncomp_from_parts(tipo, pv, num, pattern):
    doc_type, letter = _tipo_to_doc_letter(tipo, strict=True)
    pv_int = _strict_positive_int(pv, "punto de venta")
    number_int = _strict_positive_int(num, "número")
    if pv_int > 99999 or number_int > 99999999:
        raise ValueError("punto de venta o número fuera de rango")
    return _normalize_ncomp(pattern.format(
        doc_type=doc_type, letter=letter, pv=pv_int, num=number_int
    ))


def _header_index(mapping: dict, default_excel_row: int) -> int:
    return int(mapping.get("header_row", default_excel_row)) - 1


def _as_list(spec) -> list:
    if spec is None:
        return []
    return list(spec) if isinstance(spec, (list, tuple)) else [spec]


def _require_column(df, key, source):
    column = _resolve_col(df, key)
    if column not in df.columns:
        raise KeyError(f"No se encontró la columna requerida de {source} '{key}'.")
    return column


def _amount_from_row(row, df, spec, number_cfg, *, optional_missing=False):
    values = []
    for key in _as_list(spec):
        column = _resolve_col(df, key)
        if column not in df.columns:
            if optional_missing:
                continue
            raise KeyError(f"No se encontró la columna requerida '{key}'.")
        value = _parse_number(row[column], **number_cfg)
        if not pd.isna(row[column]) and row[column] != "" and pd.isna(value):
            raise ValueError(f"importe inválido en '{key}': {row[column]}")
        values.append(value)
    present = [float(value) for value in values if not pd.isna(value)]
    return sum(present) if present else pd.NA


def _issue(source, row_number, reason, ncomp="", cuit=""):
    return {
        "FUENTE": source,
        "FILA_EXCEL": row_number,
        "MOTIVO": reason,
        "N_COMP": ncomp,
        "CUIT": cuit,
    }


def load_afip_result(path: str, sheet: str, mp: dict) -> LoadResult:
    amap = mp["afip"]
    header_index = _header_index(amap, 2)
    df = pd.read_excel(path, sheet_name=sheet, header=header_index)
    c_tipo = _require_column(df, amap["tipo"], "ARCA")
    c_pv = _require_column(df, amap["pv"], "ARCA")
    c_num = _require_column(df, amap["num"], "ARCA")
    c_cuit = _require_column(df, amap["cuit"], "ARCA")
    c_date = _require_column(df, amap.get("date", "Fecha"), "ARCA")
    c_currency = _require_column(df, amap.get("currency", "Moneda"), "ARCA")
    c_tc = _require_column(df, amap.get("exchange_rate", "Tipo Cambio"), "ARCA")
    amounts = amap.get("importes", {})
    pattern = amap.get("build_pattern", "{doc_type}-{letter}{pv:05d}{num:08d}")
    number_cfg = {
        "decimal_separator": amap.get("decimal_separator"),
        "thousands_separator": amap.get("thousands_separator"),
    }
    records, issues = [], []
    for index, row in df.iterrows():
        excel_row = int(index) + header_index + 2
        ncomp, cuit = "", _valid_cuit(row[c_cuit])
        try:
            ncomp = _build_ncomp_from_parts(row[c_tipo], row[c_pv], row[c_num], pattern)
            if not cuit:
                raise ValueError(f"CUIT inválido: {row[c_cuit]}")
            date = pd.to_datetime(row[c_date], dayfirst=True, errors="coerce")
            if pd.isna(date):
                raise ValueError(f"fecha inválida: {row[c_date]}")
            currency = str(row[c_currency]).strip().upper() if not pd.isna(row[c_currency]) else ""
            if not currency:
                raise ValueError("moneda vacía")
            tc_raw = _parse_number(row[c_tc], **number_cfg)
            if currency in PESO_ALIASES:
                currency, tc = "ARS", 1.0
            elif pd.isna(tc_raw) or float(tc_raw) <= 0:
                raise ValueError(f"tipo de cambio inválido para {currency}: {row[c_tc]}")
            else:
                tc = float(tc_raw)
            record = {
                "FUENTE": "ARCA", "FILA_EXCEL": excel_row, "FILAS_EXCEL": (excel_row,),
                "FECHA": date.normalize(), "MONEDA": currency, "N_COMP": ncomp,
                "IDENTIFTRI": cuit, "TC": tc,
            }
            record.update({
                "IMP_EXENTO": _amount_from_row(row, df, amounts.get("exento"), number_cfg),
                "IMP_NETO": _amount_from_row(row, df, amounts.get("neto"), number_cfg),
                "IMP_IVA": _amount_from_row(row, df, amounts.get("iva"), number_cfg),
                "IMP_TOTAL": _amount_from_row(row, df, amounts.get("total"), number_cfg),
            })
            if pd.isna(record["IMP_TOTAL"]):
                raise ValueError("importe total vacío")
            if ncomp.startswith("NC-"):
                for column in AMOUNT_COLUMNS:
                    if not pd.isna(record[column]):
                        record[column] *= -1
            records.append(record)
        except (KeyError, ValueError) as error:
            issues.append(_issue("ARCA", excel_row, str(error), ncomp, cuit or ""))

    records_df = pd.DataFrame(records)
    if not records_df.empty:
        duplicate_mask = records_df.duplicated(["N_COMP", "IDENTIFTRI"], keep=False)
        for _, duplicate in records_df[duplicate_mask].iterrows():
            issues.append(_issue(
                "ARCA", duplicate["FILA_EXCEL"], "clave de comprobante duplicada",
                duplicate["N_COMP"], duplicate["IDENTIFTRI"],
            ))
        records_df = records_df[~duplicate_mask].reset_index(drop=True)
    return LoadResult(records_df, pd.DataFrame(issues) if issues else _empty_issues())


def load_odoo_result(path: str, sheet: str, mp: dict) -> LoadResult:
    omap = mp.get("odoo") or mp.get("tango")
    if not omap:
        raise KeyError("Falta 'mapping.odoo' en config.yaml.")
    header_index = _header_index(omap, 3)
    df = pd.read_excel(path, sheet_name=sheet, header=header_index)
    c_ncomp = _require_column(df, omap["n_comp_column"], "Odoo")
    c_cuit = _require_column(df, omap.get("cuit", "CUIT"), "Odoo")
    c_date = _require_column(df, omap.get("date", "Fecha"), "Odoo")
    amounts = omap.get("importes", {})
    number_cfg = {
        "decimal_separator": omap.get("decimal_separator"),
        "thousands_separator": omap.get("thousands_separator"),
    }
    records, issues = [], []
    for index, row in df.iterrows():
        excel_row = int(index) + header_index + 2
        raw_ncomp = row[c_ncomp]
        if str(raw_ncomp).strip().casefold() in {"total", "totales"}:
            continue
        ncomp = _normalize_ncomp(raw_ncomp)
        cuit = _valid_cuit(row[c_cuit])
        try:
            if not ncomp:
                raise ValueError(f"número de comprobante inválido: {raw_ncomp}")
            if not cuit:
                raise ValueError(f"CUIT inválido: {row[c_cuit]}")
            date = pd.to_datetime(row[c_date], dayfirst=True, errors="coerce")
            if pd.isna(date):
                raise ValueError(f"fecha inválida: {row[c_date]}")
            record = {
                "FUENTE": "ODOO", "FILA_EXCEL": excel_row, "FILAS_EXCEL": (excel_row,),
                "FECHA": date.normalize(), "MONEDA": "ARS", "N_COMP": ncomp,
                "IDENTIFTRI": cuit, "TC": 1.0,
            }
            record.update({
                "IMP_EXENTO": _amount_from_row(row, df, amounts.get("exento"), number_cfg, optional_missing=True),
                "IMP_NETO": _amount_from_row(row, df, amounts.get("neto"), number_cfg),
                "IMP_IVA": _amount_from_row(row, df, amounts.get("iva"), number_cfg, optional_missing=True),
                "IMP_TOTAL": _amount_from_row(row, df, amounts.get("total"), number_cfg),
            })
            if pd.isna(record["IMP_TOTAL"]):
                raise ValueError("importe total vacío")
            records.append(record)
        except (KeyError, ValueError) as error:
            issues.append(_issue("ODOO", excel_row, str(error), ncomp, cuit or ""))

    records_df = pd.DataFrame(records)
    if not records_df.empty:
        grouped = []
        for (_, _), group in records_df.groupby(["N_COMP", "IDENTIFTRI"], sort=False):
            first = group.iloc[0].to_dict()
            first["FILA_EXCEL"] = int(group["FILA_EXCEL"].min())
            first["FILAS_EXCEL"] = tuple(int(value) for value in group["FILA_EXCEL"])
            if group["FECHA"].nunique() > 1:
                for row_number in first["FILAS_EXCEL"]:
                    issues.append(_issue(
                        "ODOO", row_number, "misma clave con fechas diferentes",
                        first["N_COMP"], first["IDENTIFTRI"],
                    ))
                continue
            for column in AMOUNT_COLUMNS:
                first[column] = group[column].sum(min_count=1)
            grouped.append(first)
        records_df = pd.DataFrame(grouped)
    return LoadResult(records_df.reset_index(drop=True), pd.DataFrame(issues) if issues else _empty_issues())


def load_afip_with_map(path: str, sheet: str, mp: dict) -> pd.DataFrame:
    return load_afip_result(path, sheet, mp).records


def load_odoo_with_map(path: str, sheet: str, mp: dict) -> pd.DataFrame:
    return load_odoo_result(path, sheet, mp).records


def load_tango_with_map(path: str, sheet: str, mp: dict) -> pd.DataFrame:
    """Alias obsoleto conservado temporalmente para integraciones externas."""
    return load_odoo_with_map(path, sheet, mp)
