"""Regression: external navigation releases desktop input; tool cursors recover."""
import ctypes
from unittest.mock import patch
from PySide6.QtCore import Qt, QPoint
from PySide6.QtWidgets import QApplication, QPushButton
from PySide6.QtTest import QTest
from document_model import Document
from application import Overlay, Toolbar, TOOLS

app = QApplication([])
overlay = Overlay(Document())
overlay.show()
toolbar = Toolbar(overlay)
toolbar.persist_settings = False
toolbar.show()
app.processEvents()

class Point(ctypes.Structure):
    _fields_ = [('x', ctypes.c_long), ('y', ctypes.c_long)]

user32 = ctypes.windll.user32
user32.WindowFromPoint.restype = ctypes.c_void_p
origin = Point(0, 0)
user32.ClientToScreen(ctypes.c_void_p(int(overlay.winId())), ctypes.byref(origin))
point = Point(origin.x + round(700 * overlay.devicePixelRatioF()),
              origin.y + round(500 * overlay.devicePixelRatioF()))
try:
    for tool in TOOLS:
        toolbar.choose_tool(tool)
        app.processEvents()
        assert not overlay.click_through
        if tool not in ('select', 'text'):
            assert not overlay.cursor().pixmap().isNull(), tool
        button = toolbar.developer_footer.findChild(QPushButton)
        def open_url(url):
            assert overlay.click_through, 'Release input before browser gets focus'
            assert user32.WindowFromPoint(point) != int(overlay.winId())
            return True
        with patch('branding_ui.QDesktopServices.openUrl', side_effect=open_url) as opened:
            QTest.mouseClick(button, Qt.LeftButton)
            assert opened.call_count == 1
        toolbar.choose_tool('pen')
        app.processEvents()
        assert user32.WindowFromPoint(point) == int(overlay.winId())
    for mode in ('smart', 'move', 'box', 'lasso', 'polygon'):
        toolbar.choose_selection_mode(mode)
        assert not overlay.click_through
        if mode not in ('smart', 'move'):
            assert not overlay.cursor().pixmap().isNull()
    QTest.keyClick(overlay, Qt.Key_Escape)
    assert overlay.click_through and overlay.cursor().shape() == Qt.ArrowCursor
    assert toolbar.cursor().shape() == Qt.ArrowCursor
    print('PASS: all tools, link input release, native desktop hit testing, re-entry, selection cursors and Escape')
finally:
    toolbar.close()
    overlay.close()
