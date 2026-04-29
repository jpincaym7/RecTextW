"""Punto de entrada de InnoTech VideoTutor."""
import os
import sys
from pathlib import Path

# Frozen --windowed (console=False) deja sys.stdout/stderr en None. Cualquier
# librería que escriba ahí (tqdm de Whisper, prints de torch, etc.) crashea
# con AttributeError. Redirigir a archivos de log antes de cualquier import
# pesado evita el crash y nos deja diagnóstico.
if getattr(sys, 'frozen', False):
    _log_dir = Path(os.environ.get("APPDATA", Path.home())) / "InnoTech" / "VideoTutor" / "logs"
    _log_dir.mkdir(parents=True, exist_ok=True)
    if sys.stdout is None:
        sys.stdout = open(_log_dir / "stdout.log", "a", encoding="utf-8", buffering=1)
    if sys.stderr is None:
        sys.stderr = open(_log_dir / "stderr.log", "a", encoding="utf-8", buffering=1)

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import Qt

from app.config import APP_NAME, ICONS_DIR
from app.utils.logger import setup_logger


def main() -> None:
    logger = setup_logger()
    logger.info("Iniciando %s", APP_NAME)

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName("InnoTech Solutions")

    icon_path = ICONS_DIR / "app_logo.svg"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    # Splash + verificaciones
    from app.windows.splash_screen import SplashScreen
    from app.windows.main_window import MainWindow

    splash = SplashScreen()

    main_window: MainWindow | None = None

    def on_ready() -> None:
        nonlocal main_window
        main_window = MainWindow()
        main_window.show()

    splash.ready.connect(on_ready)
    splash.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
