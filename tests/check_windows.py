"""Check that the real Windows hit test reaches the overlay in drawing mode."""

import ctypes

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QPoint, Qt
from PySide6.QtTest import QTest

from document_model import Document
from application import Overlay, Toolbar


class Point(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


def run() -> None:
    app = QApplication([])
    overlay = Overlay(Document())
    overlay.show()
    toolbar = Toolbar(overlay)
    toolbar.show()
    app.processEvents()
    user32 = ctypes.windll.user32
    point = Point(700, 500)
    overlay_handle = int(overlay.winId())
    assert user32.WindowFromPoint(point) == overlay_handle, "Drawing mode cannot receive mouse input"
    overlay.set_click_through(True)
    app.processEvents()
    assert user32.WindowFromPoint(point) != overlay_handle, "Click-through failed"
    overlay.set_click_through(False)
    app.processEvents()
    assert user32.WindowFromPoint(point) == overlay_handle, "Drawing mode was not restored"
    for iteration in range(8):
        toolbar.choose_tool("pen")
        overlay.raise_()
        overlay.activateWindow()
        app.processEvents()
        QTest.mousePress(overlay, Qt.LeftButton, pos=QPoint(800, 600))
        QTest.mouseMove(overlay, QPoint(850, 650))
        QTest.mouseRelease(overlay, Qt.LeftButton, pos=QPoint(850, 650))
        assert len(overlay.document.marks) == iteration + 1
        for button in toolbar.tool_buttons.values():
            global_point = button.mapToGlobal(button.rect().center())
            local_point = global_point - overlay.pos()
            assert not overlay.mask().contains(local_point), "Toolbar covered by input overlay"
        QTest.mouseClick(toolbar.tool_buttons["rectangle"], Qt.LeftButton)
        assert overlay.tool == "rectangle"
        QTest.keyClick(overlay, Qt.Key_Escape)
        assert overlay.click_through
        toolbar.move(toolbar.pos() + QPoint(5, 3))
        app.processEvents()
    # Expanded selection panel and compact mode must retain native reachability.
    toolbar.choose_selection_mode("polygon")
    app.processEvents()
    for x, y in ((700, 500), (950, 500), (950, 750), (700, 750)):
        QTest.mouseClick(overlay, Qt.LeftButton, pos=QPoint(x, y))
    QTest.keyClick(overlay, Qt.Key_Return)
    assert len(overlay.selected) == 8
    for mode_button in toolbar.selection_buttons.values():
        overlay.raise_()
        overlay.activateWindow()
        app.processEvents()
        point_in_toolbar = mode_button.mapTo(toolbar, mode_button.rect().center())
        origin = Point(0, 0)
        user32.ClientToScreen(int(toolbar.winId()), ctypes.byref(origin))
        ratio = toolbar.devicePixelRatioF()
        native_point = Point(origin.x + round(point_in_toolbar.x() * ratio),
                             origin.y + round(point_in_toolbar.y() * ratio))
        assert user32.WindowFromPoint(native_point) == int(toolbar.winId()), "Selection toolbar blocked"
        QTest.mouseClick(mode_button, Qt.LeftButton)
    toolbar.toggle_compact()
    app.processEvents()
    toolbar.toggle_compact()
    app.processEvents()
    for button in toolbar.selection_buttons.values():
        assert not overlay.mask().contains(button.mapToGlobal(button.rect().center()) - overlay.pos())
    QTest.keyClick(toolbar, Qt.Key_Escape)
    assert overlay.click_through
    toolbar.close_app()
    print("Windows hit test, 8 draw/tool-switch cycles, area selection, expanded toolbar and Escape passed")


if __name__ == "__main__":
    run()
