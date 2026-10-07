"""Inline text, simple selection, styling, and toolbar scaling regression checks."""

import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from copy import deepcopy

from PySide6.QtCore import QPoint, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from document_model import Document, Mark
from text_editor import text_bounds, text_document
from application import Overlay, Toolbar


def run():
    app = QApplication([])
    doc = Document()
    overlay = Overlay(doc)
    overlay.show()
    toolbar = Toolbar(overlay)
    toolbar.show()
    app.processEvents()
    try:
        toolbar.choose_tool("text")
        QTest.mouseClick(overlay, Qt.LeftButton, pos=QPoint(450, 250))
        app.processEvents()
        editor = overlay.text_editor
        assert editor is not None and not editor.isWindow()
        assert editor.input.cursorWidth() == 0
        QTest.keyClicks(editor.input, "Screen note")
        toolbar.font_size.setValue(32)
        QTest.mouseClick(toolbar.text_style_buttons["bold"], Qt.LeftButton)
        toolbar.set_color("#57dd9b")
        overlay.apply_text_style(align="center", background="#112233", line_spacing=140)
        assert editor.mark.text_style.bold and editor.mark.text_style.size == 32
        assert not doc.marks, "Live edit should be a single undo transaction"
        editor.move(editor.pos() + QPoint(30, 40))
        editor.resize(360, 160)
        app.processEvents()
        QTest.keyClick(editor.input, Qt.Key_Return, Qt.ControlModifier)
        assert overlay.text_editor is None and len(doc.marks) == 1
        mark = doc.marks[0]
        assert mark.text == "Screen note" and mark.color == "#57dd9b"
        assert mark.text_style.bold and mark.text_style.align == "center"
        assert mark.text_style.background == "#112233"
        assert mark.text_box[0] > 300 and mark.points[0][0] >= 470
        assert text_bounds(mark).height() >= text_document(mark).size().height()
        overlay.undo()
        assert not doc.marks
        overlay.redo()
        assert len(doc.marks) == 1

        # Simple select/move needs no separate move mode.
        toolbar.choose_tool("select")
        assert overlay.selection_mode == "smart" and toolbar.advanced_selection.isHidden()
        point = QPoint(round(doc.marks[0].points[0][0])+10, round(doc.marks[0].points[0][1])+10)
        before = deepcopy(doc.marks[0])
        QTest.mousePress(overlay, Qt.LeftButton, pos=point)
        QTest.mouseMove(overlay, point+QPoint(35, 20))
        QTest.mouseRelease(overlay, Qt.LeftButton, pos=point+QPoint(35, 20))
        assert doc.marks[0].points[0] == (before.points[0][0]+35, before.points[0][1]+20)
        toolbar.font_size.setValue(26)
        assert doc.marks[0].text_style.size == 26
        overlay.undo()
        assert doc.marks[0].text_style.size == 32

        # Double-click edits the existing object; cancelling keeps it intact.
        before = deepcopy(doc.marks[0])
        point = QPoint(round(before.points[0][0])+10, round(before.points[0][1])+10)
        QTest.mouseDClick(overlay, Qt.LeftButton, pos=point)
        assert overlay.text_editor and overlay.text_editor.index == 0
        overlay.text_editor.input.setPlainText("Changed")
        overlay.finish_text(False)
        assert doc.marks[0] == before
        overlay.begin_text(index=0)
        overlay.text_editor.input.setPlainText("Edited note\nSecond line")
        QTest.keyClick(overlay.text_editor.input, Qt.Key_Escape)
        assert overlay.click_through and overlay.text_editor is None
        assert doc.marks[0].text == "Edited note\nSecond line"
        assert doc.marks[0].text_style.opacity == 1

        # Tool and icon sizes scale together; the toolbar stays on-screen.
        for percent in (75, 150, 100):
            toolbar.scale_slider.setValue(percent)
            app.processEvents()
            assert toolbar.width() == round(320*percent/100)
            assert toolbar.tool_buttons["pen"].iconSize().width() == round(24*percent/100)
            assert toolbar.tool_buttons["pen"].height() == round(42*percent/100)
            assert toolbar.height() <= app.primaryScreen().availableGeometry().height()
            for button in toolbar.tool_buttons.values():
                assert not overlay.mask().contains(button.mapToGlobal(button.rect().center())-overlay.pos()), (percent, button.accessibleName(), button.mapToGlobal(button.rect().center()), toolbar.geometry())

        # Empty-space drag selects a group in the default mode.
        overlay.finish_text()
        doc.marks = [Mark("pen", [(100, 100), (120, 120)]), Mark("pen", [(150, 100), (170, 120)])]
        overlay.deselect()
        toolbar.choose_tool("select")
        QTest.mousePress(overlay, Qt.LeftButton, pos=QPoint(80, 80))
        QTest.mouseMove(overlay, QPoint(190, 150))
        QTest.mouseRelease(overlay, Qt.LeftButton, pos=QPoint(190, 150))
        assert overlay.selected == {0, 1}
        QTest.mousePress(overlay, Qt.LeftButton, pos=QPoint(110, 110))
        QTest.mouseMove(overlay, QPoint(120, 130))
        QTest.mouseRelease(overlay, Qt.LeftButton, pos=QPoint(120, 130))
        assert doc.marks[0].points[0] == (110, 120) and doc.marks[1].points[0] == (160, 120)
        print("PASS: inline text, edit/cancel/undo, text formatting, smart group move, UI scaling and Escape")
    finally:
        toolbar.close_app()


if __name__ == "__main__":
    run()
