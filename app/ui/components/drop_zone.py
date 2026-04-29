"""Zona de arrastrar y soltar videos con borde animado."""
from pathlib import Path
from typing import Literal

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QPainter, QPen, QColor
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QFileDialog

from app.config import SUPPORTED_VIDEO_FORMATS
from app.ui.tokens import (
    COLOR_BG_SURFACE, COLOR_ACCENT, COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY,
    COLOR_ERROR, RADIUS_XL, SPACE_LG, SPACE_MD, ICON_LG,
)
from app.ui.svg_helper import svg_icon


class DropZoneWidget(QWidget):
    """Zona de drag & drop para videos con estados visuales animados."""

    file_dropped = pyqtSignal(Path)
    browse_clicked = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._state: Literal["idle", "drag_over", "error", "loading"] = "idle"
        self._dash_offset = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._animate_dash)
        self._timer.start(50)
        self._setup_ui()
        self.setAcceptDrops(True)

    def _setup_ui(self) -> None:
        self.setMinimumSize(500, 280)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(SPACE_MD)

        self._icon_label = QLabel()
        self._icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._icon_label.setPixmap(svg_icon("action_upload", ICON_LG, COLOR_TEXT_SECONDARY).pixmap(ICON_LG, ICON_LG))

        self._title_label = QLabel("Arrastra tu video aquí")
        self._title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._title_label.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; font-size: 18px; font-weight: 600;")

        self._subtitle_label = QLabel("o haz click en el botón para explorar")
        self._subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._subtitle_label.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: 13px;")

        formats = ", ".join(sorted(SUPPORTED_VIDEO_FORMATS))
        self._formats_label = QLabel(f"Formatos soportados: {formats}")
        self._formats_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._formats_label.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: 11px;")

        self._browse_btn = QPushButton("  Explorar archivos")
        self._browse_btn.setIcon(svg_icon("action_open_folder", 16, "#FFFFFF"))
        self._browse_btn.setFixedSize(180, 40)
        self._browse_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._browse_btn.setStyleSheet(f"""
            QPushButton {{
                background: {COLOR_ACCENT};
                color: #FFFFFF;
                border-radius: 6px;
                font-weight: 600;
                font-size: 13px;
            }}
            QPushButton:hover {{ background: #EA6C0A; }}
            QPushButton:pressed {{ background: #C2560A; }}
        """)
        self._browse_btn.clicked.connect(self._on_browse)

        layout.addWidget(self._icon_label)
        layout.addWidget(self._title_label)
        layout.addWidget(self._subtitle_label)
        layout.addSpacing(SPACE_MD)
        layout.addWidget(self._browse_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addSpacing(SPACE_MD)
        layout.addWidget(self._formats_label)

    def set_state(self, state: Literal["idle", "drag_over", "error", "loading"]) -> None:
        self._state = state
        self.update()

        if state == "error":
            self._title_label.setText("Formato no soportado")
            self._title_label.setStyleSheet(f"color: {COLOR_ERROR}; font-size: 18px; font-weight: 600;")
            QTimer.singleShot(2000, lambda: self.set_state("idle"))
        elif state == "idle":
            self._title_label.setText("Arrastra tu video aquí")
            self._title_label.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; font-size: 18px; font-weight: 600;")

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect().adjusted(2, 2, -2, -2)
        color = {
            "idle": QColor(COLOR_TEXT_SECONDARY),
            "drag_over": QColor(COLOR_ACCENT),
            "error": QColor(COLOR_ERROR),
            "loading": QColor(COLOR_TEXT_SECONDARY),
        }.get(self._state, QColor(COLOR_TEXT_SECONDARY))

        pen = QPen(color, 2, Qt.PenStyle.DashLine if self._state not in ("drag_over",) else Qt.PenStyle.SolidLine)
        pen.setDashOffset(self._dash_offset)
        painter.setPen(pen)

        bg = QColor(COLOR_ACCENT)
        bg.setAlpha(20 if self._state == "drag_over" else 0)
        painter.setBrush(bg)
        painter.drawRoundedRect(rect, RADIUS_XL, RADIUS_XL)

    def _animate_dash(self) -> None:
        if self._state == "idle":
            self._dash_offset = (self._dash_offset + 1) % 20
            self.update()

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            paths = [Path(u.toLocalFile()) for u in event.mimeData().urls()]
            if any(p.suffix.lower() in SUPPORTED_VIDEO_FORMATS for p in paths):
                event.acceptProposedAction()
                self.set_state("drag_over")
                return
        event.ignore()

    def dragLeaveEvent(self, event) -> None:
        self.set_state("idle")

    def dropEvent(self, event: QDropEvent) -> None:
        self.set_state("idle")
        for url in event.mimeData().urls():
            path = Path(url.toLocalFile())
            if self._validate_dropped_file(path):
                self.file_dropped.emit(path)
                return
        self.set_state("error")

    def _validate_dropped_file(self, path: Path) -> bool:
        return path.exists() and path.is_file() and path.suffix.lower() in SUPPORTED_VIDEO_FORMATS

    def _on_browse(self) -> None:
        exts = " ".join(f"*{e}" for e in SUPPORTED_VIDEO_FORMATS)
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Seleccionar video",
            "",
            f"Videos ({exts});;Todos los archivos (*.*)",
        )
        if file_path:
            self.file_dropped.emit(Path(file_path))
