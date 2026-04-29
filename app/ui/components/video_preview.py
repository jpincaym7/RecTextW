"""Widget de preview: thumbnail izquierda + info derecha, en una card."""
import os
import tempfile
from pathlib import Path

from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QSizePolicy,
)

from app.ui.tokens import (
    COLOR_BG_CARD, COLOR_BG_PRIMARY, COLOR_TEXT_PRIMARY,
    COLOR_TEXT_SECONDARY, RADIUS_MD, SPACE_SM, SPACE_MD,
)
from app.ui.svg_helper import svg_icon

_THUMB_W = 300
_THUMB_H = 169   # 16:9
_CARD_H  = _THUMB_H + SPACE_MD * 2   # 201 px


class _ThumbWorker(QThread):
    done   = pyqtSignal(str)
    failed = pyqtSignal()

    def __init__(self, video_path: Path, thumb_path: Path, seek_secs: float = 0.0) -> None:
        super().__init__()
        self._video = video_path
        self._thumb = thumb_path
        self._seek  = seek_secs

    def run(self) -> None:
        try:
            from app.utils.ffmpeg_check import find_ffmpeg
            from app.utils.subprocess_helper import run_hidden
            ffmpeg = find_ffmpeg()
            if not ffmpeg:
                self.failed.emit(); return

            cmd = [str(ffmpeg), "-i", str(self._video),
                   "-vframes", "1", "-q:v", "2",
                   "-vf", f"scale={_THUMB_W}:-1",
                   "-y", str(self._thumb)]
            if self._seek > 0:
                cmd = [str(ffmpeg), "-ss", str(self._seek),
                       "-i", str(self._video),
                       "-vframes", "1", "-q:v", "2",
                       "-vf", f"scale={_THUMB_W}:-1",
                       "-y", str(self._thumb)]

            run_hidden(cmd, capture_output=True, timeout=15)

            if self._thumb.exists() and self._thumb.stat().st_size > 0:
                self.done.emit(str(self._thumb))
            else:
                self.failed.emit()
        except Exception:
            self.failed.emit()


class VideoPreviewWidget(QFrame):
    """Card horizontal: thumbnail (izquierda) + nombre/meta/reproducir (derecha)."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._video_path: Path | None = None
        self._thumb_worker: _ThumbWorker | None = None
        self._thumb_path: Path | None = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setFixedHeight(_CARD_H)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setStyleSheet(f"""
            VideoPreviewWidget {{
                background-color: {COLOR_BG_CARD};
                border-radius: {RADIUS_MD}px;
            }}
        """)

        outer = QHBoxLayout(self)
        outer.setContentsMargins(SPACE_MD, SPACE_MD, SPACE_MD, SPACE_MD)
        outer.setSpacing(SPACE_MD)

        # ── Thumbnail ─────────────────────────────────────────────────────────
        self._thumb_label = QLabel()
        self._thumb_label.setFixedSize(_THUMB_W, _THUMB_H)
        self._thumb_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._thumb_label.setStyleSheet(
            f"background-color: {COLOR_BG_PRIMARY}; border-radius: 6px;"
        )
        self._thumb_label.setPixmap(
            svg_icon("file_video", 48, COLOR_TEXT_SECONDARY).pixmap(48, 48)
        )
        outer.addWidget(self._thumb_label, 0, Qt.AlignmentFlag.AlignVCenter)

        # ── Info ──────────────────────────────────────────────────────────────
        info_widget = QWidget()
        info_widget.setStyleSheet("background-color: transparent;")
        info_layout = QVBoxLayout(info_widget)
        info_layout.setContentsMargins(SPACE_SM, 0, 0, 0)
        info_layout.setSpacing(SPACE_SM)
        info_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self._name_label = QLabel("Sin video")
        self._name_label.setStyleSheet(
            f"color: {COLOR_TEXT_PRIMARY}; font-size: 15px; font-weight: 600;"
            "background-color: transparent;"
        )
        self._name_label.setWordWrap(True)

        self._meta_label = QLabel("")
        self._meta_label.setStyleSheet(
            f"color: {COLOR_TEXT_SECONDARY}; font-size: 12px;"
            "background-color: transparent;"
        )

        self._play_btn = QPushButton("  Reproducir")
        self._play_btn.setIcon(svg_icon("action_play", 14, "#FFFFFF"))
        self._play_btn.setIconSize(QSize(14, 14))
        self._play_btn.setFixedHeight(32)
        self._play_btn.setFixedWidth(140)
        self._play_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._play_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {COLOR_TEXT_SECONDARY};
                border: 1px solid #4A5568;
                border-radius: 6px;
                padding: 2px 14px;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: #2D3748;
                color: {COLOR_TEXT_PRIMARY};
            }}
        """)
        self._play_btn.clicked.connect(self._play_video)

        info_layout.addWidget(self._name_label)
        info_layout.addWidget(self._meta_label)
        info_layout.addSpacing(SPACE_SM)
        info_layout.addWidget(self._play_btn)

        outer.addWidget(info_widget, stretch=1, alignment=Qt.AlignmentFlag.AlignVCenter)

    # ── API pública ───────────────────────────────────────────────────────────

    def load_video(self, video_path: Path, video_info=None) -> None:
        self._video_path = video_path
        self._name_label.setText(video_path.name)
        duration_secs = 0.0
        if video_info:
            size_mb       = video_info.file_size_bytes / (1024 * 1024)
            duration_secs = video_info.duration_seconds
            duration      = self._fmt_duration(duration_secs)
            self._meta_label.setText(
                f"{duration}  ·  {video_info.width}×{video_info.height}"
                f"  ·  {video_info.fps:.1f} fps  ·  {size_mb:.1f} MB"
            )
        else:
            size_mb = video_path.stat().st_size / (1024 * 1024) if video_path.exists() else 0
            self._meta_label.setText(f"{size_mb:.1f} MB")
        self._extract_thumbnail(video_path, duration_secs)

    # ── Privados ──────────────────────────────────────────────────────────────

    def _extract_thumbnail(self, video_path: Path, duration_secs: float = 0.0) -> None:
        tmp = Path(tempfile.gettempdir()) / f"innotech_thumb_{video_path.stem}.jpg"
        self._thumb_path = tmp
        # seek to 10 % of duration (min 0 s, max 5 s) for a representative frame
        seek = min(max(duration_secs * 0.1, 0.0), 5.0) if duration_secs > 0.5 else 0.0
        self._thumb_worker = _ThumbWorker(video_path, tmp, seek)
        self._thumb_worker.done.connect(self._on_thumb_done)
        self._thumb_worker.failed.connect(lambda: None)
        self._thumb_worker.start()

    def _on_thumb_done(self, path: str) -> None:
        pixmap = QPixmap(path)
        if pixmap.isNull():
            return
        scaled = pixmap.scaled(
            _THUMB_W, _THUMB_H,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self._thumb_label.setPixmap(scaled)

    def _play_video(self) -> None:
        if self._video_path and self._video_path.exists():
            os.startfile(str(self._video_path))

    def _fmt_duration(self, seconds: float) -> str:
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        return f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"
