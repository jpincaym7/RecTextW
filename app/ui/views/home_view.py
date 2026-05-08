"""Vista principal: carga de video, procesamiento y resultados."""
import os
from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QStackedWidget,
    QLabel, QTabWidget, QPlainTextEdit,
    QApplication, QScrollArea,
)

from app.ui.components.drop_zone import DropZoneWidget
from app.ui.components.video_preview import VideoPreviewWidget
from app.ui.components.step_progress import StepProgressBar
from app.ui.components.icon_button import IconButton
from app.ui.components.card_widget import CardWidget
from app.ui.components.tag_badge import TagBadge
from app.ui.components.toast_manager import ToastManager
from app.ui.components.privileges_dialog import PrivilegesDialog
from app.ui.tokens import (
    COLOR_BG_SURFACE, COLOR_TEXT_PRIMARY, SPACE_MD, SPACE_LG, SPACE_SM,
)


class HomeView(QWidget):
    """Vista principal con 3 sub-estados: vacío, con video, resultados."""

    file_selected     = pyqtSignal(Path)   # solo selección — muestra preview
    process_requested = pyqtSignal(Path)   # botón pulsado — inicia procesamiento
    cancel_requested  = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._video_path: Path | None = None
        self._output_dir: Path | None = None
        self._ai_config = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        self.setObjectName("homeView")
        self.setStyleSheet(f"#homeView {{ background: {COLOR_BG_SURFACE}; }}")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(SPACE_LG, SPACE_LG, SPACE_LG, SPACE_LG)
        main_layout.setSpacing(SPACE_LG)

        self._stack = QStackedWidget()
        main_layout.addWidget(self._stack)

        self._stack.addWidget(self._build_empty_state())   # 0
        self._stack.addWidget(self._build_video_state())   # 1
        self._stack.addWidget(self._build_results_state()) # 2

        self._stack.setCurrentIndex(0)

    # ─── Estado 0: Vacío ──────────────────────────────────────────────────────

    def _build_empty_state(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._drop_zone = DropZoneWidget()
        self._drop_zone.file_dropped.connect(self._on_file_dropped)
        layout.addWidget(self._drop_zone, alignment=Qt.AlignmentFlag.AlignCenter)
        return w

    # ─── Estado 1: Con video ──────────────────────────────────────────────────

    def _build_video_state(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(SPACE_MD)

        # Preview del video — tamaño fijo, sin stretch
        self._video_preview = VideoPreviewWidget()
        layout.addWidget(self._video_preview)

        # Barra de progreso (oculta inicialmente)
        progress_card = CardWidget("Progreso del procesamiento")
        self._step_progress = StepProgressBar()
        scroll = QScrollArea()
        scroll.setWidget(self._step_progress)
        scroll.setWidgetResizable(True)
        scroll.setFixedHeight(260)
        progress_card.layout().addWidget(scroll)
        self._progress_card = progress_card
        progress_card.hide()
        layout.addWidget(progress_card)

        # Botones de acción
        btn_row = QHBoxLayout()

        change_btn = IconButton("action_upload", "  Cambiar video", "ghost")
        change_btn.setFixedHeight(44)
        change_btn.clicked.connect(lambda: self._stack.setCurrentIndex(0))

        self._cancel_btn = IconButton("action_cancel", "  Cancelar", "secondary")
        self._cancel_btn.setFixedHeight(44)
        self._cancel_btn.hide()
        self._cancel_btn.clicked.connect(self.cancel_requested)

        btn_row.addStretch()
        btn_row.addWidget(change_btn)
        btn_row.addWidget(self._cancel_btn)
        layout.addLayout(btn_row)
        layout.addStretch()   # absorbe el espacio extra al maximizar
        return w

    # ─── Estado 2: Resultados ─────────────────────────────────────────────────

    def _build_results_state(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setSpacing(SPACE_MD)

        # Cabecera con título y palabras clave
        header = QHBoxLayout()
        self._result_title = QLabel("Procesamiento completado")
        self._result_title.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; font-size: 18px; font-weight: 600;")
        header.addWidget(self._result_title)
        header.addStretch()

        open_folder_btn = IconButton("action_open_folder", "  Abrir carpeta", "ghost")
        open_folder_btn.clicked.connect(self._open_output_folder)
        header.addWidget(open_folder_btn)

        open_report_btn = IconButton("file_doc", "  Abrir informe", "primary")
        open_report_btn.clicked.connect(self._open_complete_report)
        header.addWidget(open_report_btn)

        new_btn = IconButton("nav_home", "  Nuevo procesamiento", "secondary")
        new_btn.clicked.connect(lambda: self._stack.setCurrentIndex(0))
        header.addWidget(new_btn)

        layout.addLayout(header)

        # Palabras clave
        self._tags_row = QHBoxLayout()
        self._tags_row.setSpacing(SPACE_SM)
        self._tags_row.addStretch()
        tags_widget = QWidget()
        tags_widget.setLayout(self._tags_row)
        layout.addWidget(tags_widget)

        # Tabs de resultados
        self._tabs = QTabWidget()
        self._tabs.setDocumentMode(True)

        for tab_name, attr in [
            ("Transcripción", "_tab_transcription"),
            ("Resumen",       "_tab_summary"),
            ("Guión Base",    "_tab_script"),
        ]:
            tab = self._make_text_tab()
            setattr(self, attr, tab)
            self._tabs.addTab(tab, tab_name)

        layout.addWidget(self._tabs)
        return w

    def _make_text_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, SPACE_SM, 0, 0)

        text_edit = QPlainTextEdit()
        text_edit.setReadOnly(True)
        layout.addWidget(text_edit)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        copy_btn = IconButton("action_copy", "  Copiar", "ghost")
        copy_btn.clicked.connect(lambda: self._copy_text(text_edit))
        btn_row.addWidget(copy_btn)
        layout.addLayout(btn_row)

        w._text_edit = text_edit
        return w

    # ─── Slots públicos ───────────────────────────────────────────────────────

    def on_file_selected(self, video_path: Path, video_info=None) -> None:
        """Carga un video y cambia al estado 1."""
        self._video_path = video_path
        self._video_preview.load_video(video_path, video_info)
        self._step_progress.reset()
        self._progress_card.hide()
        self._cancel_btn.hide()
        self._stack.setCurrentIndex(1)

    def on_processing_started(self) -> None:
        self._progress_card.show()
        self._cancel_btn.show()

    def on_progress_updated(self, percent: float, stage: str, message: str) -> None:
        self._step_progress.update_progress(percent, stage, message)

    def on_stage_completed(self, stage: str) -> None:
        self._step_progress.mark_step_complete(stage)

    def on_processing_done(self, result: dict) -> None:
        """Muestra los resultados del procesamiento."""
        self._output_dir = Path(result.get("output_dir", ""))

        self._result_title.setText(result.get("titulo", "Procesamiento completado"))

        # Palabras clave como tags
        for i in reversed(range(self._tags_row.count())):
            item = self._tags_row.itemAt(i)
            if item and item.widget():
                item.widget().deleteLater()

        for kw in result.get("palabras_clave", []):
            self._tags_row.insertWidget(0, TagBadge(kw))

        # Texto en tabs
        self._tab_transcription._text_edit.setPlainText(result.get("timestamped_text", ""))
        self._tab_summary._text_edit.setPlainText(result.get("resumen", ""))
        self._tab_script._text_edit.setPlainText(result.get("guion_base", ""))

        self._stack.setCurrentIndex(2)
        ToastManager.instance().success("Procesamiento completado exitosamente")

    def on_processing_error(self, stage: str, message: str) -> None:
        self._step_progress.mark_step_error(stage, message)
        self._cancel_btn.hide()

        _PERM_KEYWORDS = (
            "permissionerror", "permission denied", "access is denied",
            "winerror 5", "acceso denegado", "sin permisos",
            "espacio en disco insuficiente", "no space left",
        )
        if any(k in message.lower() for k in _PERM_KEYWORDS):
            dlg = PrivilegesDialog(message, parent=self)
            dlg.exec()
        else:
            ToastManager.instance().error(f"Error en etapa '{stage}': {message}")

    def on_processing_cancelled(self) -> None:
        self._step_progress.reset()
        self._progress_card.hide()
        self._cancel_btn.hide()
        ToastManager.instance().warning("Procesamiento cancelado")

    def set_ai_config(self, config) -> None:
        self._ai_config = config

    # ─── Privados ─────────────────────────────────────────────────────────────

    def _on_file_dropped(self, path: Path) -> None:
        self._video_path = path
        self.process_requested.emit(path)

    def _open_output_folder(self) -> None:
        if self._output_dir and self._output_dir.exists():
            os.startfile(str(self._output_dir))

    def _open_complete_report(self) -> None:
        if not self._output_dir:
            return
        path = self._output_dir / "informe_completo.docx"
        if path.exists():
            os.startfile(str(path))
        else:
            ToastManager.instance().error("No se encontró el informe completo")

    def _copy_text(self, text_edit: QPlainTextEdit) -> None:
        QApplication.clipboard().setText(text_edit.toPlainText())
        ToastManager.instance().success("Texto copiado al portapapeles")
