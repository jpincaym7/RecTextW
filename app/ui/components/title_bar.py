"""Barra de título personalizada sin marco nativo de Windows."""
from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtGui import QMouseEvent
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton

from app.config import APP_NAME
from app.ui.tokens import (
    TOOLBAR_H, SPACE_SM, SPACE_MD,
    COLOR_BG_PRIMARY, COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY, COLOR_ERROR,
)
from app.ui.svg_helper import svg_icon


class TitleBarWidget(QWidget):
    """Barra de título personalizada con drag, doble clic para maximizar y botones de ventana."""

    def __init__(self, parent: QWidget, title: str = APP_NAME) -> None:
        super().__init__(parent)
        self._parent_window = parent
        self._drag_pos: QPoint | None = None
        self._setup_ui(title)

    def _setup_ui(self, title: str) -> None:
        self.setFixedHeight(TOOLBAR_H)
        self.setObjectName("titleBar")
        self.setStyleSheet(f"""
            #titleBar {{
                background-color: {COLOR_BG_PRIMARY};
                border-bottom: 1px solid #1E3A5F;
            }}
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(SPACE_MD, 0, SPACE_SM, 0)
        layout.setSpacing(SPACE_SM)

        # Logo + título
        logo_label = QLabel()
        logo_label.setPixmap(svg_icon("app_logo", 24, COLOR_TEXT_PRIMARY).pixmap(24, 24))

        title_label = QLabel(title)
        title_label.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; font-weight: 600; font-size: 14px;")

        layout.addWidget(logo_label)
        layout.addWidget(title_label)
        layout.addSpacing(SPACE_SM)

        # Subtítulo (archivo activo)
        self._subtitle = QLabel("")
        self._subtitle.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: 12px;")
        layout.addWidget(self._subtitle)

        layout.addStretch()

        # Botones de ventana
        for icon_name, slot, is_close in [
            ("window_minimize", self._on_minimize, False),
            ("window_maximize", self._on_maximize_restore, False),
            ("window_close", self._on_close, True),
        ]:
            btn = self._make_window_btn(icon_name, slot, is_close)
            layout.addWidget(btn)
            setattr(self, f"_btn_{icon_name}", btn)

    def _make_window_btn(self, icon_name: str, slot, is_close: bool) -> QPushButton:
        btn = QPushButton()
        btn.setFixedSize(32, 32)
        btn.setIcon(svg_icon(icon_name, 16, COLOR_TEXT_PRIMARY))
        btn.setCursor(Qt.CursorShape.ArrowCursor)
        hover_bg = "#EF4444" if is_close else "rgba(255,255,255,0.08)"
        btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: none;
                border-radius: 6px;
            }}
            QPushButton:hover {{ background: {hover_bg}; }}
            QPushButton:pressed {{ background: rgba(255,255,255,0.15); }}
        """)
        btn.clicked.connect(slot)
        return btn

    def set_subtitle(self, subtitle: str) -> None:
        """Actualiza el nombre del archivo/proyecto activo."""
        self._subtitle.setText(f"— {subtitle}" if subtitle else "")

    def update_maximize_icon(self) -> None:
        """Actualiza el ícono del botón según el estado de maximización."""
        w = self._parent_window
        icon_name = "window_restore" if w.isMaximized() else "window_maximize"
        self._btn_window_maximize.setIcon(svg_icon(icon_name, 16, COLOR_TEXT_PRIMARY))

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self._parent_window.pos()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if event.buttons() == Qt.MouseButton.LeftButton and self._drag_pos is not None:
            if self._parent_window.isMaximized():
                self._parent_window.showNormal()
            self._parent_window.move(event.globalPosition().toPoint() - self._drag_pos)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        self._on_maximize_restore()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self._drag_pos = None

    def _on_minimize(self) -> None:
        self._parent_window.showMinimized()

    def _on_maximize_restore(self) -> None:
        if self._parent_window.isMaximized():
            self._parent_window.showNormal()
        else:
            self._parent_window.showMaximized()
        self.update_maximize_icon()

    def _on_close(self) -> None:
        self._parent_window.close()
