"""SR Inqly: a Windows screen annotation overlay."""

from __future__ import annotations

import ctypes
import math
import sys
import time
import os
import threading
import re
from copy import deepcopy
from pathlib import Path
from datetime import datetime
from uuid import uuid4

from PySide6.QtCore import QPoint, QPointF, QRect, QRectF, QSize, Qt, QAbstractNativeEventFilter, Signal, QStandardPaths, QTimer
from PySide6.QtGui import QColor, QFont, QGuiApplication, QImage, QKeySequence, QPainter, QPainterPath, QPen, QRegion
from PySide6.QtWidgets import (
    QApplication, QColorDialog, QFileDialog, QFrame, QHBoxLayout, QLabel,
    QFontComboBox, QSpinBox, QScrollArea, QSizePolicy, QMessageBox, QPushButton, QSlider, QVBoxLayout, QWidget,
)

from document_model import Document, Mark, TextStyle
from text_editor import InlineTextEditor, draw_text, style_for, text_bounds
from selection_tools import indices_in_region, mark_footprint
from icons import icon, crosshair_cursor
from appearance import Appearance
from render_cache import RenderCache, SceneCache
from image_capture import Fetcher, draw_image, image_path
from branding import NAME, VERSION, resource


TOOLS = ["select", "pen", "highlight", "line", "rectangle", "ellipse", "arrow", "text", "eraser", "fetcher"]
TOOL_LABELS = {
    "select": "Select", "pen": "Pen", "highlight": "Highlight", "line": "Line",
    "rectangle": "Rectangle", "ellipse": "Ellipse", "arrow": "Arrow",
    "text": "Text", "eraser": "Eraser",
    'fetcher': 'Fetcher',
}
SWATCHES = ["#ff4655", "#ffcb3d", "#57dd9b", "#40b9ff", "#a895ff", "#ffffff", "#111827"]
SELECT_HINTS = {
    "smart": "Click to select; drag to move. Drag empty space to select several.",
    "move": "Drag any selected annotation to move the whole selection.",
    "box": "Click two corners, or drag a box around annotations.",
    "lasso": "Drag a freehand loop around annotations; release to select.",
    "polygon": "Click corners. Enter, double-click or click the first point to finish.",
}


def virtual_geometry() -> QRect:
    screens = QGuiApplication.screens()
    result = screens[0].geometry()
    for screen in screens[1:]:
        result = result.united(screen.geometry())
    return result


def draw_mark(painter: QPainter, mark: Mark) -> None:
    if not mark.points:
        return
    painter.save()
    if mark.kind != "text":
        painter.setOpacity(mark.opacity)
    color = QColor(mark.color)
    if mark.kind == "highlight":
        color.setAlpha(105)
    pen = QPen(color, mark.width, Qt.PenStyle.SolidLine,
               (Qt.PenCapStyle.SquareCap if mark.kind == "highlight" else Qt.PenCapStyle.RoundCap), Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    pts = [QPointF(*point) for point in mark.points]
    if mark.kind in ("pen", "highlight"):
        path = QPainterPath(pts[0])
        for point in pts[1:]:
            path.lineTo(point)
        if len(pts) == 1:
            painter.drawPoint(pts[0])
        else:
            painter.drawPath(path)
    elif mark.kind in ("line", "arrow") and len(pts) > 1:
        painter.drawLine(pts[0], pts[-1])
        if mark.kind == "arrow":
            dx, dy = pts[-1].x() - pts[0].x(), pts[-1].y() - pts[0].y()
            angle = math.atan2(dy, dx)
            length = max(12, mark.width * 4)
            for offset in (-0.55, 0.55):
                tail = QPointF(pts[-1].x() - length * math.cos(angle + offset),
                               pts[-1].y() - length * math.sin(angle + offset))
                painter.drawLine(pts[-1], tail)
    elif mark.kind in ("rectangle", "ellipse") and len(pts) > 1:
        rect = QRectF(pts[0], pts[-1]).normalized()
        if mark.kind == "rectangle":
            painter.drawRect(rect)
        else:
            painter.drawEllipse(rect)
    elif mark.kind == "text":
        draw_text(painter, mark)
    elif mark.kind == 'image':
        draw_image(painter, mark)
    painter.restore()


class Overlay(QWidget):
    changed = Signal()
    message = Signal(str)

    def __init__(self, document: Document):
        super().__init__()
        self.document = document
        self.render_cache = RenderCache(draw_mark)
        self.scene_cache = SceneCache(self.render_cache)
        self.preview_path = QPainterPath()
        self.tool = "pen"
        self.color = SWATCHES[0]
        self.width = 4
        self.pen_color = self.color
        self.pen_width = 4
        self.highlighter_color = '#ffcb3d'
        self.highlighter_width = 20
        self.opacity = 1.0
        self.highlight_opacity = 1.0
        self.selected: set[int] = set()
        self.selection_mode = "smart"
        self.selection_operation = "replace"
        self.text_defaults = TextStyle()
        self.text_editor: InlineTextEditor | None = None
        self.selection_points: list[QPointF] = []
        self.selection_hover: QPointF | None = None
        self.selection_region = QPainterPath()
        self.box_dragged = False
        self.preview: Mark | None = None
        self.drag_start: QPointF | None = None
        self.originals: dict[int, Mark] = {}
        self.move_started = False
        self.click_through = False
        self.cursor_color = '#172033'
        self.cursor_width = 2
        self.cursor_size = 20
        self.annotations_visible = True
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool |
                            Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMouseTracking(True)
        self.setGeometry(virtual_geometry())
        self.fetcher = Fetcher(self)
        self.display_dpi = tuple((s.name(),s.devicePixelRatio(),s.logicalDotsPerInch())
                                 for s in QGuiApplication.screens())
        self.update_cursor()
        self.display_timer = QTimer(self)
        self.display_timer.setSingleShot(True)
        self.display_timer.timeout.connect(self.refresh_displays)
        app = QGuiApplication.instance()
        app.screenAdded.connect(self.watch_screen)
        app.screenRemoved.connect(lambda _screen: self.display_timer.start(100))
        for screen in app.screens():
            self.watch_screen(screen)

    def watch_screen(self, screen):
        screen.geometryChanged.connect(lambda _value: self.display_timer.start(100))
        screen.logicalDotsPerInchChanged.connect(lambda _value: self.display_timer.start(100))
        self.display_timer.start(100)

    def refresh_displays(self):
        if not QGuiApplication.screens():
            return
        geometry = virtual_geometry()
        dpi = tuple((s.name(),s.devicePixelRatio(),s.logicalDotsPerInch()) for s in QGuiApplication.screens())
        if geometry == self.geometry() and dpi == self.display_dpi:
            return
        self.display_dpi = dpi
        self.set_click_through(True)
        self.cancel_gesture()
        self.setGeometry(geometry)
        self.render_cache.clear()
        for child in self.findChildren(QWidget, options=Qt.FindDirectChildrenOnly):
            if isinstance(child, Toolbar):
                child.fit_toolbar()
        self.message.emit('Display layout changed · desktop mode')
        self.update()

    def set_tool(self, tool: str) -> None:
        if tool not in TOOLS:
            return
        self.finish_text()
        if self.tool == 'highlight':
            self.highlighter_color, self.highlighter_width = self.color, self.width
        else:
            self.pen_color, self.pen_width = self.color, self.width
        if tool == 'highlight':
            self.color, self.width = self.highlighter_color, self.highlighter_width
        else:
            self.color, self.width = self.pen_color, self.pen_width
        self.tool = tool
        self.cancel_gesture()
        if tool != "select":
            self.selected.clear()
            self.selection_region = QPainterPath()
        self.update()
        self.update_cursor()
        self.changed.emit()

    def update_cursor(self) -> None:
        if self.click_through:
            self.setCursor(Qt.ArrowCursor)
        elif self.tool == 'text':
            self.setCursor(Qt.IBeamCursor)
        elif self.tool == 'select' and self.selection_mode == 'smart':
            self.setCursor(Qt.ArrowCursor)
        elif self.tool == 'select' and self.selection_mode == 'move':
            self.setCursor(Qt.SizeAllCursor)
        else:
            self.setCursor(crosshair_cursor(self.cursor_color, self.cursor_width, self.cursor_size))

    def hit_mark(self, x, y):
        for index in range(len(self.document.marks) - 1, -1, -1):
            mark = self.document.marks[index]
            if mark.kind == "text":
                if text_bounds(mark).adjusted(-4, -4, 4, 4).contains(QPointF(x, y)):
                    return index
            elif mark.kind == 'image':
                if image_path(mark).contains(QPointF(x,y)):
                    return index
            elif mark.hit(x, y):
                return index
        return None

    def begin_text(self, point: QPointF | None = None, index: int | None = None):
        self.finish_text()
        self.cancel_gesture()
        if index is not None:
            mark = deepcopy(self.document.marks[index])
            mark.text_style = style_for(mark)
            self.selected = {index}
        else:
            self.selected.clear()
            mark = Mark("text", [(point.x(), point.y())], self.color,
                        text_style=deepcopy(self.text_defaults), text_box=(280, 80))
        self.tool = "text"
        self.update_cursor()
        self.text_defaults = style_for(mark)
        self.color = mark.color
        editor = InlineTextEditor(self, mark, index)
        self.text_editor = editor
        editor.styleChanged.connect(lambda values: self.apply_text_style(**values))
        editor.deleteRequested.connect(self.delete_live_text)
        editor.accepted.connect(self.finish_text)
        editor.cancelled.connect(lambda: self.finish_text(False))
        editor.desktopRequested.connect(lambda: self.set_click_through(True))
        editor.show()
        editor.move(max(0, min(editor.x(), self.rect().width()-editor.width())),
                    max(0, min(editor.y(), self.height()-editor.height())))
        editor.raise_()
        self.activateWindow()
        editor.input.setFocus(Qt.FocusReason.MouseFocusReason)
        self.changed.emit()
        self.update()

    def delete_live_text(self):
        if self.text_editor is None:
            return
        index = self.text_editor.index
        self.finish_text(False)
        if index is not None:
            self.document.delete(index)
        self.selected.clear()
        self.changed.emit()
        self.update()

    def finish_text(self, commit=True):
        editor = self.text_editor
        if editor is None:
            return
        mark = editor.result()
        index = editor.index
        self.text_editor = None
        editor.hide()
        editor.deleteLater()
        if commit:
            if mark.text.strip():
                if index is None:
                    self.document.checkpoint()
                    self.document.marks.append(mark)
                    index = len(self.document.marks) - 1
                elif mark != self.document.marks[index]:
                    self.document.checkpoint()
                    self.document.marks[index] = mark
                self.selected = {index}
            elif index is not None:
                self.document.delete(index)
                self.selected.clear()
        self.changed.emit()
        self.update()

    def apply_text_style(self, **values):
        for key, value in values.items():
            if key == "color":
                self.color = value
            else:
                setattr(self.text_defaults, key, value)
        if self.text_editor:
            mark = self.text_editor.mark
            for key, value in values.items():
                if key == "color":
                    mark.color = value
                else:
                    setattr(mark.text_style, key, value)
            self.text_editor.apply_style()
        else:
            targets = [i for i in self.selected if self.document.marks[i].kind == "text"]
            if targets:
                self.document.checkpoint()
                for index in targets:
                    mark = deepcopy(self.document.marks[index])
                    mark.text_style = style_for(mark)
                    for key, value in values.items():
                        if key == "color":
                            mark.color = value
                        else:
                            setattr(mark.text_style, key, value)
                    if mark.text_box:
                        mark.text_box = (mark.text_box[0], 0)
                        mark.text_box = (mark.text_box[0], text_bounds(mark).height())
                    self.document.marks[index] = mark
        self.changed.emit()
        self.update()

    def cancel_gesture(self) -> None:
        self.fetcher.cancel()
        self.preview = None
        self.selection_points.clear()
        self.selection_hover = None
        self.box_dragged = False
        self.drag_start = None
        self.originals.clear()
        self.move_started = False
        self.update()

    def set_selection_mode(self, mode: str) -> None:
        if mode not in ("smart", "move", "box", "lasso", "polygon"):
            return
        self.finish_text()
        self.cancel_gesture()
        self.tool = "select"
        self.selection_mode = mode
        self.update_cursor()
        self.changed.emit()

    def set_selection_operation(self, operation: str) -> None:
        if operation in ("replace", "add", "subtract"):
            self.selection_operation = operation
            self.changed.emit()

    def select_all(self) -> None:
        self.cancel_gesture()
        self.tool = "select"
        self.selected = set(range(len(self.document.marks)))
        self.selection_region = QPainterPath()
        self.update_cursor()
        self.changed.emit()
        self.update()

    def deselect(self) -> None:
        self.cancel_gesture()
        self.selected.clear()
        self.selection_region = QPainterPath()
        self.changed.emit()
        self.update()

    def pending_region(self, preview: bool = False) -> QPainterPath:
        path = QPainterPath()
        if not self.selection_points:
            return path
        if self.selection_mode in ("box", "smart"):
            path.addRect(QRectF(self.selection_points[0],
                               self.selection_hover or self.selection_points[0]).normalized())
        else:
            path.moveTo(self.selection_points[0])
            for point in self.selection_points[1:]:
                path.lineTo(point)
            if preview and self.selection_mode == "polygon" and self.selection_hover:
                path.lineTo(self.selection_hover)
            path.closeSubpath()
        return path

    def finish_selection(self) -> None:
        if not self.selection_points:
            return
        if self.selection_mode in ("polygon", "lasso") and len(self.selection_points) < 3:
            return
        region = self.pending_region()
        if region.boundingRect().width() < 2 or region.boundingRect().height() < 2:
            self.cancel_gesture()
            return
        hits = indices_in_region(self.document.marks, region)
        if self.selection_operation == "add":
            self.selected |= hits
            self.selection_region = self.selection_region.united(region)
        elif self.selection_operation == "subtract":
            self.selected -= hits
            self.selection_region = self.selection_region.subtracted(region)
        else:
            self.selected = hits
            self.selection_region = region
        self.cancel_gesture()
        self.message.emit(f"{len(self.selected)} annotations selected")
        self.changed.emit()
        self.update()

    def set_click_through(self, enabled: bool) -> None:
        if enabled:
            self.finish_text()
            self.cancel_gesture()
            if QWidget.mouseGrabber() is self:
                self.releaseMouse()
        self.click_through = enabled
        self.update_cursor()
        if sys.platform == "win32":
            hwnd = int(self.winId())
            user32 = ctypes.windll.user32
            get_style = user32.GetWindowLongPtrW if ctypes.sizeof(ctypes.c_void_p) == 8 else user32.GetWindowLongW
            set_style = user32.SetWindowLongPtrW if ctypes.sizeof(ctypes.c_void_p) == 8 else user32.SetWindowLongW
            get_style.argtypes = [ctypes.c_void_p, ctypes.c_int]
            get_style.restype = ctypes.c_ssize_t
            set_style.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_ssize_t]
            set_style.restype = ctypes.c_ssize_t
            old = get_style(hwnd, -20)
            new = old | 0x20 | 0x80000 if enabled else old & ~0x20
            set_style(hwnd, -20, new)
            user32.SetWindowPos(ctypes.c_void_p(hwnd), None, 0, 0, 0, 0,
                                0x0001 | 0x0002 | 0x0004 | 0x0020)
        self.message.emit("Click-through on: use the toolbar or Ctrl+Alt+D to draw again" if enabled
                          else "Drawing mode")
        self.changed.emit()
        self.update()

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        # A fully transparent layered window is skipped by Windows hit testing.
        # One alpha level is visually negligible but lets the overlay receive
        # real mouse input. Click-through mode still uses WS_EX_TRANSPARENT.
        # Replace the previous backing-store pixels, including old child-widget
        # borders. SourceOver with alpha=1 leaves visible trails after dragging.
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 1))
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
        if not self.annotations_visible:
            painter.end()
            return
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.scene_cache.paint(painter, self.document.marks, QRectF(_event.rect()), self.size(), self.devicePixelRatioF(),
                              self.text_editor.index if self.text_editor else None)
        if self.preview:
            if self.preview.kind in ('pen', 'highlight') and len(self.preview.points) > 1:
                color = QColor(self.preview.color)
                if self.preview.kind == 'highlight':
                    color.setAlpha(105)
                painter.save()
                painter.setOpacity(self.preview.opacity)
                painter.setPen(QPen(color,self.preview.width,Qt.SolidLine,Qt.SquareCap if self.preview.kind=="highlight" else Qt.RoundCap,Qt.RoundJoin))
                painter.drawPath(self.preview_path)
                painter.restore()
            else:
                draw_mark(painter, self.preview)
        if self.tool == "select" and not self.click_through:
            for index in sorted(self.selected):
                if index < len(self.document.marks):
                    bounds = mark_footprint(self.document.marks[index]).boundingRect().adjusted(-4, -4, 4, 4)
                    painter.setPen(QPen(QColor("#65d9ff"), 1.5))
                    painter.setBrush(QColor(70, 190, 255, 18))
                    painter.drawRect(bounds)
            for path in (self.selection_region, self.pending_region(preview=True)):
                if path.isEmpty():
                    continue
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.setPen(QPen(QColor("#142033"), 2))
                painter.drawPath(path)
                painter.setPen(QPen(QColor("#ffffff"), 1, Qt.PenStyle.DashLine))
                painter.drawPath(path)
            if self.selection_mode == "polygon":
                painter.setPen(QPen(QColor("#102337"), 1))
                painter.setBrush(QColor("#67d9ff"))
                for point in self.selection_points:
                    painter.drawEllipse(point, 3, 3)
        self.fetcher.paint(painter)
        painter.end()

    def mousePressEvent(self, event) -> None:
        if self.click_through:
            return
        if event.button() == Qt.MouseButton.RightButton and self.tool == "select":
            self.cancel_gesture()
            return
        if event.button() != Qt.MouseButton.LeftButton:
            return
        if self.fetcher.press(event):
            return
        self.finish_text()
        point = event.position()
        x, y = point.x(), point.y()
        self.drag_start = point
        if self.tool == "select":
            if self.selection_mode in ("smart", "move"):
                hit = self.hit_mark(x, y)
                if hit is not None:
                    if self.selection_operation == "subtract":
                        self.selected.discard(hit)
                    else:
                        if hit not in self.selected:
                            if self.selection_operation == "replace":
                                self.selected.clear()
                            self.selected.add(hit)
                        self.originals = {i: self.document.marks[i].moved(0, 0) for i in self.selected}
                        self.move_started = False
                elif self.selection_operation == "replace":
                    self.selected.clear()
                    self.selection_region = QPainterPath()
                if hit is None and self.selection_mode == "smart":
                    self.selection_points = [point]
                    self.selection_hover = point
                    self.box_dragged = False
                self.changed.emit()
            elif self.selection_mode == "box":
                self.selection_hover = point
                if self.selection_points:
                    self.finish_selection()
                else:
                    self.selection_points = [point]
                    self.box_dragged = False
            elif self.selection_mode == "lasso":
                self.selection_points = [point]
            elif self.selection_mode == "polygon":
                if len(self.selection_points) >= 3 and (point - self.selection_points[0]).manhattanLength() < 10:
                    self.finish_selection()
                elif not self.selection_points or (point - self.selection_points[-1]).manhattanLength() > 1:
                    self.selection_points.append(point)
                self.selection_hover = point
        elif self.tool == "eraser":
            self.erase_at(x, y)
        elif self.tool == "text":
            hit = self.hit_mark(x, y)
            self.begin_text(point, hit if hit is not None and self.document.marks[hit].kind == "text" else None)
        else:
            kind = "highlight" if self.tool == "highlight" else self.tool
            width = self.width
            self.preview = Mark(kind, [(x, y)], self.color, width,
                                opacity=self.highlight_opacity if kind == "highlight" else self.opacity)
            self.preview_path = QPainterPath(point)
        self.update()

    def mouseMoveEvent(self, event) -> None:
        point = event.position()
        if self.click_through:
            return
        if self.fetcher.move(event):
            return
        if self.tool == "select" and self.selection_points:
            self.selection_hover = point
            if self.selection_mode in ("box", "smart") and event.buttons() & Qt.MouseButton.LeftButton:
                if (point - self.selection_points[0]).manhattanLength() > 4:
                    self.box_dragged = True
            elif self.selection_mode == "lasso" and event.buttons() & Qt.MouseButton.LeftButton:
                if (point - self.selection_points[-1]).manhattanLength() >= 2:
                    self.selection_points.append(point)
            self.update()
            return
        if not (event.buttons() & Qt.MouseButton.LeftButton):
            return
        if self.tool == "select" and self.originals and self.drag_start:
            dirty=QRectF(self.fetcher.bar.geometry()).united(self.selection_region.boundingRect())
            for index in self.originals:
                left,top,right,bottom=self.document.marks[index].bounds()
                dirty=dirty.united(QRectF(left,top,right-left,bottom-top))
            dx, dy = point.x() - self.drag_start.x(), point.y() - self.drag_start.y()
            if not self.move_started and math.hypot(dx, dy) >= 2:
                self.document.checkpoint()
                self.move_started = True
                self.selection_region = QPainterPath()
            if self.move_started:
                for index, mark in self.originals.items():
                    self.document.marks[index] = mark.moved(dx, dy)
                self.fetcher.refresh(False,False)
                for index in self.originals:
                    left,top,right,bottom=self.document.marks[index].bounds()
                    dirty=dirty.united(QRectF(left,top,right-left,bottom-top))
                dirty=dirty.united(QRectF(self.fetcher.bar.geometry())).adjusted(-40,-40,40,40)
                self.update(dirty.toAlignedRect())
                return
        elif self.tool == "eraser":
            self.erase_at(point.x(), point.y())
        elif self.preview:
            if self.preview.kind in ("pen", "highlight"):
                last = QPointF(*self.preview.points[-1])
                if (point-last).manhattanLength() < 0.5:
                    return
                self.preview.points.append((point.x(), point.y()))
                self.preview_path.lineTo(point)
                margin = self.preview.width/2 + 3
                dirty = QRectF(last,point).normalized().adjusted(-margin,-margin,margin,margin)
                self.update(dirty.toAlignedRect())
                return
            else:
                old = QRectF(QPointF(*self.preview.points[0]),QPointF(*self.preview.points[-1])).normalized()
                self.preview.points = [self.preview.points[0], (point.x(), point.y())]
                new = QRectF(QPointF(*self.preview.points[0]),point).normalized()
                margin = max(14,self.preview.width*4+3)
                self.update(old.united(new).adjusted(-margin,-margin,margin,margin).toAlignedRect())
                return
        self.update()

    def mouseReleaseEvent(self, event) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            return
        if self.fetcher.release(event):
            return
        if self.tool == "select" and self.selection_points:
            if self.selection_mode in ("box", "smart") and self.box_dragged:
                self.selection_hover = event.position()
                self.finish_selection()
            elif self.selection_mode == "smart":
                self.cancel_gesture()
            elif self.selection_mode == "lasso":
                self.selection_points.append(event.position())
                self.finish_selection()
                self.cancel_gesture()
            return
        if self.preview:
            endpoint = (event.position().x(),event.position().y())
            if self.preview.kind in ('pen','highlight') and endpoint != self.preview.points[-1]:
                self.preview.points.append(endpoint)
            if self.preview.kind in ("pen", "highlight") and len(self.preview.points) == 1:
                self.preview.points.append(self.preview.points[0])
            if len(self.preview.points) >= 2:
                self.document.checkpoint()
                self.document.marks.append(self.preview)
                self.changed.emit()
            self.preview = None
        self.drag_start = None
        self.originals.clear()
        self.update()

    def mouseDoubleClickEvent(self, event) -> None:
        if self.tool in ("select", "text") and event.button() == Qt.MouseButton.LeftButton:
            hit = self.hit_mark(event.position().x(), event.position().y())
            if hit is not None and self.document.marks[hit].kind == "text":
                self.begin_text(index=hit)
                return
        if self.tool == "select" and self.selection_mode == "polygon" and event.button() == Qt.MouseButton.LeftButton:
            if self.selection_points and (event.position() - self.selection_points[-1]).manhattanLength() > 1:
                self.selection_points.append(event.position())
            self.finish_selection()

    def erase_at(self, x: float, y: float) -> None:
        index = self.document.hit(x, y)
        if index is not None:
            self.document.delete(index)
            self.deselect()
            self.changed.emit()
            self.update()

    def undo(self) -> None:
        if self.text_editor:
            self.text_editor.input.undo()
            return
        if self.document.undo():
            self.deselect()
            self.changed.emit()
            self.update()

    def redo(self) -> None:
        if self.text_editor:
            self.text_editor.input.redo()
            return
        if self.document.redo():
            self.deselect()
            self.changed.emit()
            self.update()

    def copy(self) -> None:
        self.finish_text()
        if self.fetcher.selected()[1] is not None:
            self.fetcher.copy()
            return
        if self.document.copy_many(self.selected):
            self.message.emit(f"{len(self.selected)} annotations copied")
            self.changed.emit()

    def paste(self) -> None:
        self.finish_text()
        pasted = self.document.paste_many()
        if not pasted:
            return
        self.cancel_gesture()
        self.selected = pasted
        self.selection_region = QPainterPath()
        self.tool = "select"
        self.selection_mode = "move"
        self.update_cursor()
        self.changed.emit()
        self.update()

    def duplicate(self) -> None:
        self.finish_text()
        if self.document.copy_many(self.selected):
            self.paste()

    def delete_selected(self) -> None:
        self.finish_text()
        self.document.delete_many(self.selected)
        self.deselect()
        self.changed.emit()
        self.update()

    def clear(self) -> None:
        self.finish_text()
        self.document.clear()
        self.deselect()
        self.changed.emit()
        self.update()

    def keyPressEvent(self, event) -> None:
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and self.selection_points:
            self.finish_selection()
        elif event.key() == Qt.Key.Key_Backspace and self.selection_mode == "polygon" and self.selection_points:
            self.selection_points.pop()
            self.update()
        elif event.key() == Qt.Key.Key_A and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                self.deselect()
            else:
                self.select_all()
        elif event.key() == Qt.Key.Key_D and event.modifiers() & Qt.ControlModifier:
            self.duplicate()
        elif event.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            self.delete_selected()
        elif event.matches(QKeySequence.StandardKey.Copy):
            self.copy()
        elif event.matches(QKeySequence.StandardKey.Paste):
            self.paste()
        elif event.matches(QKeySequence.StandardKey.Undo):
            self.undo()
        elif event.matches(QKeySequence.StandardKey.Redo):
            self.redo()
        elif event.key() == Qt.Key.Key_Escape:
            self.set_click_through(True)


class HotkeyFilter(QAbstractNativeEventFilter):
    def __init__(self, callbacks: dict[int, callable]):
        super().__init__()
        self.callbacks = callbacks

    def nativeEventFilter(self, event_type, message):
        if event_type == b"windows_generic_MSG":
            address = int(message)
            msg = ctypes.cast(address, ctypes.POINTER(WINMSG)).contents
            if msg.message == 0x0312 and msg.wParam in self.callbacks:
                self.callbacks[msg.wParam]()
                return True, 0
        return False, 0


class WINMSG(ctypes.Structure):
    _fields_ = [("hwnd", ctypes.c_void_p), ("message", ctypes.c_uint),
                ("wParam", ctypes.c_size_t), ("lParam", ctypes.c_ssize_t),
                ("time", ctypes.c_uint), ("pt_x", ctypes.c_long), ("pt_y", ctypes.c_long)]


class Toolbar(QWidget):
    def __init__(self, overlay: Overlay):
        # An owned tool window stays above its overlay when drawing activates it.
        super().__init__(overlay)
        self.overlay = overlay
        self.drag_origin: QPoint | None = None
        self.ui_scale = 1.0
        self._scale_snapshot = None
        self.setFixedWidth(320)
        self.setWindowTitle("SR Inqly")
        self.setWindowFlags(Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint |
                            Qt.WindowType.WindowStaysOnTopHint)
        self.setObjectName("panel")
        self.setCursor(Qt.ArrowCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet("""
            QWidget#panel { background: #171d2b; border: 1px solid #40506a; border-radius: 15px; }
            QLabel { color: #edf3ff; border: none; }
            QComboBox, QSpinBox { color: #edf3ff; background: #293348; border: 1px solid #43516a;
                                 border-radius: 5px; padding: 4px; font-size: 12px; }
            QScrollArea, QScrollArea > QWidget > QWidget { background: #171d2b; border: none; }
            QPushButton { color: #e9f0fa; background: #293348; border: 1px solid #43516a;
                          border-radius: 8px; padding: 6px 8px; font-size: 12px; }
            QPushButton:hover { background: #3b4d69; }
            QPushButton:disabled { background: #212a3b; border-color: #313d51; }
            QPushButton:checked { color: #0c1622; background: #67d9ff; border-color: #67d9ff; }
            QPushButton#danger { background: #4a2935; }
            QSlider::groove:horizontal { height: 5px; background: #49566a; border-radius: 2px; }
            QSlider::handle:horizontal { background: #67d9ff; width: 14px; margin: -5px 0; border-radius: 7px; }
        """)
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 10, 12, 12)
        root.setSpacing(8)
        header = QHBoxLayout()
        self.title = QLabel("SR Inqly 2.0.4")
        self.title.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.title.setStyleSheet("font-size: 13px; font-weight: 700; color: #d8f5ff;")
        header.addWidget(self.title)
        header.addStretch()
        self.minimize_button = self.button("−", self.toggle_compact, "Compact toolbar")
        self.minimize_button.setFixedWidth(32)
        self.minimize_button.setStyleSheet("padding: 3px;")
        header.addWidget(self.minimize_button)
        close = self.button("×", self.close_app, "Exit SR Inqly")
        close.setFixedWidth(32)
        close.setStyleSheet("padding: 3px;")
        header.addWidget(close)
        root.addLayout(header)

        self.body = QWidget()
        body = QVBoxLayout(self.body)
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(8)
        self.tool_buttons: dict[str, QPushButton] = {}
        self.active_tool_label = QLabel("DRAWING TOOLS")
        self.active_tool_label.setStyleSheet("color: #9db2ca; font-size: 10px; letter-spacing: 1px;")
        body.addWidget(self.active_tool_label)
        for row_tools in (TOOLS[:3], TOOLS[3:6], TOOLS[6:]):
            row = QHBoxLayout()
            for tool in row_tools:
                button = self.button(TOOL_LABELS[tool], lambda _=False, t=tool: self.toggle_tool(t),
                                     "Select & move: click an item, or drag a selection box" if tool == "select" else TOOL_LABELS[tool], tool)
                button.setCheckable(True)
                button.setFixedHeight(42)
                self.tool_buttons[tool] = button
                row.addWidget(button)
            body.addLayout(row)
        self.selection_panel = QWidget()
        selection_layout = QVBoxLayout(self.selection_panel)
        selection_layout.setContentsMargins(0, 2, 0, 4)
        selection_layout.setSpacing(6)
        selection_header = QHBoxLayout()
        selection_header.addWidget(QLabel("SELECT & MOVE"))
        self.selection_count = QLabel("0 selected")
        self.selection_count.setStyleSheet("color: #67d9ff; font-size: 11px;")
        selection_header.addStretch()
        selection_header.addWidget(self.selection_count)
        selection_layout.addLayout(selection_header)
        simple_row = QHBoxLayout()
        smart_button = self.button("Select", lambda: self.choose_selection_mode("smart"),
                                   SELECT_HINTS["smart"], "select", True)
        smart_button.setCheckable(True)
        simple_row.addWidget(smart_button, 1)
        self.multiple_button = self.button("Multiple", self.toggle_multiple, "Keep adding to the selection", "add")
        self.multiple_button.setCheckable(True)
        simple_row.addWidget(self.multiple_button)
        self.more_selection = self.button("More selection tools", self.toggle_advanced, "More: box, lasso, polygon", "more")
        self.more_selection.setCheckable(True)
        simple_row.addWidget(self.more_selection)
        selection_layout.addLayout(simple_row)
        self.advanced_selection = QWidget()
        advanced_layout = QVBoxLayout(self.advanced_selection)
        advanced_layout.setContentsMargins(0, 0, 0, 0)
        advanced_layout.setSpacing(6)
        selection_row = QHBoxLayout()
        self.selection_buttons = {"smart": smart_button}
        for mode, label in (("move", "Move selection"), ("box", "Rectangle selection"),
                            ("lasso", "Freehand lasso"), ("polygon", "Polygon selection")):
            button = self.button(label, lambda _=False, m=mode: self.choose_selection_mode(m),
                                 f"{label}: {SELECT_HINTS[mode]}", mode)
            button.setCheckable(True)
            self.selection_buttons[mode] = button
            selection_row.addWidget(button)
        advanced_layout.addLayout(selection_row)
        operation_row = QHBoxLayout()
        operation_row.setSpacing(4)
        self.operation_buttons = {}
        for operation, label in (("replace", "New selection"), ("add", "Add to selection"),
                                 ("subtract", "Subtract from selection")):
            button = self.button(label, lambda _=False, op=operation: overlay.set_selection_operation(op),
                                 f"{label} — no keyboard modifier needed", operation)
            button.setCheckable(True)
            self.operation_buttons[operation] = button
            operation_row.addWidget(button)
        operation_row.addSpacing(8)
        operation_row.addWidget(self.button("Select all", overlay.select_all, "Select all annotations (Ctrl+A)", "all"))
        operation_row.addWidget(self.button("Deselect", overlay.deselect, "Deselect all (Ctrl+Shift+A)", "none"))
        advanced_layout.addLayout(operation_row)
        selection_layout.addWidget(self.advanced_selection)
        self.advanced_selection.hide()
        self.selection_hint = QLabel()
        self.selection_hint.setWordWrap(True)
        self.selection_hint.setStyleSheet("color: #afc0d6; font-size: 11px;")
        selection_layout.addWidget(self.selection_hint)
        body.addWidget(self.selection_panel)
        self.text_panel = QWidget()
        text_layout = QVBoxLayout(self.text_panel)
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(6)
        text_layout.addWidget(QLabel("TEXT STYLE"))
        font_row = QHBoxLayout()
        self.font_family = QFontComboBox()
        self.font_family.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self.font_family.setMinimumWidth(0)
        self.font_family.setToolTip("Font family")
        self.font_family.currentFontChanged.connect(lambda font: overlay.apply_text_style(family=font.family()))
        font_row.addWidget(self.font_family, 1)
        self.font_size = QSpinBox()
        self.font_size.setRange(6, 200)
        self.font_size.setSuffix(" pt")
        self.font_size.setFixedWidth(83)
        self.font_size.setKeyboardTracking(False)
        self.font_size.setToolTip("Text font size")
        self.font_size.valueChanged.connect(lambda value: overlay.apply_text_style(size=float(value)))
        font_row.addWidget(self.font_size)
        text_layout.addLayout(font_row)
        style_row = QHBoxLayout()
        self.text_style_buttons = {}
        for key in ("bold", "italic", "underline", "strike"):
            button = self.button(key.title(), lambda checked, k=key: overlay.apply_text_style(**{k: checked}), key.title(), key)
            button.setCheckable(True)
            self.text_style_buttons[key] = button
            style_row.addWidget(button)
        text_layout.addLayout(style_row)
        align_row = QHBoxLayout()
        self.align_buttons = {}
        for align in ("left", "center", "right"):
            button = self.button(align.title(), lambda _=False, a=align: overlay.apply_text_style(align=a), f"Align {align}", f"align_{align}")
            button.setCheckable(True)
            self.align_buttons[align] = button
            align_row.addWidget(button)
        align_row.addWidget(self.button("Text background", self.pick_text_background, "Set text background color", "background"))
        align_row.addWidget(self.button("Transparent background", lambda: overlay.apply_text_style(background=""), "Remove text background", "none"))
        text_layout.addLayout(align_row)
        misc_row = QHBoxLayout()
        misc_row.addWidget(QLabel("Opacity"))
        self.text_opacity = QSpinBox()
        self.text_opacity.setRange(10, 100)
        self.text_opacity.setSuffix("%")
        self.text_opacity.setKeyboardTracking(False)
        self.text_opacity.setFixedWidth(85)
        self.text_opacity.valueChanged.connect(lambda value: overlay.apply_text_style(opacity=value / 100))
        misc_row.addStretch()
        misc_row.addWidget(self.text_opacity)
        text_layout.addLayout(misc_row)
        spacing_row = QHBoxLayout()
        spacing_row.addWidget(QLabel("Line spacing"))
        spacing_row.addStretch()
        self.text_spacing = QSpinBox()
        self.text_spacing.setRange(80, 240)
        self.text_spacing.setSuffix("%")
        self.text_spacing.setKeyboardTracking(False)
        self.text_spacing.setFixedWidth(85)
        self.text_spacing.setToolTip("Line spacing")
        self.text_spacing.valueChanged.connect(lambda value: overlay.apply_text_style(line_spacing=value))
        spacing_row.addWidget(self.text_spacing)
        text_layout.addLayout(spacing_row)
        body.addWidget(self.text_panel)
        row = QHBoxLayout()
        for color in SWATCHES:
            swatch = QPushButton("")
            swatch.setFixedSize(24, 24)
            swatch.setToolTip(color)
            swatch.setAccessibleName(f"Ink color {color}")
            swatch.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            swatch.setStyleSheet(f"background: {color}; border: 2px solid #75869b; border-radius: 12px;")
            swatch.clicked.connect(lambda _=False, c=color: self.set_color(c))
            row.addWidget(swatch)
        row.addWidget(self.button("More", self.pick_color, "Choose any color"))
        body.addLayout(row)
        width_row = QHBoxLayout()
        size_icon = QLabel()
        size_icon.setPixmap(icon("size").pixmap(QSize(20, 20)))
        size_icon.setToolTip("Stroke / text size")
        width_row.addWidget(size_icon)
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(1, 20)
        self.slider.setValue(4)
        self.slider.valueChanged.connect(self.set_width)
        width_row.addWidget(self.slider)
        self.size_label = QLabel("4 px")
        width_row.addWidget(self.size_label)
        body.addLayout(width_row)

        opacity_row = QHBoxLayout()
        opacity_icon = QLabel("◐")
        opacity_icon.setToolTip("Color opacity for new strokes and text")
        opacity_row.addWidget(opacity_icon)
        self.opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.opacity_slider.setRange(1, 100)
        self.opacity_slider.setValue(100)
        self.opacity_slider.setToolTip("Color opacity: 1% transparent to 100% solid. Highlighter keeps its translucent base.")
        self.opacity_slider.valueChanged.connect(self.set_opacity)
        opacity_row.addWidget(self.opacity_slider)
        self.opacity_label = QLabel("100%")
        opacity_row.addWidget(self.opacity_label)
        body.addLayout(opacity_row)

        self.action_buttons = {}
        for entries in (
            [("Undo", overlay.undo), ("Redo", overlay.redo), ("Clear", overlay.clear)],
            [("Copy", overlay.copy), ("Paste", overlay.paste), ("Duplicate", overlay.duplicate)],
            [("Delete", overlay.delete_selected), ("PNG", self.save_png), ("Copy PNG", self.copy_png)],
        ):
            row = QHBoxLayout()
            for label, handler in entries:
                button = self.button(label, handler, label)
                self.action_buttons[label] = button
                row.addWidget(button)
            body.addLayout(row)
        self.mode_button = self.button("Start drawing", self.toggle_click, "Switch desktop / drawing mode (Ctrl+Alt+D)", "desktop", True)
        body.addWidget(self.mode_button)
        self.visibility_button = self.button("Hide annotations", self.toggle_annotations, "Temporarily hide all marks", "eye", True)
        body.addWidget(self.visibility_button)
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setWidget(self.body)
        root.addWidget(self.scroll_area)
        scale_row = QHBoxLayout()
        scale_row.addWidget(QLabel("UI size"))
        self.scale_slider = QSlider(Qt.Orientation.Horizontal)
        self.scale_slider.setRange(75, 150)
        self.scale_slider.setValue(100)
        self.scale_slider.setToolTip("Scale the whole toolbar, including buttons and icons")
        scale_row.addWidget(self.scale_slider, 1)
        self.scale_label = QLabel("100%")
        scale_row.addWidget(self.scale_label)
        root.addLayout(scale_row)
        self.status = QLabel("Draw anywhere on the screen")
        self.status.setWordWrap(True)
        self.status.setStyleSheet("color: #9db2ca; font-size: 11px;")
        root.addWidget(self.status)
        from branding_ui import developer_footer
        self.developer_footer = developer_footer(self)
        root.addWidget(self.developer_footer)
        self.appearance = Appearance(self, root, header, scale_row)
        from PySide6.QtGui import QPixmap
        brand_logo = QLabel()
        brand_logo.setProperty('brandLogo',True)
        brand_logo.setPixmap(QPixmap(str(resource('assets/icon-32.png'))).scaled(20,20,Qt.KeepAspectRatio,Qt.SmoothTransformation))
        brand_logo.setToolTip(NAME)
        header.insertWidget(0,brand_logo)
        overlay.changed.connect(self.refresh)
        overlay.message.connect(self.show_status)
        self.capture_scale_baseline()
        self.scale_slider.valueChanged.connect(self.apply_ui_scale)
        self.refresh()
        self.move(QGuiApplication.primaryScreen().availableGeometry().topLeft() + QPoint(28, 28))
        self._register_hotkeys()

    def capture_scale_baseline(self):
        widgets = [self] + self.findChildren(QWidget)
        self._scale_snapshot = [(w, w.styleSheet(), w.minimumSize(), w.maximumSize(),
                                 w.iconSize() if isinstance(w, QPushButton) else None, w.font(),
                                 w.pixmap() if isinstance(w, QLabel) and not w.pixmap().isNull() else None) for w in widgets]
        self._layout_snapshot = []
        def collect(layout):
            if layout is None:
                return
            self._layout_snapshot.append((layout, layout.getContentsMargins(), layout.spacing()))
            for i in range(layout.count()):
                item = layout.itemAt(i)
                if item.layout():
                    collect(item.layout())
        for widget in widgets:
            collect(widget.layout())

    def apply_ui_scale(self, percent):
        self.ui_scale = percent / 100
        scale = self.ui_scale
        for widget, css, minimum, maximum, icon_size, font, pixmap in self._scale_snapshot:
            if widget is self.scroll_area or widget is self.body or widget is self:
                if widget is self:
                    widget.setStyleSheet(re.sub(r"(-?\d+(?:\.\d+)?)px", lambda m: f"{round(float(m[1])*scale)}px", css))
                continue
            widget.setStyleSheet(re.sub(r"(-?\d+(?:\.\d+)?)px", lambda m: f"{round(float(m[1])*scale)}px", css))
            widget.setMinimumSize(round(minimum.width()*scale), round(minimum.height()*scale))
            widget.setMaximumSize(round(maximum.width()*scale) if maximum.width() < 16777215 else 16777215,
                                  round(maximum.height()*scale) if maximum.height() < 16777215 else 16777215)
            scaled_font = QFont(font)
            if font.pointSizeF() > 0:
                scaled_font.setPointSizeF(font.pointSizeF()*scale)
            widget.setFont(scaled_font)
            if icon_size is not None:
                widget.setIconSize(QSize(round(icon_size.width()*scale), round(icon_size.height()*scale)))
            if pixmap is not None:
                widget.setPixmap(pixmap.scaled(round(pixmap.width()*scale), round(pixmap.height()*scale),
                                               Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        for layout, margins, spacing in self._layout_snapshot:
            layout.setContentsMargins(*(round(m*scale) for m in margins))
            if spacing >= 0:
                layout.setSpacing(round(spacing*scale))
        self.setFixedWidth(round(320*scale))
        self.scale_label.setText(f"{percent}%")
        self.appearance._applied_key = None
        self.appearance.apply()
        self.fit_toolbar()

    def fit_toolbar(self):
        if not hasattr(self, "scroll_area"):
            return
        screen = QGuiApplication.screenAt(self.frameGeometry().center()) or QGuiApplication.primaryScreen()
        available = screen.availableGeometry()
        self.body.layout().activate()
        height = min(self.body.sizeHint().height()+2, max(100, available.height()-round(185*self.ui_scale)))
        self.scroll_area.setFixedHeight(height)
        self.adjustSize()
        self.move(max(available.left(), min(self.x(), available.right()-self.width()+1)),
                  max(available.top(), min(self.y(), available.bottom()-self.height()+1)))
        self.sync_input_region()

    def toggle_multiple(self, checked):
        self.overlay.set_selection_operation("add" if checked else "replace")

    def toggle_advanced(self, checked):
        self.advanced_selection.setVisible(checked)
        if not checked:
            self.overlay.set_selection_mode("smart")
        self.fit_toolbar()

    def pick_text_background(self):
        self.pick_format_color(background=True)

    def sync_input_region(self) -> None:
        # Exclude the toolbar from the overlay's native window region. Even a
        # z-order change cannot let the overlay swallow clicks on its controls.
        region = QRegion(self.overlay.rect())
        if self.isVisible():
            hole = QRect(self.mapToGlobal(QPoint(0, 0)) - self.overlay.pos(), self.size())
            region = region.subtracted(QRegion(hole.adjusted(-3, -3, 3, 3)))
        self.overlay.setMask(region)
        if hasattr(self.overlay, 'fetcher'):
            self.overlay.fetcher.refresh()
        if self.overlay.text_editor:
            self.overlay.text_editor.position_bar()
        self.overlay.update()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self.fit_toolbar()

    def moveEvent(self, event) -> None:
        super().moveEvent(event)
        self.sync_input_region()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.sync_input_region()

    def button(self, text: str, callback, tip: str, icon_name: str | None = None,
               show_text: bool = False) -> QPushButton:
        names = {"−": "collapse", "×": "close", "More": "palette", "PNG": "save", "Copy PNG": "screenshot"}
        icon_name = icon_name or names.get(text, text.lower())
        button = QPushButton(text if show_text else "")
        button.setProperty('inkIcon', icon_name)
        button.setIcon(icon(icon_name))
        button.setIconSize(QSize(24, 24))
        button.setMinimumHeight(34)
        button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        button.setAccessibleName(text)
        button.setToolTip(tip)
        button.clicked.connect(callback)
        return button

    def toggle_tool(self, tool: str) -> None:
        if tool == self.overlay.tool and not self.overlay.click_through:
            self.overlay.set_click_through(True)
        else:
            self.choose_tool(tool)

    def choose_tool(self, tool: str) -> None:
        if self.overlay.click_through:
            self.overlay.set_click_through(False)
        self.overlay.set_tool(tool)
        if tool == "select":
            self.more_selection.setChecked(False)
            self.advanced_selection.hide()
            self.overlay.set_selection_mode("smart")
            self.fit_toolbar()

    def choose_selection_mode(self, mode: str) -> None:
        if mode != "smart":
            self.advanced_selection.show()
            self.more_selection.setChecked(True)
        if self.overlay.click_through:
            self.overlay.set_click_through(False)
        self.overlay.set_selection_mode(mode)

    def set_color(self, color: str) -> None:
        if self.overlay.tool == 'highlight':
            self.overlay.color = color
            self.overlay.highlighter_color = color
            self.overlay.changed.emit()
        else:
            self.overlay.apply_text_style(color=color)
        self.show_status(f"Color {color}")

    def pick_color(self) -> None:
        self.pick_format_color()

    def pick_format_color(self, background=False):
        editing = self.overlay.text_editor.result() if self.overlay.text_editor else None
        self.overlay.set_click_through(True)
        selected = next((i for i in sorted(self.overlay.selected)
                         if self.overlay.document.marks[i].kind == "text"), None)
        chosen = QColorDialog.getColor(QColor("#ffffff" if background else self.overlay.color), self,
                                       "Text background" if background else "Ink color")
        if chosen.isValid():
            if background:
                self.overlay.apply_text_style(background=chosen.name())
            else:
                self.set_color(chosen.name())
        if editing is not None:
            self.overlay.set_click_through(False)
            self.overlay.begin_text(QPointF(*editing.points[0]), selected)

    def set_width(self, width: int) -> None:
        self.overlay.width = width
        self.size_label.setText(f"{width} px")

    def set_opacity(self, value: int) -> None:
        self.opacity_label.setText(f"{value}%")
        if self.overlay.tool == "highlight":
            self.overlay.highlight_opacity = value / 100
        else:
            self.overlay.opacity = value / 100
            self.overlay.apply_text_style(opacity=value / 100)

    def toggle_click(self) -> None:
        self.overlay.set_click_through(not self.overlay.click_through)

    def toggle_annotations(self) -> None:
        self.overlay.annotations_visible = not self.overlay.annotations_visible
        self.overlay.update()
        self.refresh()

    def refresh(self) -> None:
        self.slider.blockSignals(True)
        self.slider.setRange(1,80 if self.overlay.tool=='highlight' else 20)
        self.slider.setValue(self.overlay.width)
        self.slider.blockSignals(False)
        self.size_label.setText(f'{self.overlay.width} px')
        highlighting = self.overlay.tool == "highlight"
        opacity = self.overlay.highlight_opacity if highlighting else self.overlay.opacity
        self.opacity_slider.blockSignals(True)
        self.opacity_slider.setValue(round(opacity * 100))
        self.opacity_slider.blockSignals(False)
        self.opacity_label.setText(f"{round(opacity * 100)}%")
        self.opacity_slider.setToolTip("Highlighter opacity (separate setting; translucent base)" if highlighting
                                       else "Shared opacity for pen, shapes and text")
        for tool, button in self.tool_buttons.items():
            button.setChecked(tool == self.overlay.tool and not self.overlay.click_through)
        self.active_tool_label.setText("TOOLS  ·  DESKTOP" if self.overlay.click_through else f"TOOLS  ·  {TOOL_LABELS[self.overlay.tool].upper()}")
        show_selection = self.overlay.tool == "select"
        panel_changed = self.selection_panel.isHidden() == show_selection
        self.selection_panel.setVisible(show_selection)
        self.multiple_button.setChecked(self.overlay.selection_operation == "add")
        for mode, button in self.selection_buttons.items():
            button.setChecked(mode == self.overlay.selection_mode)
        for operation, button in self.operation_buttons.items():
            button.setChecked(operation == self.overlay.selection_operation)
        self.selection_count.setText(f"{len(self.overlay.selected)} selected")
        self.selection_hint.setText(SELECT_HINTS[self.overlay.selection_mode])
        text_marks = [self.overlay.document.marks[i] for i in sorted(self.overlay.selected)
                      if i < len(self.overlay.document.marks) and self.overlay.document.marks[i].kind == "text"]
        target = self.overlay.text_editor.mark if self.overlay.text_editor else (text_marks[0] if text_marks else None)
        show_text = self.overlay.tool == "text" or target is not None
        panel_changed |= self.text_panel.isHidden() == show_text
        self.text_panel.setVisible(show_text)
        style = style_for(target) if target else self.overlay.text_defaults
        controls = [self.font_family, self.font_size, self.text_opacity, self.text_spacing]
        for control in controls:
            control.blockSignals(True)
        self.font_family.setCurrentFont(QFont(style.family))
        self.font_size.setValue(round(style.size))
        self.text_opacity.setValue(round(style.opacity*100))
        self.text_spacing.setValue(style.line_spacing)
        for control in controls:
            control.blockSignals(False)
        for key, button in self.text_style_buttons.items():
            button.setChecked(getattr(style, key))
        for align, button in self.align_buttons.items():
            button.setChecked(align == style.align)
        for label in ("Copy", "Duplicate", "Delete"):
            self.action_buttons[label].setEnabled(bool(self.overlay.selected))
        self.action_buttons["Paste"].setEnabled(bool(self.overlay.document.clipboard))
        self.mode_button.setText("Start drawing" if self.overlay.click_through
                                 else "Use desktop · Esc")
        self.mode_button.setProperty('inkIcon', 'pen' if self.overlay.click_through else 'desktop')
        self.visibility_button.setText("Show annotations" if not self.overlay.annotations_visible else "Hide annotations")
        self.visibility_button.setProperty('inkIcon', 'hidden' if not self.overlay.annotations_visible else 'eye')
        self.appearance.apply()
        if panel_changed:
            self.fit_toolbar()

    def show_status(self, message: str) -> None:
        self.status.setText(message)

    def toggle_compact(self) -> None:
        self.appearance.toggle()

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton and event.position().y() < 44*self.ui_scale:
            self.drag_origin = event.globalPosition().toPoint() - self.pos()

    def mouseMoveEvent(self, event) -> None:
        if self.drag_origin and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self.drag_origin)

    def mouseReleaseEvent(self, _event) -> None:
        self.drag_origin = None

    def keyPressEvent(self, event) -> None:
        self.overlay.keyPressEvent(event)

    def _register_hotkeys(self) -> None:
        self.hotkeys = {
            101: self.toggle_click, 102: self.overlay.undo, 103: self.overlay.clear,
            104: self.save_png, 105: self.overlay.redo,
        }
        self.filter = HotkeyFilter(self.hotkeys)
        QApplication.instance().installNativeEventFilter(self.filter)
        self.registered: list[int] = []
        if sys.platform == "win32":
            for hotkey_id, key, modifiers in ((101, ord("D"), 0x0001 | 0x0002),
                                               (102, ord("Z"), 0x0001 | 0x0002),
                                               (103, ord("X"), 0x0001 | 0x0002),
                                               (104, ord("S"), 0x0001 | 0x0002 | 0x0004),
                                               (105, ord("Y"), 0x0001 | 0x0002)):
                if ctypes.windll.user32.RegisterHotKey(int(self.winId()), hotkey_id, modifiers, key):
                    self.registered.append(hotkey_id)
                else:
                    self.show_status("Some Ctrl+Alt shortcuts are in use by another app")

    def capture(self) -> QImage:
        """Capture the desktop without app chrome, then paint annotations above it."""
        self.overlay.finish_text()
        geometry = virtual_geometry()
        scale = max(screen.devicePixelRatio() for screen in QGuiApplication.screens())
        image = QImage(int(geometry.width() * scale), int(geometry.height() * scale),
                       QImage.Format.Format_ARGB32)
        image.fill(Qt.GlobalColor.transparent)
        overlay_was_visible = self.overlay.isVisible()
        self.hide()
        self.overlay.hide()
        QApplication.processEvents()
        time.sleep(0.15)  # Let Desktop Window Manager reveal windows behind the overlay.
        painter = QPainter(image)
        for screen in QGuiApplication.screens():
            rect = screen.geometry()
            shot = screen.grabWindow(0)
            dest = QRectF((rect.x() - geometry.x()) * scale,
                          (rect.y() - geometry.y()) * scale,
                          rect.width() * scale, rect.height() * scale)
            painter.drawPixmap(dest, shot, QRectF(shot.rect()))
        painter.scale(scale, scale)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        for mark in self.overlay.document.marks:
            # Marks already use coordinates relative to the virtual overlay.
            draw_mark(painter, mark)
        painter.end()
        if overlay_was_visible:
            self.overlay.show()
        self.show()
        self.sync_input_region()
        self.overlay.set_click_through(True)
        return image

    def save_png(self) -> None:
        self.overlay.set_click_through(True)
        path, _ = QFileDialog.getSaveFileName(self, "Export annotated screenshot",
                                              str(Path.home() / "Pictures" / "SR Inqly.png"),
                                              "PNG image (*.png)")
        if path:
            if not path.lower().endswith(".png"):
                path += ".png"
            image = self.capture()
            if image.save(path, "PNG"):
                self.show_status(f"Saved {path}")
            else:
                QMessageBox.warning(self, "Export failed", f"Could not save {path}")

    def quick_screenshot(self) -> None:
        """Save to the Windows Pictures location without a destination dialog."""
        was_click_through = self.overlay.click_through
        try:
            pictures = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.PicturesLocation)
            if not pictures:
                raise OSError("Windows Pictures folder could not be located")
            folder = Path(pictures) / "SR Inqly Screenshots"
            folder.mkdir(parents=True, exist_ok=True)
            filename = f"SR Inqly {datetime.now():%Y-%m-%d %H-%M-%S-%f}-{uuid4().hex[:8]}.png"
            path = folder / filename
            if not self.capture().save(str(path), "PNG"):
                raise OSError(f"Could not save {path}")
            self.show_status(f"Saved {path}")
            self.appearance.quick_button.setToolTip(f"Saved: {path}")
        except OSError as error:
            self.show_status(f"Screenshot failed: {error}")
            self.appearance.quick_button.setToolTip(f"Screenshot failed: {error}")
        finally:
            self.overlay.set_click_through(was_click_through)

    def copy_png(self) -> None:
        QApplication.clipboard().setImage(self.capture())
        self.show_status("Annotated screenshot copied to clipboard")

    def close_app(self) -> None:
        if sys.platform == "win32":
            for hotkey_id in self.registered:
                ctypes.windll.user32.UnregisterHotKey(int(self.winId()), hotkey_id)
        self.overlay.close()
        self.close()
        QApplication.quit()

    def closeEvent(self, event) -> None:
        if getattr(self,'persist_settings',False):
            from preferences import save
            save(self)
        if sys.platform == "win32":
            for hotkey_id in self.registered:
                ctypes.windll.user32.UnregisterHotKey(int(self.winId()), hotkey_id)
            self.registered.clear()
        self.overlay.close()
        event.accept()
        # Both windows are Qt tool windows, so lastWindowClosed does not always
        # end the event loop. Also exit on Alt+F4 / WM_CLOSE, not only our button.
        QApplication.quit()


def main(splash=None) -> int:
    if '--performance-check' in sys.argv:
        from performance_diagnostics import run
        index = sys.argv.index('--performance-check')
        output = sys.argv[index+1]
        seconds = int(sys.argv[index+2]) if len(sys.argv)>index+2 else 120
        return run(draw_mark, Overlay, Toolbar, output, max(10,min(3600,seconds)))
    mutex = None
    if sys.platform == "win32":
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.CreateMutexW.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_wchar_p]
        kernel.CreateMutexW.restype = ctypes.c_void_p
        mutex = kernel.CreateMutexW(None, False, "Local\\SRInqlySingleInstance")
        if ctypes.get_last_error() == 183:
            if splash:splash.close()
            return 0

        def emergency_exit():
            # Runs independently of Qt, including while a modal dialog is open.
            from ctypes import wintypes
            user32 = ctypes.windll.user32
            if user32.RegisterHotKey(None, 1, 0x4000 | 0x0001 | 0x0002, ord('Q')):
                message = wintypes.MSG()
                while user32.GetMessageW(ctypes.byref(message), None, 0, 0) > 0:
                    if message.message == 0x0312:
                        os._exit(0)
                return
            # Preserve the emergency escape even if another program owns the hotkey.
            while True:
                if all(ctypes.windll.user32.GetAsyncKeyState(k) & 0x8000
                       for k in (0x11, 0x12, ord("Q"))):
                    os._exit(0)
                time.sleep(0.05)
        threading.Thread(target=emergency_exit, daemon=True).start()
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("SR Inqly")
    app.setQuitOnLastWindowClosed(True)
    document = Document()
    if splash:splash.progress(45,'Loading settings')
    overlay = Overlay(document)
    if splash:splash.progress(70,'Drawing tools and Fetcher ready')
    overlay.show()
    overlay.set_click_through(True)
    toolbar = Toolbar(overlay)
    from preferences import restore
    restore(toolbar)
    if splash:splash.progress(95,'Workspace ready')
    toolbar.show()
    toolbar.raise_()
    toolbar.show_status("Desktop mode · Ctrl+Alt+Q exits anytime")
    if splash:splash.finish()
    def fail_safe(exc_type, value, traceback):
        overlay.set_click_through(True)
        import logging
        folder = Path(QStandardPaths.writableLocation(QStandardPaths.AppLocalDataLocation))
        try:
            folder.mkdir(parents=True,exist_ok=True)
            logging.basicConfig(filename=str(folder/'errors.log'),level=logging.ERROR)
            logging.error('Unhandled UI error',exc_info=(exc_type,value,traceback))
        except OSError:
            pass
        sys.__excepthook__(exc_type, value, traceback)
        toolbar.show_status("Drawing paused after an error · Ctrl+Alt+Q exits")
    sys.excepthook = fail_safe
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
