"""Selection gestures and grouped edits through Qt mouse / keyboard events."""

import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPoint, QPointF, Qt, QRectF
from PySide6.QtGui import QPainterPath
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from document_model import Document, Mark
from selection_tools import indices_in_region
from application import Overlay, Toolbar


def click(widget, x, y):
    QTest.mouseClick(widget, Qt.MouseButton.LeftButton, pos=QPoint(x, y))


def run():
    app = QApplication([])
    doc = Document()
    doc.marks = [
        Mark("pen", [(100, 100), (140, 120)]),
        Mark("rectangle", [(180, 100), (220, 140)]),
        Mark("ellipse", [(330, 100), (380, 140)]),
        Mark("line", [(100, 250), (200, 350)]),
    ]
    overlay = Overlay(doc)
    overlay.show()
    toolbar = Toolbar(overlay)
    toolbar.show()
    try:
        toolbar.choose_selection_mode("box")
        overlay.set_selection_operation("add")
        app.processEvents()
        # Two separate clicks, with the mouse released between corners.
        click(overlay, 80, 80)
        assert not overlay.selected and overlay.selection_points
        QTest.mouseMove(overlay, QPoint(235, 160))
        click(overlay, 235, 160)
        assert overlay.selected == {0, 1}
        assert toolbar.selection_count.text() == "2 selected"
        assert toolbar.action_buttons["Copy"].isEnabled()

        # Add a disjoint region without holding Ctrl or the mouse button.
        click(overlay, 315, 80)
        click(overlay, 395, 155)
        assert overlay.selected == {0, 1, 2}
        overlay.set_selection_operation("subtract")
        click(overlay, 170, 85)
        click(overlay, 230, 150)
        assert overlay.selected == {0, 2}

        # Polygon accepts independent clicks; Enter closes it.
        overlay.set_selection_operation("replace")
        toolbar.choose_selection_mode("polygon")
        for x, y in [(75, 75), (150, 80), (165, 150), (80, 160)]:
            click(overlay, x, y)
        assert len(overlay.selection_points) == 4
        QTest.keyClick(overlay, Qt.Key_Return)
        assert overlay.selected == {0} and not overlay.selection_points

        # A second polygon closes by clicking its starting vertex.
        overlay.set_selection_operation("add")
        for x, y in [(310, 80), (400, 80), (400, 160), (310, 160), (310, 80)]:
            click(overlay, x, y)
        assert overlay.selected == {0, 2}
        # Double-click is another way to finish a polygon, without dragging.
        overlay.set_selection_operation("replace")
        for x, y in [(170, 85), (235, 85), (235, 155)]:
            click(overlay, x, y)
        QTest.mouseDClick(overlay, Qt.LeftButton, pos=QPoint(170, 155))
        assert overlay.selected == {1} and not overlay.selection_points
        overlay.selected = {0, 2}
        overlay.set_selection_operation("add")
        click(overlay, 450, 200)
        click(overlay, 500, 200)
        QTest.keyClick(overlay, Qt.Key_Backspace)
        assert len(overlay.selection_points) == 1
        QTest.mouseClick(overlay, Qt.RightButton, pos=QPoint(450, 200))
        assert not overlay.selection_points and overlay.selected == {0, 2}

        # Group movement changes every selected mark and creates one undo step.
        toolbar.choose_selection_mode("move")
        old_points = [list(mark.points) for mark in doc.marks]
        old_history = len(doc._undo)
        QTest.mousePress(overlay, Qt.LeftButton, pos=QPoint(120, 110))
        QTest.mouseMove(overlay, QPoint(150, 140))
        QTest.mouseRelease(overlay, Qt.LeftButton, pos=QPoint(150, 140))
        assert doc.marks[0].points[0] == (130, 130)
        assert doc.marks[2].points[0] == (360, 130)
        assert doc.marks[1].points == old_points[1]
        assert len(doc._undo) == old_history + 1
        overlay.undo()
        assert [mark.points for mark in doc.marks] == old_points
        overlay.redo()
        assert doc.marks[2].points[0] == (360, 130)
        overlay.undo()

        # Group copy/paste/duplicate/delete preserves ordering and undo units.
        overlay.selected = {0, 2}
        overlay.copy()
        assert toolbar.action_buttons["Paste"].isEnabled()
        overlay.paste()
        assert overlay.selected == {4, 5}
        assert doc.marks[4].points[0] == (124, 124)
        assert doc.marks[5].points[0] == (354, 124)
        overlay.delete_selected()
        assert len(doc.marks) == 4
        overlay.undo()
        assert len(doc.marks) == 6
        overlay.selected = {0, 2}
        overlay.duplicate()
        assert overlay.selected == {6, 7} and len(doc.marks) == 8
        overlay.undo()
        overlay.undo()
        overlay.undo()
        assert len(doc.marks) == 4

        # Drag rectangle and lasso, as well as single clicks, remain supported.
        overlay.set_selection_operation("replace")
        toolbar.choose_selection_mode("box")
        QTest.mousePress(overlay, Qt.LeftButton, pos=QPoint(75, 75))
        QTest.mouseMove(overlay, QPoint(235, 160))
        QTest.mouseRelease(overlay, Qt.LeftButton, pos=QPoint(235, 160))
        assert overlay.selected == {0, 1}
        toolbar.choose_selection_mode("lasso")
        QTest.mousePress(overlay, Qt.LeftButton, pos=QPoint(315, 80))
        for p in (QPoint(395, 80), QPoint(395, 160), QPoint(315, 160)):
            QTest.mouseMove(overlay, p)
        QTest.mouseRelease(overlay, Qt.LeftButton, pos=QPoint(315, 80))
        assert overlay.selected == {2}

        # Empty corners of a diagonal's bounding box must not count as ink.
        region = QPainterPath()
        region.addRect(QRectF(95, 335, 15, 15))
        assert indices_in_region(doc.marks, region) == set()
        region = QPainterPath()
        region.addRect(QRectF(140, 290, 20, 20))
        assert indices_in_region(doc.marks, region) == {3}

        # Keyboard shortcuts work with toolbar focus; safety Escape still wins.
        QTest.keyClick(toolbar, Qt.Key_A, Qt.ControlModifier)
        assert overlay.selected == {0, 1, 2, 3}
        QTest.keyClick(toolbar, Qt.Key_A, Qt.ControlModifier | Qt.ShiftModifier)
        assert not overlay.selected
        toolbar.choose_selection_mode("polygon")
        click(overlay, 400, 300)
        QTest.keyClick(toolbar, Qt.Key_Escape)
        assert overlay.click_through and not overlay.selection_points
        assert all(not button.icon().isNull() for button in
                   list(toolbar.tool_buttons.values()) + list(toolbar.selection_buttons.values()) +
                   list(toolbar.operation_buttons.values()) + list(toolbar.action_buttons.values()))
        print("PASS: area gestures, additive/subtractive selection, group editing, geometry, icons and Escape")
    finally:
        toolbar.close_app()


if __name__ == "__main__":
    run()
