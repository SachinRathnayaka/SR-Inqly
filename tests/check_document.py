"""Small functional checks for the document and Qt renderer."""

import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPainter
from PySide6.QtWidgets import QApplication

from document_model import Document, Mark
from application import draw_mark


def run() -> None:
    doc = Document()
    doc.checkpoint()
    doc.marks.append(Mark("pen", [(10, 10), (80, 80)], "#ff4655", 5))
    assert doc.hit(42, 42) == 0
    assert doc.hit(80, 10) is None
    assert doc.copy(0)
    pasted = doc.paste()
    assert pasted == 1 and doc.marks[pasted].points[0] == (34, 34)
    assert doc.undo() and len(doc.marks) == 1
    assert doc.redo() and len(doc.marks) == 2
    doc.delete(1)
    assert len(doc.marks) == 1
    doc.clear()
    assert not doc.marks
    assert doc.undo() and len(doc.marks) == 1

    app = QApplication([])
    image = QImage(200, 200, QImage.Format.Format_ARGB32)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    for kind in ("pen", "highlight", "line", "rectangle", "ellipse", "arrow", "text"):
        draw_mark(painter, Mark(kind, [(20, 20), (100, 100)], "#ff4655", 4, "Note"))
    painter.end()
    assert QColor_alpha(image.pixelColor(20, 20)) > 0
    app.quit()
    print("Document editing and Qt rendering checks passed")


def QColor_alpha(color) -> int:
    return color.alpha()


if __name__ == "__main__":
    run()
