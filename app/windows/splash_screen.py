"""Splash screen con verificaciones de prerequisites y descarga automática."""
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QApplication,
)

from app.ui.tokens import (
    COLOR_BG_PRIMARY, COLOR_BG_CARD, COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY,
    COLOR_SUCCESS, COLOR_ERROR, COLOR_ACCENT, RADIUS_MD, SPACE_MD, SPACE_LG, ICON_LG,
)
from app.ui.svg_helper import svg_icon


class _FFmpegDownloadWorker(QThread):
    """Descarga FFmpeg estático automáticamente en un hilo separado."""
    progress_updated = pyqtSignal(float, str)
    download_done    = pyqtSignal()
    download_error   = pyqtSignal(str)

    def run(self) -> None:
        try:
            from app.utils.ffmpeg_check import download_ffmpeg
            download_ffmpeg(
                progress_callback=lambda p, msg: self.progress_updated.emit(p, msg)
            )
            self.download_done.emit()
        except Exception as exc:
            self.download_error.emit(str(exc))


class _CheckWorker(QThread):
    """Ejecuta las verificaciones de prerequisites en un hilo separado."""
    check_result     = pyqtSignal(str, bool, str)  # (nombre, ok, mensaje)
    all_done         = pyqtSignal(bool)
    ffmpeg_needed    = pyqtSignal()                # FFmpeg no encontrado → descargar
    whisper_needed   = pyqtSignal()                # Modelo no descargado → descargar

    def run(self) -> None:
        # 1. FFmpeg — si no está, emite señal para descarga automática y detiene
        try:
            from app.utils.ffmpeg_check import find_ffmpeg, validate_ffmpeg
            ffmpeg = find_ffmpeg()
            ok = ffmpeg is not None and validate_ffmpeg(ffmpeg)
            if ok:
                self.check_result.emit("FFmpeg", True, str(ffmpeg))
            else:
                self.check_result.emit("FFmpeg", False, "Descargando automáticamente...")
                self.ffmpeg_needed.emit()
                return
        except Exception as exc:
            self.check_result.emit("FFmpeg", False, str(exc))
            self.ffmpeg_needed.emit()
            return

        self._run_remaining_checks()

    def run_after_ffmpeg(self) -> None:
        """Reanuda verificaciones después de que FFmpeg fue descargado."""
        self._run_remaining_checks()

    def _run_remaining_checks(self) -> None:
        all_ok = True

        # 2. Directorio de datos
        try:
            from app.config import DATA_DIR
            from app.utils.validators import is_writable_dir
            ok = is_writable_dir(DATA_DIR)
            self.check_result.emit(
                "Directorio de datos", ok,
                str(DATA_DIR) if ok else "Sin permisos de escritura"
            )
            if not ok:
                all_ok = False
        except Exception as exc:
            self.check_result.emit("Directorio de datos", False, str(exc))
            all_ok = False

        # 3. Base de datos
        try:
            from app.config import DB_PATH
            from app.db.database import initialize_database
            initialize_database(DB_PATH)
            self.check_result.emit("Base de datos", True, "OK")
        except Exception as exc:
            self.check_result.emit("Base de datos", False, str(exc))
            all_ok = False

        # 4. Modelo Whisper
        try:
            from app.utils.whisper_check import is_model_available
            ok = is_model_available("medium")
            msg = "Modelo listo" if ok else "Descargando automáticamente..."
            self.check_result.emit("Whisper medium", ok, msg)
            if not ok:
                self.whisper_needed.emit()
                return
        except Exception as exc:
            self.check_result.emit("Whisper medium", False, str(exc))
            self.whisper_needed.emit()
            return

        # 5. Logger
        try:
            from app.utils.logger import setup_logger
            setup_logger()
            self.check_result.emit("Logger", True, "Activo")
        except Exception as exc:
            self.check_result.emit("Logger", False, str(exc))

        self.all_done.emit(all_ok)


class _ResumeWorker(QThread):
    """Reanuda las verificaciones restantes después de una descarga."""
    check_result   = pyqtSignal(str, bool, str)
    all_done       = pyqtSignal(bool)
    whisper_needed = pyqtSignal()

    def run(self) -> None:
        # Directorio de datos
        try:
            from app.config import DATA_DIR
            from app.utils.validators import is_writable_dir
            ok = is_writable_dir(DATA_DIR)
            self.check_result.emit("Directorio de datos", ok, str(DATA_DIR) if ok else "Sin permisos de escritura")
        except Exception as exc:
            self.check_result.emit("Directorio de datos", False, str(exc))

        # Base de datos
        try:
            from app.config import DB_PATH
            from app.db.database import initialize_database
            initialize_database(DB_PATH)
            self.check_result.emit("Base de datos", True, "OK")
        except Exception as exc:
            self.check_result.emit("Base de datos", False, str(exc))

        # Whisper
        try:
            from app.utils.whisper_check import is_model_available
            ok = is_model_available("medium")
            self.check_result.emit("Whisper medium", ok, "Modelo listo" if ok else "Descargando automáticamente...")
            if not ok:
                self.whisper_needed.emit()
                return
        except Exception as exc:
            self.check_result.emit("Whisper medium", False, str(exc))
            self.whisper_needed.emit()
            return

        # Logger
        try:
            from app.utils.logger import setup_logger
            setup_logger()
            self.check_result.emit("Logger", True, "Activo")
        except Exception as exc:
            self.check_result.emit("Logger", False, str(exc))

        self.all_done.emit(True)


class SplashScreen(QWidget):
    """Pantalla de inicio con verificaciones y descargas automáticas."""

    ready = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self._setup_ui()
        self._start_checks()

    def _setup_ui(self) -> None:
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setFixedSize(480, 400)
        self.setStyleSheet(f"background-color: {COLOR_BG_PRIMARY};")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACE_LG, SPACE_LG, SPACE_LG, SPACE_LG)
        layout.setSpacing(SPACE_MD)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Logo + nombre
        logo_lbl = QLabel()
        logo_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_lbl.setPixmap(svg_icon("app_logo", 48, COLOR_ACCENT).pixmap(48, 48))

        name_lbl = QLabel("InnoTech VideoTutor")
        name_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_lbl.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; font-size: 20px; font-weight: 600;")

        self._loading_lbl = QLabel("Iniciando aplicación...")
        self._loading_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._loading_lbl.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: 12px;")

        layout.addWidget(logo_lbl)
        layout.addWidget(name_lbl)
        layout.addWidget(self._loading_lbl)
        layout.addSpacing(SPACE_MD)

        # Filas de verificación
        self._check_rows: dict[str, tuple[QLabel, QLabel]] = {}
        checks_container = QWidget()
        checks_container.setStyleSheet(
            f"background: {COLOR_BG_CARD}; border-radius: {RADIUS_MD}px;"
        )
        checks_layout = QVBoxLayout(checks_container)
        checks_layout.setContentsMargins(SPACE_MD, SPACE_MD, SPACE_MD, SPACE_MD)
        checks_layout.setSpacing(8)

        for check_name in ["FFmpeg", "Directorio de datos", "Base de datos", "Whisper medium", "Logger"]:
            row = QHBoxLayout()

            status_lbl = QLabel()
            status_lbl.setFixedSize(20, 20)
            status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            status_lbl.setPixmap(svg_icon("status_loading", 16, COLOR_TEXT_SECONDARY).pixmap(16, 16))

            name_lbl_w = QLabel(check_name)
            name_lbl_w.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: 12px;")

            detail_lbl = QLabel("Pendiente")
            detail_lbl.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: 11px;")
            detail_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)

            row.addWidget(status_lbl)
            row.addWidget(name_lbl_w)
            row.addStretch()
            row.addWidget(detail_lbl)
            checks_layout.addLayout(row)

            self._check_rows[check_name] = (status_lbl, detail_lbl)

        layout.addWidget(checks_container)

        # Botón de salida (solo para errores irrecuperables)
        self._exit_btn = QPushButton("Salir")
        self._exit_btn.setFixedHeight(40)
        self._exit_btn.hide()
        self._exit_btn.setStyleSheet(f"""
            QPushButton {{
                background: {COLOR_ERROR};
                color: white;
                border-radius: 6px;
                font-weight: 600;
            }}
            QPushButton:hover {{ background: #DC2626; }}
        """)
        self._exit_btn.clicked.connect(QApplication.quit)
        layout.addWidget(self._exit_btn)
        layout.addStretch()

        self._center_on_screen()

    def _center_on_screen(self) -> None:
        screen = QApplication.primaryScreen().availableGeometry()
        self.move(
            (screen.width() - self.width()) // 2,
            (screen.height() - self.height()) // 2,
        )

    # ─── Fase 1: verificaciones iniciales ────────────────────────────────────

    def _start_checks(self) -> None:
        self._worker = _CheckWorker()
        self._worker.check_result.connect(self._on_check_result)
        self._worker.all_done.connect(self._on_all_done)
        self._worker.ffmpeg_needed.connect(self._start_ffmpeg_download)
        self._worker.whisper_needed.connect(self._start_whisper_download)
        self._worker.start()

    def _on_check_result(self, name: str, ok: bool, message: str) -> None:
        if name not in self._check_rows:
            return
        status_lbl, detail_lbl = self._check_rows[name]
        icon_name = "status_check" if ok else "status_error"
        icon_color = COLOR_SUCCESS if ok else COLOR_ERROR
        status_lbl.setPixmap(svg_icon(icon_name, 16, icon_color).pixmap(16, 16))
        detail_lbl.setText(message[:52] + "…" if len(message) > 52 else message)
        self._loading_lbl.setText(f"Verificando {name}...")

    def _on_all_done(self, all_ok: bool) -> None:
        if all_ok:
            self._loading_lbl.setText("Iniciando...")
            QTimer.singleShot(400, self._launch_main)
        else:
            self._loading_lbl.setText("Error al iniciar — revisa el registro de errores")
            self._loading_lbl.setStyleSheet(f"color: {COLOR_ERROR}; font-size: 12px;")
            self._exit_btn.show()

    # ─── Descarga automática de FFmpeg ────────────────────────────────────────

    def _start_ffmpeg_download(self) -> None:
        self._loading_lbl.setText("Descargando FFmpeg (~80 MB)... primera vez solamente")
        self._ffmpeg_dl = _FFmpegDownloadWorker()
        self._ffmpeg_dl.progress_updated.connect(self._on_ffmpeg_progress)
        self._ffmpeg_dl.download_done.connect(self._on_ffmpeg_done)
        self._ffmpeg_dl.download_error.connect(self._on_ffmpeg_error)
        self._ffmpeg_dl.start()

    def _on_ffmpeg_progress(self, _pct: float, msg: str) -> None:
        self._loading_lbl.setText(msg)

    def _on_ffmpeg_done(self) -> None:
        status_lbl, detail_lbl = self._check_rows["FFmpeg"]
        status_lbl.setPixmap(svg_icon("status_check", 16, COLOR_SUCCESS).pixmap(16, 16))
        detail_lbl.setText("Instalado automáticamente")
        self._loading_lbl.setText("FFmpeg listo. Continuando...")
        # Reanudar el resto de verificaciones
        self._resume = _ResumeWorker()
        self._resume.check_result.connect(self._on_check_result)
        self._resume.all_done.connect(self._on_all_done)
        self._resume.whisper_needed.connect(self._start_whisper_download)
        self._resume.start()

    def _on_ffmpeg_error(self, error: str) -> None:
        status_lbl, detail_lbl = self._check_rows["FFmpeg"]
        status_lbl.setPixmap(svg_icon("status_error", 16, COLOR_ERROR).pixmap(16, 16))
        detail_lbl.setText("Error de descarga")
        self._loading_lbl.setText(f"No se pudo descargar FFmpeg: {error}")
        self._loading_lbl.setStyleSheet(f"color: {COLOR_ERROR}; font-size: 12px;")
        self._exit_btn.show()

    # ─── Descarga automática de Whisper ───────────────────────────────────────

    def _start_whisper_download(self) -> None:
        self._loading_lbl.setText("Descargando modelo Whisper medium (~1.5 GB)... primera vez solamente")
        from app.workers.download_worker import ModelDownloadWorker
        self._whisper_dl = ModelDownloadWorker()
        self._whisper_dl.progress_updated.connect(self._on_whisper_progress)
        self._whisper_dl.download_done.connect(self._on_whisper_done)
        self._whisper_dl.download_error.connect(self._on_whisper_error)
        self._whisper_dl.start()

    def _on_whisper_progress(self, _pct: float, msg: str) -> None:
        self._loading_lbl.setText(msg)

    def _on_whisper_done(self) -> None:
        status_lbl, detail_lbl = self._check_rows["Whisper medium"]
        status_lbl.setPixmap(svg_icon("status_check", 16, COLOR_SUCCESS).pixmap(16, 16))
        detail_lbl.setText("Descargado")
        # Finalizar logger y lanzar
        try:
            from app.utils.logger import setup_logger
            setup_logger()
            s, d = self._check_rows["Logger"]
            s.setPixmap(svg_icon("status_check", 16, COLOR_SUCCESS).pixmap(16, 16))
            d.setText("Activo")
        except Exception:
            pass
        self._on_all_done(True)

    def _on_whisper_error(self, error: str) -> None:
        status_lbl, detail_lbl = self._check_rows["Whisper medium"]
        status_lbl.setPixmap(svg_icon("status_error", 16, COLOR_ERROR).pixmap(16, 16))
        detail_lbl.setText("Error de descarga")
        self._loading_lbl.setText(f"No se pudo descargar el modelo: {error}")
        self._loading_lbl.setStyleSheet(f"color: {COLOR_ERROR}; font-size: 12px;")
        self._exit_btn.show()

    # ─── Launch ───────────────────────────────────────────────────────────────

    def _launch_main(self) -> None:
        self.ready.emit()
        self.close()
