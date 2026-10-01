from datetime import datetime
from pathlib import Path

import pandas as pd
from openpyxl import load_workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import column_index_from_string

from src.transform import (
    _as_list,
    _invoice_letter,
    _normalize_cuit,
    _normalize_ncomp,
    _to_number_locale,
)


YELLOW = PatternFill(start_color="FFF59D", end_color="FFF59D", fill_type="solid")


def _is_number(value):
    return isinstance(value, (int, float)) and not pd.isna(value)


def _column_indexes(worksheet, spec, header_row, *, optional=False):
    header = {
        str(worksheet.cell(header_row, column).value).strip(): column
        for column in range(1, worksheet.max_column + 1)
        if worksheet.cell(header_row, column).value is not None
    }
    indexes = []
    for key in _as_list(spec):
        text = str(key).strip()
        if text in header:
            indexes.append(header[text])
        elif len(text) <= 3 and text.isalpha():
            indexes.append(column_index_from_string(text.upper()))
        elif not optional:
            raise KeyError(f"En la hoja '{worksheet.title}' falta la columna '{text}'.")
    return indexes


def _aggregate_cells(worksheet, rows, columns):
    values = []
    for row in rows:
        for column in columns:
            value = _to_number_locale(worksheet.cell(row=row, column=column).value)
            if _is_number(value):
                values.append(float(value))
    return sum(values) if values else pd.NA


def _mark_cell(cell):
    cell.fill = YELLOW
    cell.font = Font(
        name=cell.font.name,
        size=cell.font.sz,
        bold=True,
        italic=cell.font.italic,
        underline="single",
        color=cell.font.color,
    )


def mark_and_append(
    origen_df: pd.DataFrame,
    destino_xlsx_path: str,
    destino_sheet: str,
    columns_cfg: list,
    out_path: str,
    mapping: dict,
):
    """Marca en amarillo los importes de Odoo que difieren de ARCA."""
    try:
        workbook = load_workbook(destino_xlsx_path)
    except PermissionError as error:
        raise PermissionError(
            f"No se pudo abrir '{destino_xlsx_path}'. Cerrá el archivo si está abierto en Excel."
        ) from error

    if destino_sheet not in workbook.sheetnames:
        raise ValueError(f"No existe la hoja '{destino_sheet}' en {destino_xlsx_path}")
    worksheet = workbook[destino_sheet]
    omap = mapping.get("odoo") or mapping.get("tango")
    header_row = int(omap.get("header_row", 3))

    ncomp_column = _column_indexes(worksheet, omap["n_comp_column"], header_row)[0]
    cuit_column = _column_indexes(worksheet, omap.get("cuit", "CUIT"), header_row)[0]
    amount_mapping = omap.get("importes", {})
    field_specs = {
        "IMP_EXENTO": amount_mapping.get("exento"),
        "IMP_NETO": amount_mapping.get("neto"),
        "IMP_IVA": amount_mapping.get("iva"),
        "IMP_TOTAL": amount_mapping.get("total"),
    }
    field_columns = {
        field: _column_indexes(worksheet, spec, header_row, optional=True)
        for field, spec in field_specs.items()
    }

    key_to_rows = {}
    for row_number in range(header_row + 1, worksheet.max_row + 1):
        ncomp = _normalize_ncomp(worksheet.cell(row_number, ncomp_column).value)
        cuit = _normalize_cuit(worksheet.cell(row_number, cuit_column).value)
        cuit = "" if pd.isna(cuit) else str(cuit)
        if ncomp:
            key_to_rows.setdefault((ncomp, cuit), []).append(row_number)

    tolerance_by_field = {
        column["name"]: float(column.get("tolerance", 0.0)) for column in columns_cfg
    }
    missing_count = 0
    for _, source_row in origen_df.iterrows():
        ncomp = _normalize_ncomp(source_row["N_COMP"])
        cuit = _normalize_cuit(source_row["IDENTIFTRI"])
        rows = key_to_rows.get((ncomp, "" if pd.isna(cuit) else str(cuit)), [])
        if not rows:
            missing_count += 1
            continue

        fields = ["IMP_TOTAL"] if _invoice_letter(ncomp) in ("B", "C") else list(field_specs)
        tc = _to_number_locale(source_row.get("TC", 1.0))
        tc = float(tc) if _is_number(tc) else 1.0
        for field in fields:
            target = _aggregate_cells(worksheet, rows, field_columns[field])
            source = _to_number_locale(source_row[field])
            source = source * tc if _is_number(source) else source
            matches = (pd.isna(source) and pd.isna(target)) or (
                _is_number(source)
                and _is_number(target)
                and abs(source - target) <= tolerance_by_field.get(field, 0.0) + 1e-9
            )
            if not matches:
                for row_number in rows:
                    for column_number in field_columns[field]:
                        _mark_cell(worksheet.cell(row=row_number, column=column_number))

    output = Path(out_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        workbook.save(output)
    except PermissionError:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output = output.with_name(f"{output.stem}_{stamp}{output.suffix}")
        workbook.save(output)
    return missing_count, str(output)
