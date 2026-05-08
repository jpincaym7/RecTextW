"""Dialog modal que informa al usuario sobre errores de permisos y ofrece soluciones."""
import sys
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QWidget,
)
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtCore import QUrl

from app.ui.tokens import (
    COLOR_BG_PRIMARY, COLOR_BG_CARD, COLOR_BG_SURFACE,
    COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY,
    COLOR_ERROR, COLOR_WARNING, COLOR_SUCCESS, COLOR_ACCENT,
    COLOR_BORDER, RADIUS_MD, SPACE_MD, SPACE_LG, SPACE_SM,
)


_DIALOG_STYLE = f"""
QDialog {{
    background: {COLOR_BG_PRIMARY};
}}
QLabel {{
    color: {COLOR_TEXT_PRIMARY};
    background: transparent;
}}
QPushButton {{
    border-radius: 6px;
    font-size: 13px;
    font-weight: 600;
    padding: 8px 16px;
    border: none;
}}
QPushButton#btnAdmin {{
    background: {COLOR_ACCENT};
    color: white;
}}
QPushButton#btnAdmin:hover {{
    background: #EA6C0A;
}}
QPushButton#btnFolder {{
    background: {COLOR_BG_CARD};
    color: {COLOR_TEXT_PRIMARY};
    border: 1px solid {COLOR_BORDER};
}}
QPushButton#btnFolder:hover {{
    background: #3D4F64;
}}
QPushButton#btnLog {{
    background: {COLOR_BG_CARD};
    color: {COLOR_TEXT_PRIMARY};
    border: 1px solid {COLOR_BORDER};
}}
QPushButton#btnLog:hover {{
    background: #3D4F64;
}}
QPushButton#btnClose {{
    background: transparent;
    color: {COLOR_TEXT_SECONDARY};
    border: 1px solid {COLOR_BORDER};
}}
QPushButton#btnClose:hover {{
    color: {COLOR_TEXT_PRIMARY};
    border-color: {COLOR_TEXT_PRIMARY};
}}
"""

_SOLUTION_STYLE = f"""
QWidget {{
    background: {COLOR_BG_SURFACE};
    border-radius: {RADIUS_MD}px;
    border: 1px solid {COLOR_BORDER};
}}
QLabel {{
    background: transparent;
    color: {COLOR_TEXT_SECONDARY};
    font-size: 12px;
}}
"""


class PrivilegesDialog(QDialog):
    """
    Dialog que explica un error de permisos/disco y ofrece:
      - Reiniciar como Administrador (UAC)
      - Abrir carpeta de datos
      - Abrir registro de errores
    """

    def __init__(
        self,
        error_message: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._error_message = error_message
        self._setup_ui()

    def _setup_ui(self) -> None:
        self.setWindowTitle("Permisos insuficientes")
        self.setWindowFlags(
            Qt.WindowType.Dialog |
            Qt.WindowType.WindowCloseButtonHint
        )
        self.setModal(True)
        self.setFixedWidth(480)
        self.setStyleSheet(_DIALOG_STYLE)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACE_LG, SPACE_LG, SPACE_LG, SPACE_LG)
        layout.setSpacing(SPACE_MD)

        # ── Cabecera ──────────────────────────────────────────────────────────
        header = QHBoxLayout()
        icon_lbl = QLabel("⚠")
        icon_lbl.setStyleSheet(f"font-size: 28px; color: {COLOR_WARNING}; background: transparent;")
        icon_lbl.setFixedWidth(36)

        title_lbl = QLabel("Se requieren permisos adicionales")
        title_lbl.setStyleSheet(
            f"font-size: 16px; font-weight: 700; color: {COLOR_TEXT_PRIMARY}; background: transparent;"
        )
        title_lbl.setWordWrap(True)

        header.addWidget(icon_lbl)
        header.addWidget(title_lbl, 1)
        layout.addLayout(header)

        # ── Detalle del error ─────────────────────────────────────────────────
        detail_lbl = QLabel(self._short_error())
        detail_lbl.setStyleSheet(
            f"font-size: 12px; color: {COLOR_ERROR}; background: {COLOR_BG_CARD}; "
            f"border-radius: 6px; padding: 8px; border: 1px solid {COLOR_ERROR}33;"
        )
        detail_lbl.setWordWrap(True)
        layout.addWidget(detail_lbl)

        # ── Soluciones sugeridas ──────────────────────────────────────────────
        solutions_box = QWidget()
        solutions_box.setStyleSheet(_SOLUTION_STYLE)
        sol_layout = QVBoxLayout(solutions_box)
        sol_layout.setContentsMargins(SPACE_MD, SPACE_MD, SPACE_MD, SPACE_MD)
        sol_layout.setSpacing(SPACE_SM)

        heading = QLabel("Posibles soluciones:")
        heading.setStyleSheet(
            f"font-weight: 600; font-size: 12px; color: {COLOR_TEXT_PRIMARY}; background: transparent;"
        )
        sol_layout.addWidget(heading)

        for txt in self._get_solutions():
            lbl = QLabel(f"  • {txt}")
            lbl.setWordWrap(True)
            sol_layout.addWidget(lbl)

        layout.addWidget(solutions_box)

        # ── Botones ───────────────────────────────────────────────────────────
        btn_layout = QVBoxLayout()
        btn_layout.setSpacing(SPACE_SM)

        if sys.platform == "win32":
            admin_btn = QPushButton("  Reiniciar como Administrador (UAC)")
            admin_btn.setObjectName("btnAdmin")
            admin_btn.setFixedHeight(44)
            admin_btn.clicked.connect(self._restart_as_admin)
            btn_layout.addWidget(admin_btn)

        row2 = QHBoxLayout()
        row2.setSpacing(SPACE_SM)

        folder_btn = QPushButton("Abrir carpeta de datos")
        folder_btn.setObjectName("btnFolder")
        folder_btn.clicked.connect(self._open_data_folder)
        row2.addWidget(folder_btn)

        log_btn = QPushButton("Ver registro de errores")
        log_btn.setObjectName("btnLog")
        log_btn.clicked.connect(self._open_log)
        row2.addWidget(log_btn)

        btn_layout.addLayout(row2)

        close_btn = QPushButton("Cerrar")
        close_btn.setObjectName("btnClose")
        close_btn.clicked.connect(self.reject)
        btn_layout.addWidget(close_btn)

        layout.addLayout(btn_layout)
        self.adjustSize()

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _short_error(self) -> str:
        msg = self._error_message
        return msg[:200] + "…" if len(msg) > 200 else msg

    def _get_solutions(self) -> list[str]:
        msg = self._error_message.lower()
        solutions = []
        if any(k in msg for k in ("permission", "acceso", "denegado", "winerror 5", "access")):
            solutions.append("Ejecutar la aplicación como Administrador (botón de arriba)")
            solutions.append("Verificar que la carpeta de datos no está en OneDrive o una unidad de red")
        if any(k in msg for k in ("espacio", "space", "disk", "no space", "full")):
            solutions.append("Liberar al menos 500 MB de espacio en el disco")
        if not solutions:
            solutions.append("Ejecutar la aplicación como Administrador")
            solutions.append("Verificar que el antivirus no bloquea la aplicación")
        solutions.append("Revisar el registro de errores para más detalles")
        return solutions

    def _restart_as_admin(self) -> None:
        from app.utils.privileges import restart_as_admin
        self.accept()
        restart_as_admin()

    def _open_data_folder(self) -> None:
        from app.config import DATA_DIR
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(DATA_DIR)))

    def _open_log(self) -> None:
        from app.config import LOGS_DIR
        log_file = LOGS_DIR / "innotech_videotutor.log"
        if log_file.exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(log_file)))
        else:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(LOGS_DIR)))
