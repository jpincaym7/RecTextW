"""Botón con ícono SVG. Variantes: primary, secondary/ghost, danger."""
from typing import Literal

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QPushButton

from app.ui.tokens import (
    COLOR_ACCENT, COLOR_ACCENT_HOVER, COLOR_ACCENT_PRESS,
    COLOR_ERROR, COLOR_TEXT_PRIMARY, COLOR_BORDER, RADIUS_SM, SPACE_SM,
)
from app.ui.svg_helper import svg_icon


class IconButton(QPushButton):
    """Botón estilizado con ícono SVG y variantes de apariencia."""

    def __init__(
        self,
        icon_name: str = "",
        label: str = "",
        variant: Literal["primary", "secondary", "danger", "ghost"] = "primary",
        icon_size: int = 16,
        parent=None,
    ) -> None:
        super().__init__(label, parent)
        self._icon_name = icon_name
        self._variant = variant
        self._icon_size = icon_size
        self._apply_style()
        if icon_name:
            self._update_icon()
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def _apply_style(self) -> None:
        if self._variant == "primary":
            self.setStyleSheet(f"""
                QPushButton {{
                    background: {COLOR_ACCENT};
                    color: #FFFFFF;
                    border-radius: {RADIUS_SM}px;
                    padding: {SPACE_SM}px {SPACE_SM * 2}px;
                    font-weight: 600;
                    font-size: 13px;
                    border: none;
                }}
                QPushButton:hover {{ background: {COLOR_ACCENT_HOVER}; }}
                QPushButton:pressed {{ background: {COLOR_ACCENT_PRESS}; }}
                QPushButton:disabled {{ background: #2D3748; color: #4A5568; }}
            """)
        elif self._variant in ("secondary", "ghost"):
            self.setStyleSheet(f"""
                QPushButton {{
                    background: transparent;
                    color: #CBD5E1;
                    border: 1px solid {COLOR_BORDER};
                    border-radius: {RADIUS_SM}px;
                    padding: {SPACE_SM}px {SPACE_SM * 2}px;
                    font-size: 13px;
                }}
                QPushButton:hover {{ background: #2D3748; }}
                QPushButton:pressed {{ background: #1A2332; }}
                QPushButton:disabled {{ color: #4A5568; border-color: #2D3748; }}
            """)
        elif self._variant == "danger":
            self.setStyleSheet(f"""
                QPushButton {{
                    background: {COLOR_ERROR};
                    color: #FFFFFF;
                    border-radius: {RADIUS_SM}px;
                    padding: {SPACE_SM}px {SPACE_SM * 2}px;
                    font-weight: 600;
                    font-size: 13px;
                    border: none;
                }}
                QPushButton:hover {{ background: #DC2626; }}
                QPushButton:pressed {{ background: #B91C1C; }}
            """)

    def _update_icon(self) -> None:
        color = "#FFFFFF" if self._variant in ("primary", "danger") else "#CBD5E1"
        self.setIcon(svg_icon(self._icon_name, self._icon_size, color))
        self.setIconSize(self.icon().actualSize(self.sizeHint()))

    def set_icon_name(self, name: str) -> None:
        self._icon_name = name
        self._update_icon()
