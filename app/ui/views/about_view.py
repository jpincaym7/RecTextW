"""Vista de información del proyecto InnoTech VideoTutor."""
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
)

from app.config import APP_NAME, APP_VERSION, APP_AUTHOR
from app.ui.tokens import (
    COLOR_BG_SURFACE, COLOR_BG_CARD, COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY,
    COLOR_ACCENT, SPACE_MD, SPACE_LG, SPACE_XL, RADIUS_MD, ICON_LG,
)
from app.ui.svg_helper import svg_icon


class AboutView(QWidget):
    """Vista de créditos e información de la aplicación."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        self.setObjectName("aboutView")
        self.setStyleSheet(f"#aboutView {{ background: {COLOR_BG_SURFACE}; }}")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACE_XL, SPACE_XL, SPACE_XL, SPACE_XL)
        layout.setSpacing(SPACE_LG)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)

        # Logo + nombre
        logo_lbl = QLabel()
        logo_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_lbl.setPixmap(svg_icon("app_logo", ICON_LG, COLOR_ACCENT).pixmap(ICON_LG, ICON_LG))

        name_lbl = QLabel(APP_NAME)
        name_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_lbl.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; font-size: 24px; font-weight: 600;")

        version_lbl = QLabel(f"Versión {APP_VERSION}")
        version_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        version_lbl.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: 14px;")

        desc_lbl = QLabel(
            "Herramienta de automatización de pre-producción de videotutoriales.\n"
            "Transcripción local con Whisper · Generación de texto con IA · Exportación a Word"
        )
        desc_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc_lbl.setWordWrap(True)
        desc_lbl.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: 13px;")

        layout.addWidget(logo_lbl)
        layout.addWidget(name_lbl)
        layout.addWidget(version_lbl)
        layout.addWidget(desc_lbl)

        # Separador
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("background: #2D3748; max-height: 1px;")
        layout.addWidget(sep)

        # Créditos
        credits_card = QWidget()
        credits_card.setObjectName("creditsCard")
        credits_card.setStyleSheet(f"#creditsCard {{ background: {COLOR_BG_CARD}; border-radius: {RADIUS_MD}px; }}")
        credits_layout = QVBoxLayout(credits_card)
        credits_layout.setContentsMargins(SPACE_LG, SPACE_LG, SPACE_LG, SPACE_LG)
        credits_layout.setSpacing(SPACE_MD)

        credits_title = QLabel("Equipo")
        credits_title.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: 11px; font-weight: 600;")
        credits_layout.addWidget(credits_title)

        for role, name in [
            ("Solicitante", "Felipe Arévalo Cordovilla — Subgerente de Sistemas"),
            ("Diseñador UX/UI", "Kevin Astudillo — Lead Designer, División de Desarrollo"),
            ("Desarrollador", "Jordy Pincay"),
            ("Empresa", APP_AUTHOR),
        ]:
            row = QHBoxLayout()
            role_lbl = QLabel(role)
            role_lbl.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: 12px; min-width: 130px;")
            name_lbl_w = QLabel(name)
            name_lbl_w.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; font-size: 12px;")
            row.addWidget(role_lbl)
            row.addWidget(name_lbl_w)
            row.addStretch()
            credits_layout.addLayout(row)

        layout.addWidget(credits_card)

        # Versiones
        try:
            import PyQt6
            import torch
            import whisper
            deps_text = (
                f"PyQt6 {PyQt6.QtCore.PYQT_VERSION_STR}  ·  "
                f"PyTorch {torch.__version__}  ·  "
                f"Whisper (openai-whisper)"
            )
        except Exception:
            deps_text = "PyQt6 · PyTorch · Whisper"

        deps_lbl = QLabel(deps_text)
        deps_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        deps_lbl.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: 11px;")
        layout.addWidget(deps_lbl)
        layout.addStretch()
