# src/compare.py
import numpy as np
import pandas as pd
from typing import Dict, List

def _to_number_locale(x):
    if pd.isna(x) or x == "":
        return np.nan
    if isinstance(x, (int, float)):
        return float(x)
    s = str(x).strip().replace(".", "").replace(",", ".")
    try:
        return float(s)
    except Exception:
        return np.nan

def _coerce(value, kind):
    if pd.isna(value):
        return np.nan
    if kind == "number":
        return _to_number_locale(value)
    if kind == "date":
        try:
            return pd.to_datetime(value).date()
        except Exception:
            return np.nan
    # string
    return str(value).strip().upper()

def compare_columns(df_merged: pd.DataFrame, keys: list, columns_cfg: list) -> pd.DataFrame:
    results = df_merged.copy()
    for col in columns_cfg:
        name = col["name"]
        kind = col.get("type", "string")
        tol = float(col.get("tolerance", 0.0))

        a = results[f"{name}_origen"].map(lambda v: _coerce(v, kind))
        b = results[f"{name}_destino"].map(lambda v: _coerce(v, kind))

        if kind == "number":
            match = (pd.isna(a) & pd.isna(b)) | (np.abs(a - b) <= tol)
        else:
            match = (a.fillna("") == b.fillna(""))

        results[f"__match__{name}"] = match

    match_cols = [f"__match__{c['name']}" for c in columns_cfg]
    results["__row_ok__"] = results[match_cols].all(axis=1)
    return results

# -------- Mensajes por factura (según requerimiento) --------
def _fmt_money_es(v: float) -> str:
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return ""
    s = f"{v:,.2f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")

def _fmt_cuit_hyphen(cuit_digits: str) -> str:
    s = str(cuit_digits or "").strip()
    if len(s) == 11 and s.isdigit():
        return f"{s[0:2]}-{s[2:10]}-{s[10:11]}"
    return s

def compare_and_messages(
    origen_df: pd.DataFrame,
    destino_df: pd.DataFrame,
    tolerances: Dict[str, float],
) -> List[str]:
    origen_df = origen_df.copy()
    destino_df = destino_df.copy()
    origen_df["N_COMP"] = origen_df["N_COMP"].astype(str).str.strip().str.upper()
    destino_df["N_COMP"] = destino_df["N_COMP"].astype(str).str.strip().str.upper()
    origen_df["IDENTIFTRI"] = origen_df["IDENTIFTRI"].astype(str).str.strip()
    destino_df["IDENTIFTRI"] = destino_df["IDENTIFTRI"].astype(str).str.strip()

    keys = ["N_COMP", "IDENTIFTRI"]
    merged = origen_df.merge(destino_df, on=keys, how="left", suffixes=("_origen", "_destino"), indicator=True)

    messages: List[str] = []
    for _, row in merged.iterrows():
        ncomp = str(row.get("N_COMP", "")).strip().upper()
        if row.get("_merge") == "left_only":
            cuit = _fmt_cuit_hyphen(row.get("IDENTIFTRI", ""))
            messages.append(f"⚠️ Factura {ncomp} del proveedor {cuit} no se encuentra en destino. Se omite.")
            continue

        # Para Factura C, solo TOTAL; para el resto, todas
        letter = ncomp[0] if ncomp else ""
        cols_to_check = ("IMP_TOTAL",) if letter == "C" else ("IMP_EXENTO", "IMP_NETO", "IMP_IVA", "IMP_TOTAL")

        # Tipo de cambio del ORIGEN (si no viene, 1.0)
        tc_raw = row.get("TC_origen", 1.0)
        tc = _to_number_locale(tc_raw)
        if not isinstance(tc, float) or np.isnan(tc):
            tc = 1.0

        ok_all = True
        diffs = []
        for name in cols_to_check:
            tol = float(tolerances.get(name, 0.0))
            av = _to_number_locale(row.get(f"{name}_origen"))
            bv = _to_number_locale(row.get(f"{name}_destino"))

            a_adj = av * tc if (isinstance(av, float) and not np.isnan(av)) else av

            # Ambos NaN => ok
            if (isinstance(a_adj, float) and np.isnan(a_adj)) and (isinstance(bv, float) and np.isnan(bv)):
                continue

            is_ok = (isinstance(a_adj, float) and isinstance(bv, float) and (abs(a_adj - bv) <= tol))
            if not is_ok:
                ok_all = False
                # Guardamos el valor AJUSTADO para el mensaje
                diffs.append((name, a_adj, bv))

        if ok_all:
            messages.append(f"✅ Factura {ncomp} coincide entre origen y destino.")
        else:
            parts = [
                f"diferencia en {name.replace('IMP_', '').title()}. Origen: {_fmt_money_es(a_adj)} - Destino: {_fmt_money_es(bv)}"
                for name, a_adj, bv in diffs
            ]
            messages.append(f"❌ Factura {ncomp}: " + "; ".join(parts))

    return messages


