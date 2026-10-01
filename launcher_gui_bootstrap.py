import tkinter as tk
import traceback
import threading
from queue import Empty, Queue
from tkinter import filedialog, messagebox
from pathlib import Path

# Usamos ttkbootstrap para una interfaz más moderna
import ttkbootstrap as ttk
from ttkbootstrap.constants import BOTH, BOTTOM, LEFT, X

from src.main import run_validation # Mantenemos tu lógica de validación intacta

# --- Clases y Funciones ---

class App(ttk.Window):
    def __init__(self, title, size):
        # --- Configuración de la ventana principal ---
        super().__init__(themename="superhero") # Elige un tema, e.g., "superhero", "litera", "minty"
        self.title(title)
        self.geometry(size)
        self.minsize(560, 480)

        # --- Variables de estado ---
        self.origen_path = tk.StringVar()
        self.destino_path = tk.StringVar()
        self.origen_name = tk.StringVar()
        self.destino_name = tk.StringVar()
        self.output_dir = tk.StringVar(value=str(Path.cwd() / "outputs"))
        self.origen_sheet = tk.StringVar()
        self.destino_sheet = tk.StringVar()
        self.status_text = tk.StringVar(value="Listo para empezar. Por favor, selecciona los archivos.")
        self.result_queue = Queue()

        # --- Crear la interfaz de usuario ---
        self.create_widgets()

    def create_widgets(self):
        """Crea y posiciona todos los widgets en la ventana."""
        main_frame = ttk.Frame(self, padding="20")
        main_frame.pack(fill=BOTH, expand=True)

        # --- Sección de Archivos ---
        files_frame = ttk.LabelFrame(main_frame, text=" 📂 1. Selección de Archivos ", padding="15")
        files_frame.pack(fill=X, expand=True)
        files_frame.columnconfigure(1, weight=1) # Permite que el Entry se expanda

        # Origen (ARCA)
        ttk.Label(files_frame, text="Origen (ARCA):").grid(row=0, column=0, sticky="w", padx=5, pady=(0, 5))
        origen_entry = ttk.Entry(files_frame, textvariable=self.origen_name, state="readonly")
        origen_entry.grid(row=0, column=1, sticky="we", padx=5, pady=(0, 5))
        ttk.Button(
            files_frame,
            text="Elegir...",
            command=lambda: self._pick_file('origen'),
            bootstyle="info-outline"
        ).grid(row=0, column=2, padx=5, pady=(0, 5))

        # Destino (Odoo)
        ttk.Label(files_frame, text="Destino (Odoo):").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        destino_entry = ttk.Entry(files_frame, textvariable=self.destino_name, state="readonly")
        destino_entry.grid(row=1, column=1, sticky="we", padx=5, pady=5)
        ttk.Button(files_frame, text="Elegir...", command=lambda: self._pick_file('destino'), bootstyle="info-outline").grid(row=1, column=2, padx=5, pady=5)

        # --- Sección de Opciones Avanzadas ---
        options_frame = ttk.LabelFrame(main_frame, text=" ⚙️ 2. Opciones (Opcional) ", padding="15")
        options_frame.pack(fill=X, expand=True, pady="15")
        options_frame.columnconfigure((0, 1), weight=1)

        # Hojas de Excel
        ttk.Label(options_frame, text="Nombre de la hoja (Origen):").grid(row=0, column=0, sticky="w", padx=5, pady=(0, 5))
        ttk.Entry(options_frame, textvariable=self.origen_sheet).grid(row=1, column=0, sticky="we", padx=5)

        ttk.Label(options_frame, text="Nombre de la hoja (Destino):").grid(row=0, column=1, sticky="w", padx=5, pady=(0, 5))
        ttk.Entry(options_frame, textvariable=self.destino_sheet).grid(row=1, column=1, sticky="we", padx=5)

        # Carpeta de Salida
        ttk.Label(options_frame, text="Carpeta de Salida:").grid(row=2, column=0, columnspan=2, sticky="w", padx=5, pady=(10, 5))
        output_entry = ttk.Entry(options_frame, textvariable=self.output_dir, state="readonly")
        output_entry.grid(row=3, column=0, columnspan=2, sticky="we", padx=5)
        ttk.Button(options_frame, text="Cambiar Carpeta...", command=self._pick_output_dir, bootstyle="info-outline").grid(row=3, column=2, sticky="e", padx=5)

        # --- Sección de Ejecución ---
        action_frame = ttk.Frame(main_frame, padding="10 0")
        action_frame.pack(fill=X, expand=True)

        self.progress = ttk.Progressbar(action_frame, mode='indeterminate', bootstyle="success-striped")
        self.progress.pack(fill=X, pady=(5, 10))

        self.validate_button = ttk.Button(action_frame, text="🚀 Validar Facturas", command=self.start_validation_thread, bootstyle="success", padding="10")
        self.validate_button.pack(fill=X, expand=True)

        # --- Barra de Estado ---
        status_bar = ttk.Frame(self, padding="5 0", bootstyle="secondary")
        status_bar.pack(side=BOTTOM, fill=X)
        ttk.Label(status_bar, textvariable=self.status_text, padding="5 0").pack(side=LEFT)


    def _pick_file(self, kind):
        file_path = filedialog.askopenfilename(
            title="Elegir Excel de Origen (ARCA)" if kind == 'origen' else "Elegir Excel de Destino (Odoo)",
            filetypes=[("Archivos de Excel", "*.xlsx"), ("Todos los archivos", "*.*")]
        )
        if file_path:
            p = Path(file_path)
            if kind == 'origen':
                self.origen_path.set(str(p))   # ← path completo para lógica
                self.origen_name.set(p.name)   # ← sólo nombre para mostrar
            else:
                self.destino_path.set(str(p))
                self.destino_name.set(p.name)
            self.status_text.set(f"Archivo seleccionado: {p.name}")

    def _pick_output_dir(self):
        """Manejador para seleccionar la carpeta de salida."""
        dir_path = filedialog.askdirectory(title="Elegir carpeta de salida")
        if dir_path:
            self.output_dir.set(dir_path)
            self.status_text.set("Carpeta de salida actualizada.")

    def start_validation_thread(self):
        """Inicia la validación en un hilo separado para no bloquear la GUI."""
        if not self.origen_path.get() or not self.destino_path.get():
            messagebox.showwarning("Faltan archivos", "Por favor, selecciona los archivos de Origen y Destino.")
            return

        params = {
            "origen_path": self.origen_path.get(),
            "destino_path": self.destino_path.get(),
            "origen_sheet": self.origen_sheet.get().strip() or None,
            "destino_sheet": self.destino_sheet.get().strip() or None,
            "output_dir": self.output_dir.get(),
        }

        # Deshabilitar botón y empezar la animación de progreso
        self.validate_button.config(state="disabled", text="Validando...")
        self.progress.start()
        self.status_text.set("Procesando archivos, por favor espera...")

        # Ejecutar la lógica pesada en otro hilo
        thread = threading.Thread(target=self._run_validation_logic, args=(params,))
        thread.daemon = True
        thread.start()
        self.after(100, self._poll_validation_result)

    def _run_validation_logic(self, params):
        """Contiene la lógica de validación que se ejecutará en el hilo."""
        try:
            Path(params["output_dir"]).mkdir(parents=True, exist_ok=True)
            result = run_validation(**params)
            self.result_queue.put(("ok", result))
        except Exception as e:
            traceback.print_exc()
            self.result_queue.put(("error", e))

    def _poll_validation_result(self):
        """Entrega el resultado al hilo de Tk, sin acceder a Tk desde el worker."""
        try:
            status, payload = self.result_queue.get_nowait()
        except Empty:
            self.after(100, self._poll_validation_result)
            return
        if status == "ok":
            self._on_validation_complete(payload)
        else:
            self._on_validation_error(payload)

    def _on_validation_complete(self, result):
        """Se ejecuta en el hilo principal cuando la validación es exitosa."""
        self._reset_ui_state()
        resumen = (
            f"✔ Resultados: {result['run_dir']}\n"
            f"✔ Reporte: {result['reporte_validacion']}\n"
            f"\n✔ Coinciden: {result['coincidencias']}\n"
            f"✖ Con diferencias: {result['diferencias']}\n"
            f"⚠ Faltan en Odoo: {result['faltantes_en_odoo']}\n"
            f"⚠ Faltan en ARCA: {result['faltantes_en_arca']}\n"
            f"⚠ Inválidos: {result['invalidos_arca'] + result['invalidos_odoo']}\n"
            f"ℹ Odoo fuera del período: {result['fuera_periodo_odoo']}\n"
        )
        self.status_text.set("¡Validación completada con éxito!")
        messagebox.showinfo("Proceso Terminado", resumen)

    def _on_validation_error(self, error):
        """Se ejecuta en el hilo principal si ocurre un error."""
        self._reset_ui_state()
        self.status_text.set("Ocurrió un error durante la validación.")
        messagebox.showerror("Error", f"Ocurrió un error inesperado:\n{error}")

    def _reset_ui_state(self):
        """Restaura la GUI a su estado inicial después de una operación."""
        self.progress.stop()
        self.validate_button.config(state="normal", text="🚀 Validar Facturas")

def main():
    app = App(title="Validador de Facturas ARCA ↔ Odoo v4.0", size="600x500")
    app.mainloop()

if __name__ == "__main__":
    main()
