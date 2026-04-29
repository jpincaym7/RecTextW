"""Punto de entrada de InnoTech VideoTutor."""
import sys

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
