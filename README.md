# Validador de facturas ARCA ↔ Odoo / Finnegans

Aplicación de escritorio para comparar la exportación **Comprobantes de Compras**
de ARCA con el reporte **Libro de IVA argentino** de Odoo o con el reporte
**IVA Compras** de Finnegans. El modo se elige antes de iniciar cada validación.

## Qué valida

- Identifica cada comprobante por tipo, letra, punto de venta, número y CUIT.
- Soporta facturas, notas de crédito y notas de débito A, B y C, además de
  los tipos Tique Factura A y Recibo C presentes en el reporte de referencia.
- Convierte los importes de ARCA a pesos usando el tipo de cambio informado.
- Trata las notas de crédito con el signo contable correspondiente a cada sistema.
- Para comprobantes B y C compara el total, ya que ARCA no siempre discrimina sus
  componentes de la misma forma que Odoo.
- Para comprobantes A compara neto gravado, IVA, otros conceptos y total.
- Concilia en ambos sentidos: faltantes en el sistema elegido y faltantes en ARCA.
- Separa los comprobantes destino fuera del rango de fechas cubierto por ARCA.
- Agrupa las líneas de impuestos y otros conceptos que Finnegans exporta debajo
  del comprobante principal.
- Excluye datos inválidos del cruce y los informa sin detener las filas válidas.

El mapeo de hojas, filas de encabezado y columnas está en `config.yaml` para poder
adaptarlo si cambia una exportación.

## Archivos esperados

1. Origen ARCA: Excel de **Comprobantes de Compras**.
2. Uno de los siguientes destinos:
   - Odoo: Excel del **Libro de IVA argentino**.
   - Finnegans: Excel de **IVA Compras**.

Los formatos de referencia para esta versión son:

- `Comprobantes de Compras - CUIT 30719485991.xlsx`
- `libro_de_iva_argentino (2).xlsx`
- `IVA COMPRAS GT - FINNEGANS.xlsx`

## Uso con interfaz gráfica

```bash
python -m venv .venv
```

En Windows:

```powershell
.venv\Scripts\activate
pip install -r requirements.txt
python launcher_gui_bootstrap.py
```

En Linux/macOS:

```bash
source .venv/bin/activate
pip install -r requirements.txt
python launcher_gui_bootstrap.py
```

En la ventana:

1. Elegí **ARCA ↔ Odoo** o **ARCA ↔ Finnegans**.
2. Seleccioná el archivo de ARCA.
3. Seleccioná el archivo del sistema elegido.
4. Elegí la carpeta de salida y presioná **Validar Facturas**.

Las hojas predeterminadas son `Sheet1` para ARCA, `Libro de IVA argentino` para
Odoo y `hoja1` para Finnegans.

## Resultados

Cada ejecución crea una carpeta `Validacion_AAAAMMDD_HHMMSS` con:

- `origen_validado.xlsx`: copia completa del libro ARCA, conservando formato y hojas.
- `odoo_validado.xlsx` o `finnegans_validado.xlsx`: copia completa del destino con
  estados e importes diferentes.
- `reporte_validacion.xlsx`: resumen, conciliación, incidencias y comprobantes del
  destino fuera del período.
- `validacion.log`: archivos usados, período y métricas de la ejecución.

Los estados usan verde para coincidencias, rojo para diferencias, amarillo para
faltantes, naranja para inválidos y gris para filas fuera del período. La carpeta se
publica únicamente cuando los cuatro archivos terminan correctamente.

## Desarrollo y prueba por consola

La función reutilizable es `src.main.run_validation`. El argumento
`comparison_mode` acepta `odoo` (predeterminado) o `finnegans`. También se puede
ejecutar:

```bash
python -m unittest discover -s tests -v
```

Para generar el ejecutable en Windows, abrí una terminal en la raíz del proyecto y
ejecutá:

```bat
build_windows.bat
```

El script crea un entorno limpio, instala las versiones fijadas, ejecuta las pruebas
y genera `dist\ValidadorFacturas.exe` junto con `dist\config.yaml`. PyInstaller no es
un compilador cruzado: el EXE de Windows debe construirse en Windows.

La configuración externa colocada al lado del EXE tiene prioridad sobre la copia
incluida dentro del ejecutable, por lo que futuros ajustes de columnas no siempre
requieren recompilar.

El análisis técnico vigente está en `ANALISIS_CODIGO.md`.

## Errores frecuentes

- **Archivo en uso**: cerrá el Excel antes de validar.
- **Hoja o columna no encontrada**: comprobá que los archivos correspondan a las
  exportaciones indicadas o actualizá `config.yaml`.
- **Comprobante omitido**: está en ARCA pero todavía no se encontró en el destino
  con el mismo tipo, número y CUIT.
- **Validación fallida**: el diálogo muestra la ruta de un log técnico creado en la
  carpeta de salida; no quedan Excel parciales.
