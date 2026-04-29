"""Ventana principal frameless con sidebar, stacked views y barra de título personalizada."""
from pathlib import Path

from PyQt6.QtCore import Qt, QSettings, QSize, QEvent
from PyQt6.QtGui import QFontDatabase, QCloseEvent
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QStackedWidget, QSizeGrip,
)

from app.config import APP_NAME, FONTS_DIR, STYLES_PATH
from app.ui.components.title_bar import TitleBarWidget
from app.ui.components.sidebar import SidebarWidget
from app.ui.components.toast_manager import ToastManager
from app.ui.tokens import MIN_WIN_W, MIN_WIN_H
from app.ui.views.home_view import HomeView
from app.ui.views.history_view import HistoryView
from app.ui.views.settings_view import SettingsView
from app.ui.views.about_view import AboutView
from app.utils.logger import get_logger
from app.utils.file_utils import generate_output_dir
from app.config import OUTPUTS_DIR

logger = get_logger()

_VIEW_NAMES = ["home", "history", "settings", "about"]


class MainWindow(QMainWindow):
    """Ventana principal de la aplicación InnoTech VideoTutor."""

    def __init__(self) -> None:
        super().__init__()
        self._worker = None
        self._ai_config = None
        self._setup_fonts()
        self._setup_frameless_window()
        self._load_styles()
        self._setup_ui()
        self._setup_taskbar_presence()
        self._restore_window_geometry()
        ToastManager.instance().set_parent(self)
        logger.info("Ventana principal iniciada")

    def _setup_fonts(self) -> None:
        for font_file in ("Inter-Regular.ttf", "Inter-Medium.ttf", "Inter-SemiBold.ttf"):
            path = FONTS_DIR / font_file
            if path.exists():
                QFontDatabase.addApplicationFont(str(path))

    def _setup_frameless_window(self) -> None:
        self.setWindowFlags(
            Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setMinimumSize(MIN_WIN_W, MIN_WIN_H)

    def _setup_taskbar_presence(self) -> None:
        from PyQt6.QtGui import QIcon
        from app.config import ICONS_DIR
        icon_path = ICONS_DIR / "app_logo.svg"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))
        self.setWindowTitle(APP_NAME)

    def _load_styles(self) -> None:
        try:
            if STYLES_PATH.exists():
                from PyQt6.QtWidgets import QApplication
                QApplication.instance().setStyleSheet(STYLES_PATH.read_text(encoding="utf-8"))
        except Exception as exc:
            logger.warning("No se pudo cargar el QSS: %s", exc)

    def _setup_ui(self) -> None:
        central = QWidget()
        central.setObjectName("centralWidget")
        self.setCentralWidget(central)

        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Barra de título
        self._title_bar = TitleBarWidget(self)
        main_layout.addWidget(self._title_bar)

        # Cuerpo: sidebar + contenido
        body = QWidget()
        body_layout = QHBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)

        self._sidebar = SidebarWidget()
        self._sidebar.navigation_requested.connect(self.navigate_to)
        body_layout.addWidget(self._sidebar)

        # Stack de vistas
        self._stack = QStackedWidget()
        body_layout.addWidget(self._stack)

        self._home_view = HomeView()
        self._history_view = HistoryView()
        self._settings_view = SettingsView()
        self._about_view = AboutView()

        for view in (self._home_view, self._history_view, self._settings_view, self._about_view):
            self._stack.addWidget(view)

        main_layout.addWidget(body)

        # Size grip para redimensionar desde esquina inferior derecha
        grip_container = QWidget()
        grip_layout = QHBoxLayout(grip_container)
        grip_layout.setContentsMargins(0, 0, 0, 0)
        grip_layout.addStretch()
        grip = QSizeGrip(self)
        grip.setFixedSize(16, 16)
        grip_layout.addWidget(grip)
        main_layout.addWidget(grip_container)

        # Conectar señales del home
        self._home_view.process_requested.connect(self._on_process_requested)
        self._home_view.cancel_requested.connect(self._on_cancel_requested)
        self._settings_view.config_saved.connect(self._on_config_saved)

        # Cargar config guardada
        self._ai_config = self._settings_view.get_current_config()

    def navigate_to(self, view_name: str) -> None:
        """Navega a la vista especificada."""
        index = _VIEW_NAMES.index(view_name) if view_name in _VIEW_NAMES else 0
        self._stack.setCurrentIndex(index)
        self._sidebar.set_active(view_name)
        if view_name == "history":
            self._history_view.refresh()

    def _on_process_requested(self, video_path: Path) -> None:
        """Muestra el preview, y si hay config de IA arranca el procesamiento."""
        # Mostrar preview con metadatos siempre
        try:
            from app.core.audio_extractor import AudioExtractor
            video_info = AudioExtractor().get_video_info(video_path)
            self._home_view.on_file_selected(video_path, video_info)
        except Exception:
            self._home_view.on_file_selected(video_path)

        if self._ai_config is None:
            ToastManager.instance().warning(
                "Configura una API key en Configuración para iniciar el procesamiento."
            )
            return

        from app.workers.processing_worker import ProcessingWorker

        output_dir = generate_output_dir(video_path.stem, OUTPUTS_DIR)
        self._home_view.on_processing_started()

        self._worker = ProcessingWorker(video_path, self._ai_config, output_dir)
        self._worker.progress_updated.connect(self._home_view.on_progress_updated)
        self._worker.stage_completed.connect(self._home_view.on_stage_completed)
        self._worker.processing_done.connect(self._home_view.on_processing_done)
        self._worker.processing_error.connect(self._home_view.on_processing_error)
        self._worker.processing_cancelled.connect(self._home_view.on_processing_cancelled)
        self._worker.start()

    def _on_cancel_requested(self) -> None:
        if self._worker and self._worker.isRunning():
            self._worker.cancel()

    def _on_config_saved(self, config) -> None:
        self._ai_config = config
        logger.info("Configuración de IA actualizada: %s", config.provider)

    def _restore_window_geometry(self) -> None:
        settings = QSettings("InnoTech", "VideoTutor")
        geometry = settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)
        else:
            self.resize(MIN_WIN_W, MIN_WIN_H)
            self._center_on_screen()

    def _center_on_screen(self) -> None:
        from PyQt6.QtWidgets import QApplication
        screen = QApplication.primaryScreen().availableGeometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)

    def _save_window_geometry(self) -> None:
        settings = QSettings("InnoTech", "VideoTutor")
        settings.setValue("geometry", self.saveGeometry())

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._worker and self._worker.isRunning():
            self._worker.cancel()
            self._worker.wait(3000)
        self._save_window_geometry()
        event.accept()

    def changeEvent(self, event: QEvent) -> None:
        super().changeEvent(event)
        if event.type() == QEvent.Type.WindowStateChange:
            self._title_bar.update_maximize_icon()
