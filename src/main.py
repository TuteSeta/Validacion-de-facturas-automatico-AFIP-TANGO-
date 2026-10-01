import shutil
import sys
import tempfile
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

from src.compare import messages_from_result, reconcile
from src.mark_dest import write_odoo_validado
from src.origen_validated import write_origen_validado
from src.output_report import write_consolidated_report
from src.transform import load_afip_result, load_odoo_result


APP_VERSION = "4.0"


def _base_dir() -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parents[1]


def _executable_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


def _load_config(config_path: Optional[str] = None) -> dict:
    candidates = []
    if config_path:
        candidates.append(Path(config_path))
    candidates.extend([
        _executable_dir() / "config.yaml",
        _base_dir() / "config.yaml",
        Path.cwd() / "config.yaml",
    ])
    for path in dict.fromkeys(candidates):
        if path.exists():
            config = yaml.safe_load(path.read_text(encoding="utf-8"))
            if not isinstance(config, dict) or "mapping" not in config:
                raise ValueError(f"Configuración inválida: {path}")
            return config
    raise FileNotFoundError("No se encontró config.yaml en ninguna ubicación conocida.")


def _available_run_dir(output_dir: Path, stamp: str) -> Path:
    base = output_dir / f"Validacion_{stamp}"
    candidate, suffix = base, 1
    while candidate.exists():
        candidate = output_dir / f"{base.name}_{suffix:02d}"
        suffix += 1
    return candidate


def _success_log(reconciliation, source_paths):
    metrics = reconciliation.metrics
    lines = [
        f"Validador ARCA–Odoo v{APP_VERSION}",
        f"Fecha de ejecución: {datetime.now():%d/%m/%Y %H:%M:%S}",
        f"ARCA: {source_paths['arca']}",
        f"Odoo: {source_paths['odoo']}",
        f"Período: {reconciliation.period_start:%d/%m/%Y}–{reconciliation.period_end:%d/%m/%Y}",
    ]
    lines.extend(f"{key}: {value}" for key, value in metrics.items())
    return "\n".join(lines) + "\n"


def run_validation(
    origen_path: str,
    destino_path: str,
    origen_sheet: Optional[str] = None,
    destino_sheet: Optional[str] = None,
    output_dir: Optional[str] = None,
    config_path: Optional[str] = None,
) -> Dict[str, Any]:
    cfg = _load_config(config_path)
    origen_sheet = origen_sheet or cfg.get("origen_sheet", "Sheet1")
    destino_sheet = destino_sheet or cfg.get("destino_sheet", "Libro de IVA argentino")
    mapping = cfg["mapping"]
    columns_cfg = cfg.get("columns", [])
    tolerances = {column["name"]: float(column.get("tolerance", 0.0)) for column in columns_cfg}

    output_root = Path(output_dir) if output_dir else (_executable_dir() / "outputs")
    output_root.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    final_dir = _available_run_dir(output_root, stamp)
    staging_dir = Path(tempfile.mkdtemp(prefix=f".{final_dir.name}_", dir=output_root))

    try:
        arca_result = load_afip_result(origen_path, origen_sheet, mapping)
        odoo_result = load_odoo_result(destino_path, destino_sheet, mapping)
        reconciliation = reconcile(arca_result, odoo_result, tolerances)
        messages = messages_from_result(reconciliation)

        arca_output = staging_dir / "origen_validado.xlsx"
        odoo_output = staging_dir / "odoo_validado.xlsx"
        report_output = staging_dir / "reporte_validacion.xlsx"
        log_output = staging_dir / "validacion.log"
        write_origen_validado(
            origen_path, origen_sheet, mapping, reconciliation, arca_output
        )
        write_odoo_validado(
            destino_path, destino_sheet, mapping, reconciliation, odoo_output
        )
        write_consolidated_report(
            report_output,
            reconciliation,
            {"arca": Path(origen_path).name, "odoo": Path(destino_path).name},
        )
        log_output.write_text(
            _success_log(reconciliation, {"arca": origen_path, "odoo": destino_path}),
            encoding="utf-8",
        )

        staging_dir.replace(final_dir)
        metrics = reconciliation.metrics
        result = {
            "run_dir": str(final_dir),
            "destino_validado": str(final_dir / odoo_output.name),
            "origen_validado": str(final_dir / arca_output.name),
            "reporte_validacion": str(final_dir / report_output.name),
            "log": str(final_dir / log_output.name),
            "faltantes": metrics["faltantes_en_odoo"],
            **metrics,
            "periodo": {
                "desde": reconciliation.period_start.date().isoformat(),
                "hasta": reconciliation.period_end.date().isoformat(),
            },
            "mensajes": messages,
        }
        for message in messages:
            print(message)
        return result
    except Exception as error:
        shutil.rmtree(staging_dir, ignore_errors=True)
        error_log = output_root / f"validacion_error_{stamp}.log"
        error_log.write_text(
            f"Validador ARCA–Odoo v{APP_VERSION}\n{traceback.format_exc()}",
            encoding="utf-8",
        )
        raise RuntimeError(
            f"La validación falló. Detalle técnico: {error_log}"
        ) from error


def main():
    result = run_validation(
        origen_path=str(_base_dir() / "data" / "origen.xlsx"),
        destino_path=str(_base_dir() / "data" / "destino.xlsx"),
        output_dir=str(_base_dir() / "outputs"),
    )
    print(f"Resultados: {result['run_dir']}")


if __name__ == "__main__":
    main()
