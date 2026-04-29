"""Vista de historial de procesamientos con tabla y acciones."""
import os
from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QLabel, QPushButton,
)

from app.config import DB_PATH
from app.db.repository import ProcessingRepository
from app.ui.components.icon_button import IconButton
from app.ui.components.toast_manager import ToastManager
from app.ui.tokens import (
    COLOR_BG_SURFACE, COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY,
    COLOR_SUCCESS, COLOR_ERROR, COLOR_WARNING, SPACE_MD, SPACE_LG,
)
from app.ui.svg_helper import svg_icon


class HistoryView(QWidget):
    """Muestra el historial de procesamientos con opciones de acción."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._repo = ProcessingRepository(DB_PATH)
        self._setup_ui()

    def _setup_ui(self) -> None:
        self.setObjectName("historyView")
        self.setStyleSheet(f"#historyView {{ background: {COLOR_BG_SURFACE}; }}")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACE_LG, SPACE_LG, SPACE_LG, SPACE_LG)
        layout.setSpacing(SPACE_MD)

        # Cabecera
        header = QHBoxLayout()
        title = QLabel("Historial de procesamientos")
        title.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; font-size: 18px; font-weight: 600;")
        header.addWidget(title)
        header.addStretch()

        refresh_btn = IconButton("nav_history", "  Actualizar", "ghost")
        refresh_btn.clicked.connect(self.refresh)
        header.addWidget(refresh_btn)

        clear_btn = IconButton("action_delete", "  Limpiar historial", "danger")
        clear_btn.clicked.connect(self._clear_all)
        header.addWidget(clear_btn)

        layout.addLayout(header)

        # Tabla
        self._table = QTableWidget()
        self._table.setColumnCount(7)
        self._table.setHorizontalHeaderLabels([
            "Fecha", "Video", "Duración", "Estado", "Proveedor IA", "Confianza", "Acciones"
        ])
        self._table.setAlternatingRowColors(True)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self._table.verticalHeader().setVisible(False)
        self._table.setShowGrid(False)
        layout.addWidget(self._table)

        self.refresh()

    def refresh(self) -> None:
        """Recarga los registros del historial desde la base de datos."""
        records = self._repo.get_all(limit=100)
        self._table.setRowCount(len(records))

        status_colors = {
            "completed": COLOR_SUCCESS,
            "error": COLOR_ERROR,
            "cancelled": COLOR_WARNING,
        }
        status_labels = {
            "completed": "Completado",
            "error": "Error",
            "cancelled": "Cancelado",
        }

        for row, record in enumerate(records):
            self._table.setRowHeight(row, 48)

            date_str = record.created_at.strftime("%d/%m/%Y %H:%M") if isinstance(record.created_at, datetime) else str(record.created_at)
            duration = self._format_duration(record.duration_seconds)
            status_color = status_colors.get(record.status, COLOR_TEXT_SECONDARY)
            status_text = status_labels.get(record.status, record.status)

            items = [
                date_str,
                record.video_name,
                duration,
                status_text,
                f"{record.ai_provider}",
                f"{record.transcription_confidence:.1%}",
            ]

            for col, text in enumerate(items):
                item = QTableWidgetItem(text)
                item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
                if col == 3:
                    item.setForeground(__import__("PyQt6.QtGui", fromlist=["QColor"]).QColor(status_color))
                self._table.setItem(row, col, item)

            # Botones de acción
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(4, 4, 4, 4)
            actions_layout.setSpacing(4)

            open_btn = QPushButton()
            open_btn.setIcon(svg_icon("action_open_folder", 16, "#94A3B8"))
            open_btn.setFixedSize(32, 32)
            open_btn.setToolTip("Abrir carpeta de salida")
            open_btn.setStyleSheet("QPushButton { background: transparent; border-radius: 4px; } QPushButton:hover { background: #2D3748; }")
            open_btn.clicked.connect(lambda _, r=record: self._open_folder(r.output_dir))

            del_btn = QPushButton()
            del_btn.setIcon(svg_icon("action_delete", 16, "#EF4444"))
            del_btn.setFixedSize(32, 32)
            del_btn.setToolTip("Eliminar registro")
            del_btn.setStyleSheet("QPushButton { background: transparent; border-radius: 4px; } QPushButton:hover { background: rgba(239,68,68,0.15); }")
            del_btn.clicked.connect(lambda _, r=record: self._delete_record(r.id))

            actions_layout.addWidget(open_btn)
            actions_layout.addWidget(del_btn)
            actions_layout.addStretch()
            self._table.setCellWidget(row, 6, actions_widget)

    def _format_duration(self, seconds: float) -> str:
        m = int(seconds // 60)
        s = int(seconds % 60)
        return f"{m:02d}:{s:02d}"

    def _open_folder(self, folder: str) -> None:
        p = Path(folder)
        if p.exists():
            os.startfile(str(p))
        else:
            ToastManager.instance().warning("La carpeta de salida ya no existe")

    def _delete_record(self, record_id: int | None) -> None:
        if record_id is None:
            return
        self._repo.delete(record_id)
        self.refresh()
        ToastManager.instance().info("Registro eliminado del historial")

    def _clear_all(self) -> None:
        ToastManager.instance().warning("¿Limpiar todo el historial? Haz click de nuevo para confirmar")
        self._confirm_clear = True

        from PyQt6.QtCore import QTimer
        def _do_clear():
            if getattr(self, "_confirm_clear", False):
                self._repo.delete_all()
                self.refresh()
                ToastManager.instance().success("Historial limpiado")
                self._confirm_clear = False

        QTimer.singleShot(3000, _do_clear)
