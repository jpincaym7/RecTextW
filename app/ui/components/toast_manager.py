"""Sistema de notificaciones flotantes (toasts) en la esquina inferior derecha."""
from typing import Literal
from collections import deque

from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QPoint, QEasingCurve
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QApplication

from app.ui.tokens import (
    COLOR_SUCCESS, COLOR_ERROR, COLOR_WARNING, COLOR_INFO,
    COLOR_TEXT_PRIMARY, RADIUS_MD, SPACE_SM, SPACE_MD,
)
from app.ui.svg_helper import svg_icon


class _ToastWidget(QWidget):
    """Una notificación individual flotante."""

    def __init__(
        self,
        message: str,
        variant: Literal["success", "error", "warning", "info"],
        parent: QWidget,
    ) -> None:
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.ToolTip)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._setup_ui(message, variant)

    def _setup_ui(self, message: str, variant: str) -> None:
        variants = {
            "success": (COLOR_SUCCESS, "check_circle",    "rgba(34,197,94,0.13)"),
            "error":   (COLOR_ERROR,   "x_circle",        "rgba(239,68,68,0.13)"),
            "warning": (COLOR_WARNING, "warning_triangle","rgba(234,179,8,0.13)"),
            "info":    (COLOR_INFO,    "info_circle",     "rgba(59,130,246,0.13)"),
        }
        color, icon_name, bg_tint = variants.get(variant, variants["info"])

        self.setObjectName("toast")
        self.setStyleSheet(f"""
            #toast {{
                background-color: {bg_tint};
                border-radius: {RADIUS_MD}px;
                border: 1px solid {color};
                border-left: 4px solid {color};
            }}
        """)
        self.setFixedWidth(360)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(SPACE_MD, SPACE_SM, SPACE_MD, SPACE_SM)
        layout.setSpacing(SPACE_SM)

        icon_lbl = QLabel()
        icon_lbl.setPixmap(svg_icon(icon_name, 20, color).pixmap(20, 20))
        icon_lbl.setFixedSize(20, 20)

        msg_lbl = QLabel(message)
        msg_lbl.setWordWrap(True)
        msg_lbl.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; font-size: 13px;")

        layout.addWidget(icon_lbl, alignment=Qt.AlignmentFlag.AlignTop)
        layout.addWidget(msg_lbl)
        self.adjustSize()


class ToastManager:
    """Singleton que gestiona la cola de notificaciones flotantes."""

    _instance: "ToastManager | None" = None

    @classmethod
    def instance(cls) -> "ToastManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self) -> None:
        self._parent: QWidget | None = None
        self._active: list[_ToastWidget] = []
        self._queue: deque = deque()

    def set_parent(self, parent: QWidget) -> None:
        """Establece la ventana padre donde se anclan los toasts."""
        self._parent = parent

    def success(self, message: str, duration_ms: int = 4000) -> None:
        self._show(message, "success", duration_ms)

    def error(self, message: str, duration_ms: int = 6000) -> None:
        self._show(message, "error", duration_ms)

    def warning(self, message: str, duration_ms: int = 5000) -> None:
        self._show(message, "warning", duration_ms)

    def info(self, message: str, duration_ms: int = 4000) -> None:
        self._show(message, "info", duration_ms)

    def _show(self, message: str, variant: str, duration_ms: int) -> None:
        if self._parent is None:
            return
        if len(self._active) >= 3:
            self._queue.append((message, variant, duration_ms))
            return

        toast = _ToastWidget(message, variant, self._parent)
        toast.show()
        self._active.append(toast)
        self._position_toasts()

        # Animación slide-up
        start_y = self._parent.height()
        end_pos = toast.pos()
        anim = QPropertyAnimation(toast, b"pos", toast)
        anim.setStartValue(QPoint(end_pos.x(), start_y))
        anim.setEndValue(end_pos)
        anim.setDuration(250)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.start()

        QTimer.singleShot(duration_ms, lambda t=toast: self._remove(t))

    def _remove(self, toast: _ToastWidget) -> None:
        if toast in self._active:
            self._active.remove(toast)
        toast.hide()
        toast.deleteLater()
        self._position_toasts()
        if self._queue:
            msg, variant, duration = self._queue.popleft()
            self._show(msg, variant, duration)

    def _position_toasts(self) -> None:
        if not self._parent:
            return
        margin = 20
        spacing = 8
        parent_rect = self._parent.rect()
        y = self._parent.mapToGlobal(parent_rect.bottomRight()).y() - margin
        x = self._parent.mapToGlobal(parent_rect.bottomRight()).x() - 360 - margin

        for toast in reversed(self._active):
            if toast.isVisible():
                toast.move(x, y - toast.height())
                y -= toast.height() + spacing
