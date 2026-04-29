vc_redist.x64.exe — Visual C++ Redistributable (Microsoft)
===========================================================

Este archivo es OPCIONAL. Se usa para garantizar que el equipo tenga
las DLLs de Visual C++ que necesitan PyTorch y Whisper.

En Windows 10/11 modernos casi siempre ya viene instalado, pero
incluirlo evita el error "MSVCP140.dll no se encontró" en máquinas viejas.

DESCARGAR (manual, una sola vez)
--------------------------------
URL oficial:
  https://aka.ms/vs/17/release/vc_redist.x64.exe

Guardar como:
  installer/prereqs/vc_redist.x64.exe

Si NO lo descargas, el build sigue funcionando — Inno Setup omite el
componente y la app se instala sin él (puede fallar en máquinas sin
Visual C++ ya instalado).
