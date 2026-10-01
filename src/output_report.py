import pandas as pd
from openpyxl import load_workbook
from openpyxl.styles import Font, PatternFill


def _excel_safe(frame):
    output = frame.copy()
    for column in output.columns:
        output[column] = output[column].map(
            lambda value: ", ".join(map(str, value)) if isinstance(value, (tuple, list)) else value
        )
    return output


def write_consolidated_report(path, reconciliation, source_names):
    metrics = reconciliation.metrics
    summary = pd.DataFrame([
        ("Archivo ARCA", source_names["arca"]),
        ("Archivo Odoo", source_names["odoo"]),
        ("Período desde", reconciliation.period_start.strftime("%d/%m/%Y")),
        ("Período hasta", reconciliation.period_end.strftime("%d/%m/%Y")),
        ("Coincidencias", metrics["coincidencias"]),
        ("Diferencias", metrics["diferencias"]),
        ("Faltantes en Odoo", metrics["faltantes_en_odoo"]),
        ("Faltantes en ARCA", metrics["faltantes_en_arca"]),
        ("Inválidos ARCA", metrics["invalidos_arca"]),
        ("Inválidos Odoo", metrics["invalidos_odoo"]),
        ("Filas Odoo fuera del período", metrics["fuera_periodo_odoo"]),
    ], columns=["Concepto", "Valor"])

    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        summary.to_excel(writer, sheet_name="Resumen", index=False)
        _excel_safe(reconciliation.details).to_excel(
            writer, sheet_name="Conciliación", index=False
        )
        _excel_safe(reconciliation.issues).to_excel(
            writer, sheet_name="Incidencias", index=False
        )
        _excel_safe(reconciliation.out_of_period).to_excel(
            writer, sheet_name="Odoo fuera de período", index=False
        )

    workbook = load_workbook(path)
    header_fill = PatternFill("solid", fgColor="1F4E78")
    for worksheet in workbook.worksheets:
        worksheet.freeze_panes = "A2"
        worksheet.auto_filter.ref = worksheet.dimensions
        for cell in worksheet[1]:
            cell.fill = header_fill
            cell.font = Font(color="FFFFFF", bold=True)
        for column_cells in worksheet.columns:
            width = min(max(len(str(cell.value or "")) for cell in column_cells) + 2, 60)
            worksheet.column_dimensions[column_cells[0].column_letter].width = width
    workbook.save(path)
