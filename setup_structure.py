import os

folders = [
    "data",
    "outputs",
    "src"
]

files = {
    "README.md": "# Validador de Facturas\n",
    "requirements.txt": "pandas\nopenpyxl\nPyYAML\n",
    "config.yaml": "# Configuración inicial\n",
    "src/__init__.py": "",
    "src/main.py": "",
    "src/loader.py": "",
    "src/matcher.py": "",
    "src/compare.py": "",
    "src/report.py": ""
}

for folder in folders:
    os.makedirs(folder, exist_ok=True)

for path, content in files.items():
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

print("✅ Estructura creada correctamente.")
