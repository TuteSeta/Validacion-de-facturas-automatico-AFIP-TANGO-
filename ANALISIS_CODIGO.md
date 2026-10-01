# Análisis técnico del validador ARCA–Odoo

Fecha del análisis: 1 de octubre de 2026.

## Resumen ejecutivo

El flujo principal funciona con las exportaciones actuales y genera dos libros de
salida válidos. La prueba integral con los archivos disponibles procesó 231
comprobantes de ARCA y 189 registros agrupados de Odoo:

- 146 coincidencias;
- 30 comprobantes con diferencias;
- 55 comprobantes de ARCA ausentes en Odoo;
- 13 claves presentes en Odoo y ausentes en ARCA, actualmente no informadas por la
  aplicación.

La base es adecuada para continuar como aplicación Python de escritorio. Los riesgos
principales no están en el rendimiento, sino en reglas de negocio duplicadas, datos
inválidos aceptados silenciosamente y una conciliación que hoy funciona en un solo
sentido.

## Hallazgos prioritarios

### Alta: la conciliación no informa Odoo → ARCA

`compare_and_messages` realiza un `left join` desde ARCA. Esto detecta lo que falta
en Odoo, pero no compras cargadas en Odoo que no estén en la descarga de ARCA. En los
archivos actuales existen 13 claves de este tipo; algunas pueden corresponder a julio
porque el reporte Odoo contiene filas anteriores a agosto.

Recomendación: producir un resultado estructurado bidireccional y validar también el
período de ambos archivos. Separar al menos `coincide`, `difiere`, `falta_en_odoo` y
`falta_en_arca`.

### Alta: las reglas de comparación están triplicadas

La selección de campos por letra, el tipo de cambio y la tolerancia se implementan
por separado en:

- `src/compare.py`;
- `src/origen_validated.py`;
- `src/mark_dest.py`.

Una modificación puede cambiar los mensajes sin cambiar los colores, o viceversa.
Durante esta migración ya fue necesario corregir la misma regla B/C en los tres
lugares.

Recomendación: crear un único motor que devuelva resultados estructurados por clave
y campo. Los escritores Excel y la GUI deberían consumir ese resultado sin volver a
comparar importes.

### Alta: valores inválidos pueden transformarse en claves aparentemente válidas

`_tipo_to_doc_letter` cae por defecto en `FA-A` para un tipo desconocido y
`_to_int_safe` convierte valores inválidos o vacíos en cero. Un formato nuevo de ARCA
podría terminar como un comprobante A con punto de venta o número cero en lugar de
detener la validación.

`_normalize_cuit` tampoco exige exactamente 11 dígitos. Además, al convertir claves
a texto, CUIT ausentes pueden terminar comparándose como el mismo valor textual.

Recomendación: validar tipo soportado, CUIT de 11 dígitos, punto de venta y número
antes del cruce. Rechazar o listar filas inválidas; nunca asignarles una identidad por
defecto.

### Alta: el tipo de cambio ausente se reemplaza silenciosamente por 1

Esto es correcto para pesos, pero puede validar incorrectamente una factura en moneda
extranjera si la exportación cambia o viene incompleta. El archivo ARCA contiene la
columna `Moneda`, pero actualmente no forma parte del modelo normalizado.

Recomendación: incorporar moneda. Para moneda distinta de pesos, exigir un tipo de
cambio positivo; para pesos, normalizarlo explícitamente a 1.

## Hallazgos medios

### El parser numérico asume formato argentino para todo texto

Una cadena `1.234,56` se interpreta correctamente, pero `1234.56` se convierte en
`123456`. Las celdas actuales llegan como números de Excel y no sufren el problema,
pero una exportación futura con importes almacenados como texto podría hacerlo.

Recomendación: detectar separadores según su posición o definir el formato por fuente
en la configuración.

### Los resultados no se escriben como una operación atómica

Primero se guarda la copia de Odoo y después la de ARCA. Si falla el segundo archivo,
queda una salida parcial aunque la GUI muestre error. La salida ARCA tampoco tiene el
fallback con fecha que sí tiene la salida Odoo cuando el archivo está abierto.

Recomendación: generar ambos archivos con nombres temporales y moverlos a sus nombres
finales solo cuando los dos terminen correctamente.

### Los mensajes son también el modelo de datos

Las métricas se calculan inspeccionando si cada texto comienza con `✅` o `❌`. Esto
es frágil frente a cambios de redacción y dificulta agregar reportes, filtros o una
tabla en pantalla.

Recomendación: usar un objeto o `DataFrame` de resultados con estado, clave y
diferencias; generar los textos al final.

### Los errores del EXE serán difíciles de diagnosticar

La GUI muestra el mensaje de la excepción, pero PyInstaller se genera en modo
`windowed`, por lo que el traceback impreso no queda visible. Errores de encabezado,
permisos o archivos dañados pueden requerir asistencia técnica.

Recomendación: escribir un log en la carpeta de salida, con traceback y versión de la
aplicación, y mostrar su ruta en el diálogo de error.

### La salida ARCA no conserva el libro original

La salida se reconstruye con pandas. Pierde la fila de título y el formato del archivo
ARCA original. Esto no afecta la comparación, pero el resultado no es literalmente
una copia marcada como sí ocurre con Odoo.

Recomendación: decidir si la salida tabular actual es suficiente. Si se necesita
fidelidad visual, marcar una copia con openpyxl.

## Mantenibilidad y pruebas

- Ruff no informa errores después de la limpieza realizada.
- Las cuatro pruebas unitarias pasan, pero cubren solo normalización básica. La
  medición actual da 36 % sobre los módulos importados por esas pruebas y no ejercita
  comparación, escritura Excel, GUI ni configuración.
- La prueba integral manual con los dos archivos reales pasa y mantiene el resultado
  146/30/55.
- `loader.py`, `matcher.py`, `report.py`, `compare_columns`, `_normalize_name`,
  `_tipo_to_letter` y el alias `load_tango_with_map` no participan en el flujo actual.

Recomendación: agregar fixtures Excel pequeños para facturas A/B/C, moneda extranjera,
NC, duplicados, CUIT inválido, columna faltante y archivo bloqueado. Después retirar
el código histórico cuando se confirme que ninguna integración externa lo usa.

## Mejoras aplicadas durante el análisis

- Acceso a Tkinter confinado al hilo principal mediante una cola.
- Ruta real devuelta cuando Odoo debe guardarse con nombre alternativo.
- `config.yaml` externo junto al EXE con prioridad sobre el incluido en el bundle.
- Ruff limpio y dependencia `ttkbootstrap` declarada.
- Build Windows reproducible con `ValidadorFacturas.spec`,
  `requirements-build.txt` y `build_windows.bat`.
- Skills de mantenimiento y release disponibles tanto en `.agents/skills` como en
  `.claude/skills`.

## Plan recomendado

1. Centralizar el motor de comparación y devolver resultados estructurados.
2. Agregar conciliación Odoo → ARCA y control de período.
3. Validar claves, moneda y tipo de cambio antes de comparar.
4. Incorporar pruebas Excel de integración y llevar la cobertura del núcleo por
   encima de 80 %.
5. Agregar log de errores y escritura atómica de salidas.
6. Retirar módulos heredados y recién entonces considerar nuevas funciones de UI.
