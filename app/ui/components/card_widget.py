"""Tarjeta de contenido reutilizable con estilo dark."""
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel

from app.ui.tokens import COLOR_BG_CARD, RADIUS_MD, SPACE_MD, COLOR_TEXT_SECONDARY


class CardWidget(QWidget):
    """Tarjeta con fondo oscuro, borde redondeado y padding interno."""

    def __init__(
        self,
        title: str = "",
        content_widget: QWidget | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._setup_ui(title, content_widget)

    def _setup_ui(self, title: str, content_widget: QWidget | None) -> None:
        self.setObjectName("card")
        self.setStyleSheet(f"""
            #card {{
                background-color: {COLOR_BG_CARD};
                border-radius: {RADIUS_MD}px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACE_MD, SPACE_MD, SPACE_MD, SPACE_MD)
        layout.setSpacing(SPACE_MD)

        if title:
            lbl = QLabel(title)
            lbl.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;")
            layout.addWidget(lbl)

        if content_widget:
            layout.addWidget(content_widget)

    def set_content(self, widget: QWidget) -> None:
        self.layout().addWidget(widget)
