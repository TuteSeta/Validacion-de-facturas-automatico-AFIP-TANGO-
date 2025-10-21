# Validador de Facturas (AFIP ⇄ Sistema interno)

Herramienta para **comparar y validar** facturas entre dos fuentes (por ejemplo AFIP y Tango/ERP), generar un **reporte de diferencias** y **marcar** en el archivo de destino qué comprobantes faltan o no coinciden.

Pensado para **usuarios no técnicos**: puede utilizarse con **interfaz gráfica (EXE)** o en **modo desarrollador** con Python.

---

## 🧰 Características
- Procesa en lote dos archivos Excel (origen y destino).
- Mapea columnas mediante `config.yaml` (sin tocar el código).
- Genera mensajes de validación y marcas en los archivos Excel.
- Mantiene el formato original de los documentos.
- Interfaz empaquetada en `.exe` para uso directo sin consola.

---

---

## 🖱️ Uso del ejecutable (.exe)
1. Entrá en la carpeta `dist/`.
2. Abrí `ValidadorFacturas.exe` (doble clic).
3. En la interfaz:
   - Seleccioná el archivo **de AFIP** en el campo **origen**.
   - Seleccioná el archivo **de TANGO** en el campo **destino**.
   - Elegí una **carpeta de salida** donde se guardarán los resultados.
4. Presioná **Validar**.
5. En la carpeta de salida se generarán los siguientes archivos:
   - `origen_validado.xlsx` → versión de AFIP con colores sobre lo que esta, no esta o esta diferente.
   - `destino_marcado.xlsx` → archivo TANGO con marcas y comentarios.

✅ **No requiere instalación** ni entorno Python.

---

## 💻 Uso en modo desarrollador
1. Crear y activar entorno virtual:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate    # En Windows
   # source .venv/bin/activate  # En Linux/Mac
   ```

2. Instalar dependencias:
   ```bash
   pip install -r requirements.txt
   ```

3. Ejecutar la interfaz gráfica:
   ```bash
   python src/launcher_gui_bootstrap.py
   ```

4. O ejecutar desde la consola (modo CLI):
   ```bash
   python src/main.py
   ```

---

## 🧾 Archivos generados
- `data/salida/origen_validado.xlsx`
- `data/salida/destino_marcado.xlsx`

---

## 🧯 Errores comunes
- **"Archivo en uso"** → Cerrá los Excel abiertos antes de correr.
- **"Hoja o columna no encontrada"** → Revisá nombres exactos en `config.yaml`.
- **"No se encuentran archivos"** → Verificá que estén en la carpeta correcta.

---


---

## 🧩 Licencia
Proyecto de uso libre para fines administrativos y educativos.
