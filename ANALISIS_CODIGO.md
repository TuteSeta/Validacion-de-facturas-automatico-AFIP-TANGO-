# Estado técnico del validador ARCA–Odoo

Actualizado el 1 de octubre de 2026 después de la refactorización v4.

## Hallazgos corregidos

- La conciliación es bidireccional y distingue coincidencias, diferencias, faltantes
  en Odoo y faltantes en ARCA.
- El período se obtiene de las fechas ARCA válidas; Odoo fuera de sus límites se
  informa por separado y no altera los faltantes.
- Tipo, CUIT, punto de venta, número, fecha, moneda, tipo de cambio e importes se
  validan antes del cruce. Las filas inválidas quedan en incidencias.
- El motor de `src/compare.py` es la única implementación de las reglas monetarias.
  Mensajes, métricas y escritores consumen su resultado estructurado.
- Los importes textuales admiten formato español o inglés; también pueden definirse
  separadores por fuente en la configuración.
- Los cuatro artefactos se generan en una carpeta temporal y la carpeta completa se
  publica solo después de finalizar. Ante un error se conserva únicamente el log.
- Los libros ARCA y Odoo se copian con openpyxl, preservando hojas y formato, y se les
  agregan columnas de estado y detalle.
- Las métricas ya no se deducen de emojis o textos.
- La GUI usa una cola para mantener todas las operaciones Tkinter en el hilo principal
  y muestra las nuevas métricas y el reporte consolidado.
- Se retiraron `loader.py`, `matcher.py`, `report.py` y helpers históricos sin uso.
  `load_tango_with_map` se conserva temporalmente como alias compatible.

## Verificación

- 13 pruebas automatizadas cubren conciliación A/B/C, NC/ND, moneda extranjera,
  tolerancia, período, inválidos, duplicados, columnas faltantes, permisos, escritura
  atómica y preservación de libros.
- Cobertura del núcleo: 86 %.
- Ruff y compilación Python: sin errores.
- Integración con los archivos reales:
  - 146 coincidencias;
  - 30 diferencias;
  - 55 faltantes en Odoo;
  - 3 faltantes en ARCA;
  - 10 filas Odoo fuera del período;
  - 0 filas inválidas.

## Riesgos residuales

- La validez del CUIT se limita a exigir 11 dígitos; no se verifica matemáticamente
  el dígito de control.
- Una publicación por renombrado de carpeta es atómica dentro del mismo sistema de
  archivos. El directorio temporal se crea expresamente dentro de la salida para
  mantener esa condición.
- El alias Tango debe retirarse en una versión mayor futura, después de confirmar que
  no existan consumidores externos.
- El EXE incluido sigue siendo el histórico hasta ejecutar `build_windows.bat` en
  Windows y verificar el nuevo PE.
