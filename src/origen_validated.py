from openpyxl import load_workbook
from openpyxl.styles import Font, PatternFill

from src.compare import STATUS_DIFFERENT, STATUS_INVALID, STATUS_MATCH, STATUS_MISSING_ODOO


FILLS = {
    STATUS_MATCH: PatternFill("solid", fgColor="C8E6C9"),
    STATUS_DIFFERENT: PatternFill("solid", fgColor="FFCDD2"),
    STATUS_MISSING_ODOO: PatternFill("solid", fgColor="FFF59D"),
    STATUS_INVALID: PatternFill("solid", fgColor="FFCC80"),
}


def write_origen_validado(origen_path, sheet, mapping, reconciliation, out_path):
    """Copia el libro ARCA completo y agrega estado/detalle sin reconstruirlo."""
    workbook = load_workbook(origen_path)
    if sheet not in workbook.sheetnames:
        raise ValueError(f"No existe la hoja '{sheet}' en {origen_path}")
    worksheet = workbook[sheet]
    header_row = int(mapping["afip"].get("header_row", 2))
    status_column = worksheet.max_column + 1
    detail_column = status_column + 1
    worksheet.cell(header_row, status_column, "Estado_Validación").font = Font(bold=True)
    worksheet.cell(header_row, detail_column, "Detalle_Validación").font = Font(bold=True)

    row_results = {}
    for _, result in reconciliation.details.iterrows():
        for row_number in result.get("FILAS_ARCA", ()) or ():
            row_results[int(row_number)] = (result["ESTADO"], result["DETALLE"])
    if not reconciliation.issues.empty:
        for _, issue in reconciliation.issues[reconciliation.issues["FUENTE"] == "ARCA"].iterrows():
            row_results[int(issue["FILA_EXCEL"])] = (STATUS_INVALID, issue["MOTIVO"])

    for row_number, (status, detail) in row_results.items():
        worksheet.cell(row_number, status_column, status)
        worksheet.cell(row_number, detail_column, detail)
        fill = FILLS.get(status)
        if status.startswith("Falta en "):
            fill = FILLS[STATUS_MISSING_ODOO]
        if fill:
            worksheet.cell(row_number, status_column).fill = fill
            worksheet.cell(row_number, detail_column).fill = fill

    workbook.save(out_path)
