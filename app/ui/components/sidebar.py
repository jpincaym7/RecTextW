"""Panel de navegación lateral con iconos SVG y estado activo."""
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel, QHBoxLayout

from app.ui.tokens import (
    SIDEBAR_W, SPACE_MD, SPACE_SM, SPACE_LG,
    COLOR_BG_SIDEBAR, COLOR_ACCENT, COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY,
)
from app.ui.svg_helper import svg_icon


_NAV_ITEMS = [
    ("home",     "nav_home",     "Inicio"),
    ("history",  "nav_history",  "Historial"),
    ("settings", "nav_settings", "Configuración"),
    ("about",    "nav_about",    "Acerca de"),
]


class SidebarWidget(QWidget):
    """Panel lateral de navegación con indicador de sección activa."""

    navigation_requested = pyqtSignal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._active = "home"
        self._buttons: dict[str, QPushButton] = {}
        self._setup_ui()

    def _setup_ui(self) -> None:
        self.setFixedWidth(SIDEBAR_W)
        self.setObjectName("sidebar")
        self.setStyleSheet(f"#sidebar {{ background-color: {COLOR_BG_SIDEBAR}; border-right: 1px solid #163050; }}")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, SPACE_LG, 0, SPACE_LG)
        layout.setSpacing(4)

        for key, icon_name, label in _NAV_ITEMS:
            btn = self._make_nav_btn(key, icon_name, label)
            self._buttons[key] = btn
            layout.addWidget(btn)

        layout.addStretch()

    def _make_nav_btn(self, key: str, icon_name: str, label: str) -> QPushButton:
        btn = QPushButton()
        btn.setFixedHeight(48)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setObjectName(f"navBtn_{key}")

        row = QHBoxLayout(btn)
        row.setContentsMargins(SPACE_MD, 0, SPACE_MD, 0)
        row.setSpacing(SPACE_SM)

        icon_label = QLabel(btn)
        icon_label.setPixmap(svg_icon(icon_name, 20, COLOR_TEXT_SECONDARY).pixmap(20, 20))
        icon_label.setFixedSize(20, 20)
        icon_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        text_label = QLabel(label, btn)
        text_label.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: 13px;")
        text_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        row.addWidget(icon_label)
        row.addWidget(text_label)
        row.addStretch()

        # Almacenar referencias para actualizar color al cambiar selección
        btn._icon_label = icon_label
        btn._text_label = text_label
        btn._icon_name = icon_name

        btn.clicked.connect(lambda checked, k=key: self._on_click(k))
        self._apply_btn_style(btn, active=False)
        return btn

    def _apply_btn_style(self, btn: QPushButton, active: bool) -> None:
        accent = COLOR_ACCENT if active else "transparent"
        bg = "rgba(249,115,22,0.1)" if active else "transparent"
        txt_color = COLOR_ACCENT if active else COLOR_TEXT_SECONDARY
        icon_color = COLOR_ACCENT if active else COLOR_TEXT_SECONDARY

        btn.setStyleSheet(f"""
            QPushButton {{
                background: {bg};
                border: none;
                border-left: 3px solid {accent};
                text-align: left;
                padding: 0;
            }}
            QPushButton:hover {{
                background: rgba(255,255,255,0.05);
            }}
        """)
        if hasattr(btn, "_text_label"):
            btn._text_label.setStyleSheet(f"color: {txt_color}; font-size: 13px;")
        if hasattr(btn, "_icon_label") and hasattr(btn, "_icon_name"):
            btn._icon_label.setPixmap(svg_icon(btn._icon_name, 20, icon_color).pixmap(20, 20))

    def _on_click(self, key: str) -> None:
        self.set_active(key)
        self.navigation_requested.emit(key)

    def set_active(self, key: str) -> None:
        """Actualiza visualmente la sección activa."""
        self._active = key
        for k, btn in self._buttons.items():
            self._apply_btn_style(btn, active=(k == key))
