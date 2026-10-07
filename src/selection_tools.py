"""Area selection against actual annotation geometry, in overlay coordinates."""

import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QFont, QFontMetricsF, QPainterPath, QPainterPathStroker

from document_model import Mark
from text_editor import text_bounds


def mark_footprint(mark: Mark) -> QPainterPath:
    path = QPainterPath()
    if not mark.points:
        return path
    if mark.kind == 'image':
        from image_capture import image_path
        return image_path(mark)
    points = [QPointF(*p) for p in mark.points]
    if mark.kind == "text":
        path.addRect(text_bounds(mark))
        return path
    if len(points) == 1 or all(p == points[0] for p in points):
        radius = max(mark.width / 2, 1)
        path.addEllipse(points[0], radius, radius)
        return path
    if mark.kind in ("rectangle", "ellipse"):
        rect = QRectF(points[0], points[-1]).normalized()
        if mark.kind == "rectangle":
            path.addRect(rect)
        else:
            path.addEllipse(rect)
    else:
        if mark.kind=='pen' and mark.neon:
            from pen_effects import smooth_path
            path=smooth_path(mark.points)
        else:
            path.moveTo(points[0])
            for point in points[1:]:
                path.lineTo(point)
        if mark.kind == "arrow":
            angle = math.atan2(points[-1].y() - points[0].y(), points[-1].x() - points[0].x())
            length = max(12, mark.width * 4)
            for offset in (-0.55, 0.55):
                path.moveTo(points[-1])
                path.lineTo(points[-1].x() - length * math.cos(angle + offset),
                            points[-1].y() - length * math.sin(angle + offset))
    stroke = QPainterPathStroker()
    stroke.setWidth(max(mark.width, 1))
    stroke.setCapStyle(Qt.PenCapStyle.SquareCap if mark.kind == "highlight" else Qt.PenCapStyle.RoundCap)
    stroke.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    return stroke.createStroke(path)


def indices_in_region(marks: list[Mark], region: QPainterPath) -> set[int]:
    if region.isEmpty():
        return set()
    result = set()
    for index, mark in enumerate(marks):
        footprint = mark_footprint(mark)
        if region.intersects(footprint) or region.contains(footprint):
            result.add(index)
    return result
