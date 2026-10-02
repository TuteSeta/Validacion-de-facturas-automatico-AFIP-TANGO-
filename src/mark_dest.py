from openpyxl import load_workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import column_index_from_string

from src.compare import (
    STATUS_DIFFERENT,
    STATUS_INVALID,
    STATUS_MATCH,
    STATUS_MISSING_ARCA,
    STATUS_OUT_OF_PERIOD,
)
from src.transform import _as_list


FILLS = {
    STATUS_MATCH: PatternFill("solid", fgColor="C8E6C9"),
    STATUS_DIFFERENT: PatternFill("solid", fgColor="FFCDD2"),
    STATUS_MISSING_ARCA: PatternFill("solid", fgColor="FFF59D"),
    STATUS_INVALID: PatternFill("solid", fgColor="FFCC80"),
    STATUS_OUT_OF_PERIOD: PatternFill("solid", fgColor="D9E1F2"),
}


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


def write_destino_validado(destino_path, sheet, mapping, reconciliation, out_path, target_key="odoo"):
    """Copia el destino, agrega estados y resalta únicamente los importes diferentes."""
    workbook = load_workbook(destino_path)
    if sheet not in workbook.sheetnames:
        raise ValueError(f"No existe la hoja '{sheet}' en {destino_path}")
    worksheet = workbook[sheet]
    if target_key == "odoo":
        target_map = mapping.get("odoo") or mapping.get("tango")
    else:
        target_map = mapping.get(target_key)
    if not target_map:
        raise KeyError(f"Falta 'mapping.{target_key}' en config.yaml.")
    header_row = int(target_map.get("header_row", 3))
    status_column = worksheet.max_column + 1
    detail_column = status_column + 1
    worksheet.cell(header_row, status_column, "Estado_Validación").font = Font(bold=True)
    worksheet.cell(header_row, detail_column, "Detalle_Validación").font = Font(bold=True)

    field_specs = {
        "IMP_EXENTO": target_map.get("importes", {}).get("exento"),
        "IMP_NETO": target_map.get("importes", {}).get("neto"),
        "IMP_IVA": target_map.get("importes", {}).get("iva"),
        "IMP_TOTAL": target_map.get("importes", {}).get("total"),
    }
    field_columns = {
        field: _column_indexes(worksheet, spec, header_row, optional=True)
        for field, spec in field_specs.items()
    }

    row_results = {}
    for _, result in reconciliation.details.iterrows():
        for row_number in result.get("FILAS_DESTINO", ()) or ():
            row_results[int(row_number)] = (
                result["ESTADO"], result["DETALLE"], result["CAMPOS_DIFERENTES"]
            )
    for _, record in reconciliation.out_of_period.iterrows():
        detail = (
            f"Fecha fuera del rango ARCA "
            f"{reconciliation.period_start:%d/%m/%Y}–{reconciliation.period_end:%d/%m/%Y}."
        )
        for row_number in record["FILAS_EXCEL"]:
            row_results[int(row_number)] = (STATUS_OUT_OF_PERIOD, detail, "")
    if not reconciliation.issues.empty:
        source_name = reconciliation.target_name.upper()
        for _, issue in reconciliation.issues[reconciliation.issues["FUENTE"] == source_name].iterrows():
            row_results[int(issue["FILA_EXCEL"])] = (STATUS_INVALID, issue["MOTIVO"], "")

    for row_number, (status, detail, different_fields) in row_results.items():
        worksheet.cell(row_number, status_column, status)
        worksheet.cell(row_number, detail_column, detail)
        fill = FILLS.get(status)
        if status.startswith("Falta en "):
            fill = FILLS[STATUS_MISSING_ARCA]
        if fill:
            worksheet.cell(row_number, status_column).fill = fill
            worksheet.cell(row_number, detail_column).fill = fill
        if status == STATUS_DIFFERENT:
            fields = (value.strip() for value in different_fields.split(","))
            for field in filter(None, fields):
                for column_number in field_columns.get(field, []):
                    worksheet.cell(row_number, column_number).fill = FILLS[STATUS_DIFFERENT]
                    worksheet.cell(row_number, column_number).font = Font(bold=True, underline="single")

    workbook.save(out_path)


def write_odoo_validado(destino_path, sheet, mapping, reconciliation, out_path):
    """Alias compatible con integraciones anteriores."""
    return write_destino_validado(
        destino_path, sheet, mapping, reconciliation, out_path, target_key="odoo"
    )
