"""Original, scalable toolbar line icons; no font or external asset dependency."""

from functools import lru_cache

from PySide6.QtCore import QByteArray, Qt, QRectF
from PySide6.QtGui import QColor, QCursor, QIcon, QPainter, QPen, QPixmap
from PySide6.QtSvg import QSvgRenderer


SHAPES = {
    "bold": '<path d="M7 3h6a5 5 0 0 1 0 10H7M7 13h7a4 4 0 0 1 0 8H7V3" stroke-width="3"/>',
    "italic": '<path d="M10 3h10M4 21h10M15 3 9 21"/>',
    "underline": '<path d="M6 3v9a6 6 0 0 0 12 0V3M4 22h16"/>',
    "strike": '<path d="M18 5c-4-4-12-2-11 3 1 4 10 3 10 8 0 5-9 6-12 2M3 12h18"/>',
    "align_left": '<path d="M3 4h18M3 9h11M3 14h18M3 19h11"/>',
    "align_center": '<path d="M3 4h18M7 9h10M3 14h18M7 19h10"/>',
    "align_right": '<path d="M3 4h18M10 9h11M3 14h18M10 19h11"/>',
    "background": '<rect x="3" y="3" width="18" height="18" rx="2"/><path d="m7 16 5-10 5 10M9 13h6"/>',
    "more": '<circle cx="5" cy="12" r="1.5"/><circle cx="12" cy="12" r="1.5"/><circle cx="19" cy="12" r="1.5"/>',
    "select": '<path d="M5 3v16l4-5 4 7 3-2-4-6 6-1z"/>',
    "pen": '<path d="m4 16-1 5 5-1L20 8l-4-4zM13 7l4 4M4 16l4 4"/>',
    "highlight": '<path d="m6 13 8-9 6 5-8 9zM6 13l-2 5 4 3 4-3M3 22h18"/>',
    "line": '<path d="M4 20 20 4"/><circle cx="4" cy="20" r="1"/><circle cx="20" cy="4" r="1"/>',
    "rectangle": '<rect x="4" y="5" width="16" height="14" rx="1"/>',
    "ellipse": '<ellipse cx="12" cy="12" rx="9" ry="7"/>',
    "arrow": '<path d="M4 20 20 4M10 4h10v10"/>',
    "text": '<path d="M4 7V4h16v3M12 4v16M8 20h8"/>',
    "eraser": '<path d="m3 14 10-11 8 7-10 11H9zM7 10l8 7M11 21h10"/>',
    "move": '<path d="M12 2v20M2 12h20M9 5l3-3 3 3M9 19l3 3 3-3M5 9l-3 3 3 3M19 9l3 3-3 3"/>',
    "box": '<rect x="3" y="4" width="18" height="16" rx="1" stroke-dasharray="3 3"/>',
    "lasso": '<path d="M8 17C1 16 1 6 8 4S23 5 21 11 15 20 8 17Z" stroke-dasharray="3 2"/><path d="M8 16c6 4 5 8 1 6-3-1-2-5 1-7"/>',
    "polygon": '<path d="M4 5 19 3 21 17 11 21 3 14Z" stroke-dasharray="3 2"/><circle cx="4" cy="5" r="1.5"/><circle cx="19" cy="3" r="1.5"/><circle cx="21" cy="17" r="1.5"/><circle cx="11" cy="21" r="1.5"/><circle cx="3" cy="14" r="1.5"/>',
    "replace": '<rect x="4" y="4" width="16" height="16" stroke-dasharray="3 3"/>',
    "add": '<rect x="3" y="3" width="13" height="13" stroke-dasharray="3 2"/><path d="M17 12v10M12 17h10"/>',
    "subtract": '<rect x="3" y="3" width="13" height="13" stroke-dasharray="3 2"/><path d="M12 18h10"/>',
    "all": '<rect x="3" y="3" width="18" height="18" stroke-dasharray="3 2"/><path d="m7 12 3 3 7-7"/>',
    "none": '<rect x="3" y="3" width="18" height="18" stroke-dasharray="3 2"/><path d="m8 8 8 8M16 8l-8 8"/>',
    "undo": '<path d="m8 4-5 5 5 5M3 9h10a6 6 0 0 1 0 12h-3"/>',
    "redo": '<path d="m16 4 5 5-5 5M21 9H11a6 6 0 0 0 0 12h3"/>',
    "clear": '<path d="m4 16 9-13 5 4-8 13H3zM4 16l6 4M15 17h6M18 12h3M15 22h6"/>',
    "copy": '<rect x="8" y="8" width="13" height="13" rx="2"/><path d="M16 5V3H3v13h2"/>',
    "paste": '<path d="M8 5H4v17h16V5h-4"/><rect x="8" y="2" width="8" height="6" rx="2"/><path d="M8 12h8M8 16h6"/>',
    "duplicate": '<rect x="8" y="8" width="13" height="13" rx="2"/><path d="M16 5V3H3v13h2M14.5 11v7M11 14.5h7"/>',
    "delete": '<path d="M3 6h18M9 6V3h6v3M5 6l1 15h12l1-15M10 10v7M14 10v7"/>',
    "save": '<path d="M12 2v12M8 10l4 4 4-4M4 15v6h16v-6"/>',
    "screenshot": '<rect x="3" y="6" width="18" height="15" rx="2"/><path d="M8 6V3h8v3"/><circle cx="12" cy="13" r="4"/>',
    "palette": '<path d="M12 3a9 9 0 1 0 0 18c3 0 0-4 3-5 3-1 6 0 6-4a9 9 0 0 0-9-9z"/><circle cx="7" cy="10" r="1"/><circle cx="11" cy="7" r="1"/><circle cx="16" cy="8" r="1"/>',
    "size": '<path d="M4 5h16M4 12h16"/><path d="M4 20h16" stroke-width="4"/>',
    "desktop": '<rect x="2" y="3" width="20" height="14" rx="2"/><path d="M12 17v4M8 21h8"/>',
    "eye": '<path d="M2 12c5-10 15-10 20 0-5 10-15 10-20 0z"/><circle cx="12" cy="12" r="3"/>',
    "hidden": '<path d="M3 3l18 18M2 12c2-4 4-6 7-7M13 4c4 0 7 4 9 8l-3 4M15 20c-6 1-10-3-13-8"/>',
    "close": '<path d="m5 5 14 14M19 5 5 19"/>',
    "collapse": '<path d="M5 12h14"/>',
    "expand": '<path d="M5 12h14M12 5v14"/>',
}

SHAPES.update({
 'fetcher':'<path d="M3 8V3h5M16 3h5v5M21 16v5h-5M8 21H3v-5"/><rect x="7" y="7" width="10" height="10"/>',
 'crop':'<path d="M6 2v16h16M2 6h16v16"/>',
 'rotate_left':'<path d="M8 5H3v-4M3 5a10 10 0 1 1-1 12"/>',
 'rotate_right':'<path d="M16 5h5v-4M21 5a10 10 0 1 0 1 12"/>',
 'reset':'<path d="M5 5v6h6M5 11a8 8 0 1 1 2 8"/>',
 'flip_h':'<path d="M12 2v20M3 7v10l6-5zM21 7v10l-6-5z"/>',
 'flip_v':'<path d="M2 12h20M7 3h10l-5 6zM7 21h10l5-6z"/>',
 'up':'<path d="m5 13 7-7 7 7M12 6v15"/>',
 'down':'<path d="m5 11 7 7 7-7M12 18V3"/>',
 'front':'<path d="M3 3h18M5 14l7-7 7 7M12 7v14"/>',
 'back':'<path d="M3 21h18M5 10l7 7 7-7M12 17V3"/>'
})


@lru_cache(maxsize=32)
def crosshair_cursor(color: str, width: int, size: int) -> QCursor:
    """Simple customizable crosshair; the center is the drawing hotspot."""
    pixmap = QPixmap(size + 8, size + 8)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    center = pixmap.width() // 2
    half = size // 2
    outline = '#ffffff' if QColor(color).lightnessF() < .5 else '#172033'
    for stroke, thickness in ((outline, width + 2), (color, width)):
        painter.setPen(QPen(QColor(stroke), thickness, Qt.SolidLine, Qt.RoundCap))
        painter.drawLine(center - half, center, center + half, center)
        painter.drawLine(center, center - half, center, center + half)
    painter.end()
    return QCursor(pixmap, center, center)


@lru_cache(maxsize=256)
def icon(name: str, foreground: str = "#e5edf8") -> QIcon:
    result = QIcon()
    shape = SHAPES[name]
    for mode, state, color in ((QIcon.Mode.Normal, QIcon.State.Off, foreground),
                               (QIcon.Mode.Normal, QIcon.State.On, "#102337"),
                               (QIcon.Mode.Disabled, QIcon.State.Off, "#68758a")):
        for size in (24, 48, 72):
            svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" '
                   f'viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="1.8" '
                   f'stroke-linecap="round" stroke-linejoin="round">{shape}</svg>')
            pixmap = QPixmap(size, size)
            pixmap.fill(Qt.GlobalColor.transparent)
            painter = QPainter(pixmap)
            QSvgRenderer(QByteArray(svg.encode())).render(painter)
            painter.end()
            result.addPixmap(pixmap, mode, state)
    return result
