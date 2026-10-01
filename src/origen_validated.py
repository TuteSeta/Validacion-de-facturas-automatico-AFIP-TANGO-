import pandas as pd
from openpyxl import load_workbook
from openpyxl.styles import PatternFill

from src.transform import _invoice_letter, _to_number_locale, load_afip_with_map


GREEN_FILL = PatternFill(start_color="C8E6C9", end_color="C8E6C9", fill_type="solid")
RED_FILL = PatternFill(start_color="FFCDD2", end_color="FFCDD2", fill_type="solid")
YELLOW_FILL = PatternFill(start_color="FFF59D", end_color="FFF59D", fill_type="solid")


def _is_number(value):
    return isinstance(value, (int, float)) and not pd.isna(value)


def _compute_status_series(origen_df: pd.DataFrame, destino_df: pd.DataFrame, tolerances: dict) -> pd.Series:
    merged = origen_df.merge(
        destino_df,
        on=["N_COMP", "IDENTIFTRI"],
        how="left",
        suffixes=("_origen", "_destino"),
        indicator=True,
    )
    status = []
    for _, row in merged.iterrows():
        if row["_merge"] == "left_only":
            status.append("Omitida")
            continue

        columns = ("IMP_TOTAL",) if _invoice_letter(row["N_COMP"]) in ("B", "C") else (
            "IMP_EXENTO", "IMP_NETO", "IMP_IVA", "IMP_TOTAL"
        )
        tc = _to_number_locale(row.get("TC", row.get("TC_origen", 1.0)))
        tc = float(tc) if _is_number(tc) else 1.0
        is_ok = True
        for name in columns:
            source = _to_number_locale(row.get(f"{name}_origen"))
            target = _to_number_locale(row.get(f"{name}_destino"))
            source = source * tc if _is_number(source) else source
            if pd.isna(source) and pd.isna(target):
                continue
            if not (
                _is_number(source)
                and _is_number(target)
                and abs(source - target) <= tolerances.get(name, 0) + 1e-9
            ):
                is_ok = False
                break
        status.append("Coincide" if is_ok else "No coincide")
    return pd.Series(status, index=origen_df.index)


def write_origen_validado(
    origen_path: str,
    sheet: str,
    mapping: dict,
    destino_df: pd.DataFrame,
    tolerances: dict,
    out_path: str,
):
    amap = mapping["afip"]
    header_index = int(amap.get("header_row", 2)) - 1
    full_df = pd.read_excel(origen_path, sheet_name=sheet, header=header_index)
    origen_df = load_afip_with_map(origen_path, sheet, mapping)
    estados = _compute_status_series(origen_df, destino_df, tolerances)

    export_df = full_df.copy()
    export_df["Estado_Validación"] = estados.values
    export_df.to_excel(out_path, sheet_name="ARCA validado", index=False)

    workbook = load_workbook(out_path)
    worksheet = workbook["ARCA validado"]
    status_column = worksheet.max_column
    for row_number in range(2, worksheet.max_row + 1):
        estado = worksheet.cell(row=row_number, column=status_column).value
        fill = GREEN_FILL if estado == "Coincide" else (RED_FILL if estado == "No coincide" else YELLOW_FILL)
        for column_number in range(1, worksheet.max_column + 1):
            worksheet.cell(row=row_number, column=column_number).fill = fill
    workbook.save(out_path)
