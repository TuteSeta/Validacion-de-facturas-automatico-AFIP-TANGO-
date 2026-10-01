from dataclasses import dataclass

import pandas as pd

from src.transform import AMOUNT_COLUMNS, _invoice_letter, _to_number_locale


STATUS_MATCH = "Coincide"
STATUS_DIFFERENT = "No coincide"
STATUS_MISSING_ODOO = "Falta en Odoo"
STATUS_MISSING_ARCA = "Falta en ARCA"
STATUS_INVALID = "Inválido"
STATUS_OUT_OF_PERIOD = "Fuera del período"


@dataclass
class ReconciliationResult:
    details: pd.DataFrame
    issues: pd.DataFrame
    out_of_period: pd.DataFrame
    period_start: pd.Timestamp
    period_end: pd.Timestamp

    @property
    def metrics(self):
        counts = self.details["ESTADO"].value_counts().to_dict()
        return {
            "coincidencias": int(counts.get(STATUS_MATCH, 0)),
            "diferencias": int(counts.get(STATUS_DIFFERENT, 0)),
            "faltantes_en_odoo": int(counts.get(STATUS_MISSING_ODOO, 0)),
            "faltantes_en_arca": int(counts.get(STATUS_MISSING_ARCA, 0)),
            "invalidos_arca": int((self.issues["FUENTE"] == "ARCA").sum()) if not self.issues.empty else 0,
            "invalidos_odoo": int((self.issues["FUENTE"] == "ODOO").sum()) if not self.issues.empty else 0,
            "fuera_periodo_odoo": int(sum(len(rows) for rows in self.out_of_period.get("FILAS_EXCEL", []))),
        }


def _is_number(value):
    parsed = _to_number_locale(value)
    return not pd.isna(parsed)


def _fmt_money(value) -> str:
    parsed = _to_number_locale(value)
    if pd.isna(parsed):
        return ""
    rendered = f"{float(parsed):,.2f}"
    return rendered.replace(",", "X").replace(".", ",").replace("X", ".")


def _comparison_fields(ncomp):
    return ("IMP_TOTAL",) if _invoice_letter(ncomp) in ("B", "C") else AMOUNT_COLUMNS


def _source_rows(value):
    return value if isinstance(value, (tuple, list)) else ()


def _detail_message(differences):
    labels = {
        "IMP_EXENTO": "Otros/exento",
        "IMP_NETO": "Neto",
        "IMP_IVA": "IVA",
        "IMP_TOTAL": "Total",
    }
    return "; ".join(
        f"{labels[field]}: ARCA {_fmt_money(source)} - Odoo {_fmt_money(target)}"
        for field, source, target in differences
    )


def reconcile(arca_result, odoo_result, tolerances) -> ReconciliationResult:
    arca = arca_result.records.copy()
    odoo = odoo_result.records.copy()
    if arca.empty:
        raise ValueError("ARCA no contiene filas válidas para determinar el período.")

    period_start = arca["FECHA"].min().normalize()
    period_end = arca["FECHA"].max().normalize()
    in_period_mask = odoo["FECHA"].between(period_start, period_end, inclusive="both")
    out_of_period = odoo[~in_period_mask].copy().reset_index(drop=True)
    odoo = odoo[in_period_mask].copy()

    merged = arca.merge(
        odoo,
        on=["N_COMP", "IDENTIFTRI"],
        how="outer",
        suffixes=("_ARCA", "_ODOO"),
        indicator=True,
    )
    rows = []
    for _, merged_row in merged.iterrows():
        ncomp = merged_row["N_COMP"]
        base = {
            "N_COMP": ncomp,
            "CUIT": merged_row["IDENTIFTRI"],
            "FECHA_ARCA": merged_row.get("FECHA_ARCA"),
            "FECHA_ODOO": merged_row.get("FECHA_ODOO"),
            "FILAS_ARCA": _source_rows(merged_row.get("FILAS_EXCEL_ARCA")),
            "FILAS_ODOO": _source_rows(merged_row.get("FILAS_EXCEL_ODOO")),
            "CAMPOS_DIFERENTES": "",
        }
        merge_status = merged_row["_merge"]
        if merge_status == "left_only":
            base.update(ESTADO=STATUS_MISSING_ODOO, DETALLE="El comprobante de ARCA no existe en Odoo.")
        elif merge_status == "right_only":
            base.update(ESTADO=STATUS_MISSING_ARCA, DETALLE="El comprobante de Odoo no existe en ARCA.")
        else:
            exchange_rate = _to_number_locale(merged_row.get("TC_ARCA", 1.0))
            exchange_rate = float(exchange_rate) if _is_number(exchange_rate) else 1.0
            differences = []
            for field in _comparison_fields(ncomp):
                source = _to_number_locale(merged_row.get(f"{field}_ARCA"))
                target = _to_number_locale(merged_row.get(f"{field}_ODOO"))
                source_adjusted = source * exchange_rate if _is_number(source) else source
                matches = (pd.isna(source_adjusted) and pd.isna(target)) or (
                    _is_number(source_adjusted)
                    and _is_number(target)
                    and abs(float(source_adjusted) - float(target))
                    <= float(tolerances.get(field, 0.0)) + 1e-9
                )
                if not matches:
                    differences.append((field, source_adjusted, target))
            if differences:
                base.update(
                    ESTADO=STATUS_DIFFERENT,
                    DETALLE=_detail_message(differences),
                    CAMPOS_DIFERENTES=", ".join(field for field, _, _ in differences),
                )
            else:
                base.update(ESTADO=STATUS_MATCH, DETALLE="Los importes coinciden.")

        for field in AMOUNT_COLUMNS:
            source = _to_number_locale(merged_row.get(f"{field}_ARCA"))
            tc = _to_number_locale(merged_row.get("TC_ARCA", 1.0))
            if _is_number(source) and _is_number(tc):
                source = float(source) * float(tc)
            target = _to_number_locale(merged_row.get(f"{field}_ODOO"))
            base[f"{field}_ARCA"] = source
            base[f"{field}_ODOO"] = target
            base[f"{field}_DIF"] = (
                float(source) - float(target) if _is_number(source) and _is_number(target) else pd.NA
            )
        rows.append(base)

    issues = pd.concat([arca_result.issues, odoo_result.issues], ignore_index=True)
    return ReconciliationResult(
        details=pd.DataFrame(rows),
        issues=issues,
        out_of_period=out_of_period,
        period_start=period_start,
        period_end=period_end,
    )


def messages_from_result(result: ReconciliationResult) -> list[str]:
    icons = {
        STATUS_MATCH: "✅",
        STATUS_DIFFERENT: "❌",
        STATUS_MISSING_ODOO: "⚠️",
        STATUS_MISSING_ARCA: "⚠️",
    }
    messages = [
        f"{icons[row['ESTADO']]} Comprobante {row['N_COMP']}: {row['DETALLE']}"
        for _, row in result.details.iterrows()
    ]
    for _, issue in result.issues.iterrows():
        messages.append(
            f"⚠️ {issue['FUENTE']} fila {issue['FILA_EXCEL']}: {issue['MOTIVO']}"
        )
    return messages
