---
name: windows-exe-release
description: Build, replace, and verify this repository's standalone Windows invoice-validator executable with PyInstaller. Use when preparing or diagnosing a distributable EXE; not for ordinary Python development runs.
---

# Windows EXE release

Build Windows artifacts on Windows. PyInstaller is not a cross-compiler: an artifact
built on Linux is a Linux executable even if its filename ends in `.exe`. If a
Windows runner is unavailable, prepare the reproducible build configuration and
state that the checked-in EXE was not replaced.

The entry point is `launcher_gui_bootstrap.py`. Bundle `config.yaml` at the bundle
root because `src.main._base_dir()` resolves it through `sys._MEIPASS` in a frozen
application. Include `src` imports and ttkbootstrap assets detected by PyInstaller.

Use a clean virtual environment, install pinned runtime dependencies plus a pinned
PyInstaller version, and build through the repository's checked-in spec or build
script. Replace `dist/ValidadorFacturas.exe` only after a successful build. Do not
delete an older usable artifact before its replacement exists.

Verify at minimum:

- the artifact has Windows PE format (`MZ` header), not ELF;
- the frozen app can find `config.yaml`;
- the GUI process starts without an immediate import/configuration failure;
- SHA-256, size, build command, Python version, and PyInstaller version are recorded
  in the handoff;
- source unit/integration tests pass before packaging.

Do not claim that an EXE is updated merely because Python sources changed.
