# Validador de facturas ARCA ↔ Odoo

Aplicación de escritorio para comparar la exportación **Mis Comprobantes Recibidos**
de ARCA con el reporte **Libro de IVA argentino** de Odoo.

## Qué valida

- Identifica cada comprobante por tipo, letra, punto de venta, número y CUIT.
- Soporta facturas, notas de crédito y notas de débito A, B y C.
- Convierte los importes de ARCA a pesos usando el tipo de cambio informado.
- Trata las notas de crédito de ARCA con el signo contable usado por Odoo.
- Para comprobantes B y C compara el total, ya que ARCA no siempre discrimina sus
  componentes de la misma forma que Odoo.
- Para comprobantes A compara neto gravado, IVA, otros conceptos y total.

El mapeo de hojas, filas de encabezado y columnas está en `config.yaml` para poder
adaptarlo si cambia una exportación.

## Archivos esperados

1. Origen ARCA: Excel de **Mis Comprobantes Recibidos**.
2. Destino Odoo: Excel del **Libro de IVA argentino**.

Los formatos de referencia para esta versión son:

- `Mis Comprobantes Recibidos - CUIT 30719485991 (1).xlsx`
- `libro_de_iva_argentino (2).xlsx`

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

1. Seleccioná el archivo de ARCA.
2. Seleccioná el archivo de Odoo.
3. Elegí la carpeta de salida.
4. Presioná **Validar Facturas**.

Si se dejan vacíos los nombres de hoja, se usan `Sheet1` para ARCA y
`Libro de IVA argentino` para Odoo.

## Resultados

- `origen_validado.xlsx`: copia tabular de ARCA con cada fila en verde
  (coincide), rojo (difiere) o amarillo (no existe en Odoo).
- `odoo_validado.xlsx`: copia del reporte original de Odoo; los importes que
  difieren quedan resaltados en amarillo, sin alterar el archivo original.

## Desarrollo y prueba por consola

La función reutilizable es `src.main.run_validation`. También se puede ejecutar:

```bash
python -m unittest discover -s tests -v
```

El ejecutable histórico de `dist/` corresponde a la versión Tango hasta que se haga
un build nuevo en Windows. Para generarlo, abrí una terminal en la raíz del proyecto
y ejecutá:

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
- **Comprobante omitido**: está en ARCA pero todavía no se encontró en Odoo con el
  mismo tipo, número y CUIT.
