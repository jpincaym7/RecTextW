"""Carga y colorización programática de SVGs. Cacheado con lru_cache."""
import functools
import re
from pathlib import Path

from PyQt6.QtCore import Qt, QByteArray
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor
from PyQt6.QtSvg import QSvgRenderer

from app.config import ICONS_DIR


@functools.lru_cache(maxsize=256)
def svg_icon(name: str, size: int = 24, color: str = "#F0F4F8") -> QIcon:
    """Carga un SVG y lo coloriza programáticamente."""
    svg_path = ICONS_DIR / f"{name}.svg"
    if not svg_path.exists():
        return QIcon()
    return _render_svg(svg_path, size, color)


def _render_svg(svg_path: Path, size: int, color: str) -> QIcon:
    """Renderiza un SVG con colorización aplicada."""
    svg_content = svg_path.read_text(encoding="utf-8")
    colored_svg = _apply_color(svg_content, color)

    renderer = QSvgRenderer(QByteArray(colored_svg.encode("utf-8")))
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()

    return QIcon(pixmap)


def _apply_color(svg_content: str, color: str) -> str:
    """Reemplaza currentColor, stroke y fill con el color dado."""
    result = svg_content.replace("currentColor", color)
    result = re.sub(r'stroke="[^"]*"', f'stroke="{color}"', result)
    # No sobreescribir fill="none" (necesario para iconos hollow)
    result = re.sub(r'fill="(?!none)[^"]*"', f'fill="{color}"', result)
    return result


def svg_pixmap(name: str, size: int = 24, color: str = "#F0F4F8") -> QPixmap:
    """Retorna un QPixmap del SVG colorizado."""
    icon = svg_icon(name, size, color)
    return icon.pixmap(size, size)
