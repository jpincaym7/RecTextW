"""Barra de progreso por etapas con nombres, iconos y animación."""
from PyQt6.QtCore import Qt, QPropertyAnimation, QRect, pyqtProperty
from PyQt6.QtGui import QPainter, QColor
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea

from app.ui.tokens import (
    COLOR_BG_CARD, COLOR_ACCENT, COLOR_SUCCESS, COLOR_ERROR,
    COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY, COLOR_TEXT_MUTED,
    SPACE_SM, SPACE_MD, SPACE_XS, RADIUS_MD,
)
from app.ui.svg_helper import svg_icon


_STEPS = [
    ("metadata",   "Analizando video"),
    ("audio",      "Extrayendo audio"),
    ("model",      "Cargando Whisper"),
    ("transcribe", "Transcribiendo"),
    ("summary",    "Generando resumen"),
    ("titles",     "Identificando título"),
    ("script",     "Organizando guión"),
    ("extras",     "Generando insumos"),
    ("export",     "Exportando documentos"),
    ("save",       "Guardando historial"),
]


class _SpinnerWidget(QWidget):
    """Spinner rotatorio animado via QPainter."""

    def __init__(self, size: int = 20, parent=None) -> None:
        super().__init__(parent)
        self._angle = 0
        self._size = size
        self.setFixedSize(size, size)
        self._anim = QPropertyAnimation(self, b"rotation_angle", self)
        self._anim.setStartValue(0)
        self._anim.setEndValue(360)
        self._anim.setDuration(800)
        self._anim.setLoopCount(-1)
        self._anim.start()

    @pyqtProperty(int)
    def rotation_angle(self) -> int:
        return self._angle

    @rotation_angle.setter
    def rotation_angle(self, val: int) -> None:
        self._angle = val
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.translate(self._size / 2, self._size / 2)
        painter.rotate(self._angle)
        from PyQt6.QtGui import QPen
        from PyQt6.QtCore import QRectF
        pen = QPen(QColor(COLOR_ACCENT), 2)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        r = self._size / 2 - 2
        painter.drawArc(QRectF(-r, -r, r * 2, r * 2), 0 * 16, 270 * 16)


class StepProgressBar(QWidget):
    """Barra de progreso por etapas con estado visual por paso."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._step_widgets: dict[str, dict] = {}
        self._setup_ui()

    def _setup_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(SPACE_XS)

        # Barra de progreso numérica
        self._progress_label = QLabel("0%")
        self._progress_label.setStyleSheet(f"color: {COLOR_ACCENT}; font-size: 13px; font-weight: 600;")
        self._message_label = QLabel("Listo para procesar")
        self._message_label.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: 12px;")

        top_row = QHBoxLayout()
        top_row.addWidget(self._progress_label)
        top_row.addWidget(self._message_label)
        top_row.addStretch()
        outer.addLayout(top_row)

        # Pasos
        for key, label in _STEPS:
            row = QHBoxLayout()
            row.setSpacing(SPACE_SM)

            indicator = QLabel()
            indicator.setFixedSize(20, 20)
            indicator.setPixmap(svg_icon("status_check", 20, COLOR_TEXT_MUTED).pixmap(20, 20))

            spinner = _SpinnerWidget(20)
            spinner.hide()

            lbl = QLabel(label)
            lbl.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: 12px;")

            row.addWidget(indicator)
            row.addWidget(spinner)
            row.addWidget(lbl)
            row.addStretch()

            self._step_widgets[key] = {
                "indicator": indicator,
                "spinner": spinner,
                "label": lbl,
            }
            outer.addLayout(row)

    def update_progress(self, overall_percent: float, stage_name: str, message: str) -> None:
        """Actualiza el progreso global y el estado del paso activo."""
        self._progress_label.setText(f"{overall_percent:.0f}%")
        self._message_label.setText(message)

        if stage_name in self._step_widgets:
            w = self._step_widgets[stage_name]
            w["indicator"].hide()
            w["spinner"].show()
            w["label"].setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; font-size: 12px; font-weight: 600;")

    def mark_step_complete(self, step_key: str) -> None:
        if step_key not in self._step_widgets:
            return
        w = self._step_widgets[step_key]
        w["spinner"].hide()
        w["indicator"].show()
        w["indicator"].setPixmap(svg_icon("status_check", 20, COLOR_SUCCESS).pixmap(20, 20))
        w["label"].setStyleSheet(f"color: {COLOR_SUCCESS}; font-size: 12px;")

    def mark_step_error(self, step_key: str, error_msg: str = "") -> None:
        if step_key not in self._step_widgets:
            return
        w = self._step_widgets[step_key]
        w["spinner"].hide()
        w["indicator"].show()
        w["indicator"].setPixmap(svg_icon("status_error", 20, COLOR_ERROR).pixmap(20, 20))
        w["label"].setStyleSheet(f"color: {COLOR_ERROR}; font-size: 12px;")

    def reset(self) -> None:
        self._progress_label.setText("0%")
        self._message_label.setText("Listo para procesar")
        for w in self._step_widgets.values():
            w["spinner"].hide()
            w["indicator"].show()
            w["indicator"].setPixmap(svg_icon("status_check", 20, COLOR_TEXT_MUTED).pixmap(20, 20))
            w["label"].setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: 12px;")
