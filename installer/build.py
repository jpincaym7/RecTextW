"""
Script automatizado de build. Ejecutar con: python installer/build.py
Pasos:
  1. Limpia directorios dist/ y build/
  2. Ejecuta PyInstaller
  3. Ejecuta Inno Setup compiler (ISCC.exe) si está disponible
  4. Reporta tamaño final del instalador
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
SEP = ";" if sys.platform == "win32" else ":"


def clean() -> None:
    print("[1/4] Limpiando directorios dist/ y build/...")
    for d in (ROOT / "dist", ROOT / "build"):
        if d.exists():
            shutil.rmtree(d)
            print(f"  Eliminado: {d}")


def run_pyinstaller() -> None:
    print("[2/4] Ejecutando PyInstaller...")
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name", "InnoTech VideoTutor",
        "--windowed",
        "--onedir",
        "--noconfirm",
        # Datos no-Python que deben quedar en _internal/
        "--add-data", f"{ROOT / 'resources'}{SEP}resources",
        "--add-data", f"{ROOT / 'app' / 'ui' / 'styles.qss'}{SEP}app/ui",
        # Imports ocultos (detectados en runtime, PyInstaller no los rastrea)
        "--hidden-import", "whisper",
        "--hidden-import", "torch",
        "--hidden-import", "torchaudio",
        "--hidden-import", "numba",
        "--hidden-import", "llvmlite",
        "--hidden-import", "google.generativeai",
        "--hidden-import", "groq",
        "--hidden-import", "openai",
        "--hidden-import", "cryptography",
        "--hidden-import", "keyring.backends.Windows",
        "--hidden-import", "tiktoken_ext.openai_public",
        "--hidden-import", "tiktoken_ext",
        "--hidden-import", "pkg_resources.py2_warn",
        # Paquetes con extensiones nativas o assets de datos
        "--collect-all", "whisper",
        "--collect-all", "torch",
        "--collect-all", "torchaudio",
        "--collect-all", "numba",
        "--collect-all", "llvmlite",
        # Excluir módulos pesados innecesarios
        "--exclude-module", "matplotlib",
        "--exclude-module", "scipy",
        "--exclude-module", "PIL",
        "--exclude-module", "IPython",
        "--exclude-module", "jupyter",
        str(ROOT / "main.py"),
    ]

    # Agregar ícono si existe (formato .ico requerido por PyInstaller)
    ico_path = ROOT / "resources" / "icons" / "app_logo.ico"
    if ico_path.exists():
        cmd += ["--icon", str(ico_path)]

    result = subprocess.run(cmd, cwd=str(ROOT))
    if result.returncode != 0:
        print("ERROR: PyInstaller falló")
        sys.exit(1)
    print("  PyInstaller completado exitosamente")


def run_inno_setup() -> None:
    print("[3/4] Buscando Inno Setup...")
    local_programs = Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Inno Setup 6" / "ISCC.exe"
    iscc_candidates = [
        Path("C:/Program Files (x86)/Inno Setup 6/ISCC.exe"),
        Path("C:/Program Files/Inno Setup 6/ISCC.exe"),
        local_programs,
        shutil.which("ISCC"),
    ]
    iscc = next((p for p in iscc_candidates if p and Path(p).exists()), None)

    if iscc is None:
        print("  AVISO: Inno Setup no encontrado.")
        print("  Descárgalo gratis desde: https://jrsoftware.org/isinfo.php")
        print("  El build de PyInstaller está listo en: dist/InnoTech VideoTutor/")
        return

    iss_path = ROOT / "installer" / "innosetup_script.iss"
    result = subprocess.run([str(iscc), str(iss_path)], cwd=str(ROOT))
    if result.returncode != 0:
        print("ERROR: Inno Setup falló")
        sys.exit(1)
    print("  Instalador generado exitosamente")


def report_size() -> None:
    print("[4/4] Reportando tamaño...")
    installer_dir = ROOT / "dist" / "installer"
    if installer_dir.exists():
        for f in installer_dir.glob("*.exe"):
            size_mb = f.stat().st_size / (1024 * 1024)
            print(f"  Instalador: {f.name} ({size_mb:.1f} MB)")

    app_dir = ROOT / "dist" / "InnoTech VideoTutor"
    if app_dir.exists():
        total = sum(f.stat().st_size for f in app_dir.rglob("*") if f.is_file())
        print(f"  Tamaño total del directorio: {total / (1024 * 1024):.1f} MB")


if __name__ == "__main__":
    print("=" * 50)
    print("InnoTech VideoTutor — Build Script")
    print("=" * 50)
    clean()
    run_pyinstaller()
    run_inno_setup()
    report_size()
    print("\nBuild completado.")
