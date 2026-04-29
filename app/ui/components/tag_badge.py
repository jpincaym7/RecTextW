"""Chip/badge de etiqueta reutilizable."""
from PyQt6.QtWidgets import QLabel
from app.ui.tokens import COLOR_ACCENT, RADIUS_SM, SPACE_XS, SPACE_SM


class TagBadge(QLabel):
    """Etiqueta tipo chip con fondo semitransparente y texto de acento."""

    def __init__(self, text: str = "", parent=None) -> None:
        super().__init__(text, parent)
        self.setStyleSheet(f"""
            QLabel {{
                background: rgba(249, 115, 22, 0.15);
                color: {COLOR_ACCENT};
                border-radius: {RADIUS_SM}px;
                padding: {SPACE_XS}px {SPACE_SM}px;
                font-size: 11px;
                font-weight: 600;
            }}
        """)
