import sys
import yaml
from pathlib import Path
from typing import Optional, Dict, Any

from src.transform import load_afip_with_map, load_odoo_with_map
from src.compare import compare_and_messages
from src.origen_validated import write_origen_validado
from src.mark_dest import mark_and_append


def _base_dir() -> Path:
    """
    Devuelve la carpeta base del proyecto en dev o la carpeta temporal
    del bundle cuando está empaquetado (sys._MEIPASS).
    """
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)  
    return Path(__file__).resolve().parents[1]


def _executable_dir() -> Path:
    """Carpeta visible junto al EXE, o raíz del proyecto en desarrollo."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


def _load_config(config_path: Optional[str] = None) -> dict:
    """
    Busca config.yaml en:
    1) Ruta explícita (si se pasa),
    2) Carpeta base (_base_dir()),
    3) Directorio actual (cwd) como último recurso.
    """
    candidates = []
    if config_path:
        candidates.append(Path(config_path))
    # Un config junto al EXE permite ajustar futuras exportaciones sin recompilar.
    candidates.append(_executable_dir() / "config.yaml")
    candidates.append(_base_dir() / "config.yaml")
    candidates.append(Path.cwd() / "config.yaml")

    for p in dict.fromkeys(candidates):
        if p.exists():
            return yaml.safe_load(p.read_text(encoding="utf-8"))

    raise FileNotFoundError("No se encontró config.yaml en ninguna ubicación conocida.")


# --- API para la GUI (importa launcher_gui_bootstrap.py) ---
def run_validation(
    origen_path: str,
    destino_path: str,
    origen_sheet: Optional[str] = None,
    destino_sheet: Optional[str] = None,
    output_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Ejecuta todo el pipeline usando tu lógica actual
    y devuelve paths de salida + métricas para la GUI.
    """
    cfg = _load_config()

    origen_sheet  = origen_sheet  or cfg.get("origen_sheet", "Sheet1")
    destino_sheet = destino_sheet or cfg.get("destino_sheet", "Hoja1")
    mapping       = cfg["mapping"]

    # 1) Normalizamos ARCA/Odoo según el mapeo
    df_afip  = load_afip_with_map(origen_path,  origen_sheet,  mapping)
    df_odoo = load_odoo_with_map(destino_path, destino_sheet, mapping)

    # 2) Columnas a comparar 
    columns_cfg = cfg.get("columns", [
        {"name": "IMP_EXENTO", "type": "number", "tolerance": 0.01},
        {"name": "IMP_NETO",   "type": "number", "tolerance": 0.01},
        {"name": "IMP_IVA",    "type": "number", "tolerance": 0.01},
        {"name": "IMP_TOTAL",  "type": "number", "tolerance": 0.01},
    ])

    # 3) Mensajes
    tolerances = {c["name"]: float(c.get("tolerance", 0.0)) for c in columns_cfg}
    msgs = compare_and_messages(
        origen_df=df_afip,
        destino_df=df_odoo,
        tolerances=tolerances,
    )
    for m in msgs:
        print(m)

    # 4) Generamos copia del destino con marcas visuales
    out_dir = Path(output_dir) if output_dir else (_base_dir() / "outputs")
    out_dir.mkdir(parents=True, exist_ok=True)

    destino_validado_name = Path(cfg.get("output_file", "destino_validado.xlsx")).name
    destino_validado_path = out_dir / destino_validado_name

    faltantes, destino_guardado = mark_and_append(
        origen_df=df_afip,
        destino_xlsx_path=destino_path,
        destino_sheet=destino_sheet,
        columns_cfg=columns_cfg,
        out_path=str(destino_validado_path),
        mapping=mapping,
    )

    # 5) Origen validado
    origen_validado_path = out_dir / "origen_validado.xlsx"
    write_origen_validado(
        origen_path=origen_path,
        sheet=origen_sheet,
        mapping=mapping,
        destino_df=df_odoo,
        tolerances=tolerances,
        out_path=str(origen_validado_path),
    )

    return {
        "destino_validado": destino_guardado,
        "origen_validado":  str(origen_validado_path),
        "faltantes":        int(faltantes),
        "coincidencias":    sum(message.startswith("✅") for message in msgs),
        "diferencias":      sum(message.startswith("❌") for message in msgs),
        "mensajes":         msgs,
    }


# --- Modo CLI ---
def main():
    cfg = _load_config()

    origen_path   = str(_base_dir() / "data" / "origen.xlsx")
    destino_path  = str(_base_dir() / "data" / "destino.xlsx")
    origen_sheet  = cfg.get("origen_sheet", "Sheet1")
    destino_sheet = cfg.get("destino_sheet", "Hoja1")

    result = run_validation(
        origen_path=origen_path,
        destino_path=destino_path,
        origen_sheet=origen_sheet,
        destino_sheet=destino_sheet,
        output_dir=str(_base_dir() / "outputs"),
    )

    print(f"✅ Archivo de salida (destino): {result['destino_validado']}")
    print(f"✅ Archivo de salida (origen) : {result['origen_validado']}")
    if result["faltantes"]:
        print(f"⚠️ Hay {result['faltantes']} comprobante(s) de ARCA sin coincidencia en Odoo.")
    else:
        print("✅ Todos los comprobantes de ARCA existen al menos una vez en Odoo.")


if __name__ == "__main__":
    main()
