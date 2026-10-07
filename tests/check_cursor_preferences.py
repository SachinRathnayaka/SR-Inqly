"""Cursor dialog acceptance, cancellation, defaults and preference validation."""
from pathlib import Path
from unittest.mock import patch
from PySide6.QtCore import QSettings, QTimer, Qt
from PySide6.QtTest import QTest
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QApplication, QDialog, QDialogButtonBox, QPushButton, QSpinBox
from document_model import Document
from icons import crosshair_cursor
from application import Overlay, Toolbar

app = QApplication([])
o = Overlay(Document())
t = Toolbar(o)
t.persist_settings = False
o.show()
t.show()
app.processEvents()
a = t.appearance
settings_path = Path('build/cursor-test.ini').resolve()
a.settings = QSettings(str(settings_path), QSettings.IniFormat)
a.settings.clear()
errors = []

def inspect(accept, reset=False):
    dialog = app.activeModalWidget()
    try:
        assert isinstance(dialog, QDialog)
        assert o.click_through
        for name in ('cursorWidth', 'cursorSize'):
            spin = dialog.findChild(QSpinBox, name)
            spin.setValue(spin.minimum() + 1)
            for suffix, expected in (('Increase', spin.minimum() + 2), ('Decrease', spin.minimum() + 1)):
                button = dialog.findChild(QPushButton, name + suffix)
                center = button.rect().center()
                assert QApplication.widgetAt(button.mapToGlobal(center)) is button
                QTest.mouseMove(button, center)
                assert button.cursor().shape() == Qt.ArrowCursor
                QTest.mouseClick(button, Qt.LeftButton, pos=center)
                assert spin.value() == expected
                assert dialog.isVisible()
            spin.setValue(spin.maximum())
            QTest.mouseClick(dialog.findChild(QPushButton, name + 'Increase'), Qt.LeftButton)
            assert spin.value() == spin.maximum()
        dialog.findChild(QSpinBox, 'cursorWidth').setValue(5)
        dialog.findChild(QSpinBox, 'cursorSize').setValue(32)
        with patch('appearance.QColorDialog.getColor', return_value=QColor('#ff00aa')):
            dialog.findChild(QPushButton, 'cursorColor').click()
        if reset:
            dialog.findChild(QDialogButtonBox).button(QDialogButtonBox.RestoreDefaults).click()
        dialog.grab().save('cursor-settings-preview.png')
    except Exception as error:
        errors.append(error)
    finally:
        dialog.accept() if accept else dialog.reject()

try:
    t.choose_tool('pen')
    QTimer.singleShot(100, lambda: inspect(True))
    a.custom_cursor()
    assert not errors, errors
    assert not o.click_through
    assert (o.cursor_color, o.cursor_width, o.cursor_size) == ('#ff00aa', 5, 32)
    expected = o.cursor().pixmap().toImage()
    for tool in ('pen', 'highlight', 'eraser', 'line', 'rectangle', 'ellipse', 'arrow', 'fetcher'):
        t.choose_tool(tool)
        assert o.cursor().pixmap().toImage() == expected, 'Tool badge must not return'
    a.settings.sync()
    a.settings = QSettings(str(settings_path), QSettings.IniFormat)
    o.cursor_color = '#000000'
    a.restore_cursor()
    assert o.cursor_color == '#ff00aa' and o.cursor_width == 5 and o.cursor_size == 32
    o.set_click_through(True)
    QTimer.singleShot(100, lambda: inspect(False, True))
    a.custom_cursor()
    assert not errors, errors
    assert o.click_through and o.cursor_color == '#ff00aa' and o.cursor_width == 5
    t.choose_tool('pen')
    QTimer.singleShot(100, lambda: inspect(True, True))
    a.custom_cursor()
    assert not errors, errors
    assert (o.cursor_color, o.cursor_width, o.cursor_size) == ('#172033', 2, 20)
    a.settings.setValue('cursor_width', 'corrupt')
    a.settings.setValue('cursor_size', 500)
    a.settings.setValue('cursor_color', 'invalid')
    a.restore_cursor()
    assert (o.cursor_color, o.cursor_width, o.cursor_size) == ('#172033', 2, 40)
    cursor = crosshair_cursor('#ff00aa', 5, 32)
    assert cursor.hotSpot().x() == cursor.pixmap().width() // 2
    assert cursor.pixmap().toImage().pixelColor(cursor.hotSpot()).name() == '#ff00aa'
    print('PASS: cursor preview, color/thickness/size, save/reload, cancel, defaults, invalid settings, centered hotspot and no tool badges')
finally:
    t.close()
    o.close()
    a.settings.clear()
    a.settings.sync()
    settings_path.unlink(missing_ok=True)
