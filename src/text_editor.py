"""Inline text editing and a shared document layout for display and export."""

from copy import deepcopy

from PySide6.QtCore import QPoint, QPointF, QRect, QRectF, QSize, Qt, Signal, QTimer
from PySide6.QtGui import QColor, QFont, QPainter, QRegion, QTextBlockFormat, QTextCharFormat, QTextCursor, QTextDocument
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QTextEdit, QVBoxLayout, QWidget

from icons import icon
from document_model import Mark, TextStyle


def style_for(mark: Mark) -> TextStyle:
    return deepcopy(mark.text_style or TextStyle(size=max(10, mark.width * 5)))


def text_font(style: TextStyle) -> QFont:
    font = QFont(style.family)
    font.setPointSizeF(style.size)
    font.setBold(style.bold)
    font.setItalic(style.italic)
    font.setUnderline(style.underline)
    font.setStrikeOut(style.strike)
    font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, style.letter_spacing)
    return font


def format_document(document: QTextDocument, mark: Mark) -> None:
    style = style_for(mark)
    font = text_font(style)
    document.setDefaultFont(font)
    char = QTextCharFormat()
    char.setFont(font)
    char.setForeground(QColor(mark.color))
    cursor = QTextCursor(document)
    cursor.select(QTextCursor.SelectionType.Document)
    cursor.setCharFormat(char)
    block = QTextBlockFormat()
    block.setAlignment({"left": Qt.AlignmentFlag.AlignLeft, "center": Qt.AlignmentFlag.AlignHCenter,
                        "right": Qt.AlignmentFlag.AlignRight}[style.align])
    block.setLineHeight(style.line_spacing, QTextBlockFormat.LineHeightTypes.ProportionalHeight.value)
    cursor.setBlockFormat(block)


def text_document(mark: Mark) -> QTextDocument:
    document = QTextDocument()
    document.setDocumentMargin(0)
    document.setPlainText(mark.text)
    format_document(document, mark)
    document.setTextWidth(mark.text_box[0] if mark.text_box else 400)
    return document


def text_bounds(mark: Mark) -> QRectF:
    document = text_document(mark)
    x, y = mark.points[0]
    width = mark.text_box[0] if mark.text_box else document.idealWidth()
    height = max(mark.text_box[1] if mark.text_box else 0, document.size().height())
    return QRectF(x, y, width, height)


def draw_text(painter: QPainter, mark: Mark) -> None:
    document = text_document(mark)
    bounds = text_bounds(mark)
    painter.save()
    painter.setOpacity(style_for(mark).opacity)
    if style_for(mark).background:
        painter.fillRect(bounds, QColor(style_for(mark).background))
    painter.translate(bounds.topLeft())
    document.drawContents(painter, QRectF(0, 0, bounds.width(), bounds.height()))
    painter.restore()


class TextInput(QTextEdit):
    done = Signal()
    desktop = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        # Draw our own opaque caret, including on an empty placeholder. Its
        # visibility is independent of the selected ink color and opacity.
        self.setCursorWidth(0)
        self.caret_visible = True
        self.caret_timer = QTimer(self)
        self.caret_timer.setInterval(500)
        self.caret_timer.timeout.connect(self.blink_caret)
        self.cursorPositionChanged.connect(self.reset_caret)
        self.textChanged.connect(self.reset_caret)

    def reset_caret(self):
        self.caret_visible = True
        if self.isVisible():
            self.caret_timer.start()
        self.viewport().update()

    def blink_caret(self):
        self.caret_visible = not self.caret_visible
        self.viewport().update()

    def showEvent(self, event):
        super().showEvent(event)
        self.reset_caret()

    def hideEvent(self, event):
        self.caret_timer.stop()
        super().hideEvent(event)

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.caret_visible and not self.textCursor().hasSelection():
            painter = QPainter(self.viewport())
            rect = self.cursorRect()
            rect.setWidth(2)
            painter.fillRect(rect.adjusted(-1,0,1,0), QColor('#ffffff'))
            painter.fillRect(rect, QColor('#111111'))

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.desktop.emit()
        elif event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self.done.emit()
        else:
            super().keyPressEvent(event)


class DragHandle(QLabel):
    def __init__(self, editor, resize=False):
        super().__init__(editor)
        self.editor, self.resizing, self.start = editor, resize, None
        self.setCursor(Qt.CursorShape.SizeHorCursor if resize else Qt.CursorShape.SizeAllCursor)
        self.setText("" if resize else "⠿")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setToolTip("Drag to resize text width" if resize else "Drag to move text")
        self.setStyleSheet("background:white; border:3px solid #0085ed; border-radius:7px;" if resize
                          else "background:#0085ed; color:white; border:none; font:18px 'Segoe UI';")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.start, self.initial = event.globalPosition().toPoint(), self.editor.geometry()

    def mouseMoveEvent(self, event):
        if self.start is not None and event.buttons() & Qt.MouseButton.LeftButton:
            delta = event.globalPosition().toPoint() - self.start
            parent = self.editor.parentWidget()
            if self.resizing:
                self.editor.resize(max(100, min(parent.rect().width()-self.editor.x(), self.initial.width()+delta.x())), self.editor.height())
            else:
                target = self.initial.topLeft()+delta
                self.editor.move(max(0,min(target.x(),parent.rect().width()-self.editor.width())),
                                 max(0,min(target.y(),parent.height()-self.editor.height())))

    def mouseReleaseEvent(self, event):
        self.start = None


class InlineTextEditor(QWidget):
    accepted = Signal()
    cancelled = Signal()
    desktopRequested = Signal()
    styleChanged = Signal(dict)
    deleteRequested = Signal()

    def __init__(self, parent, mark: Mark, index: int | None):
        super().__init__(parent)
        self.mark, self.index = deepcopy(mark), index
        self.mark.text_style = style_for(mark)
        self.setObjectName("inlineText")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet("QWidget#inlineText {background:transparent; border:none;}")
        self.input = TextInput(self)
        self.input.setAcceptRichText(False)
        self.input.setCursorWidth(0)
        self.input.setFont(text_font(self.mark.text_style))
        self.input.setPlaceholderText("Start typing here…")
        self.input.document().setDocumentMargin(0)
        self.input.setPlainText(mark.text)
        self.input.done.connect(self.accepted)
        self.input.desktop.connect(self.desktopRequested)
        self.handle = DragHandle(self)
        self.grip = DragHandle(self, True)
        # A sibling child remains inside the overlay's native input/safety boundary.
        self.bar = QWidget(parent)
        self.bar.setObjectName("textContext")
        self.bar.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.bar.setStyleSheet("""
          QWidget#textContext {background:white; border:1px solid #dedede; border-radius:7px;}
          QPushButton {background:transparent; color:#303030; border:none; border-radius:4px; font:20px 'Segoe UI';}
          QPushButton:hover {background:#eaf3fc;}
          QPushButton:pressed {background:#d1e7fb;}
        """)
        row = QHBoxLayout(self.bar)
        row.setContentsMargins(8,6,8,6)
        row.setSpacing(3)
        self.buttons = {}
        for key, label, tip, callback in (
            ("color", "A ▾", "Text color", self.toggle_palette),
            ("larger", "A⌃", "Increase font size", lambda:self.adjust("size",2,6,200)),
            ("smaller", "A⌄", "Decrease font size", lambda:self.adjust("size",-2,6,200)),
            ("wider", "AV↔", "Increase character spacing", lambda:self.adjust("letter_spacing",0.5,-2,20)),
            ("narrower", "AV↤", "Decrease character spacing", lambda:self.adjust("letter_spacing",-0.5,-2,20)),
            ("delete", "", "Delete text", self.deleteRequested.emit)):
            button = QPushButton(label, self.bar)
            button.setFixedSize(49,44)
            button.setToolTip(tip)
            button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            if key == "delete":
                button.setIcon(icon("delete", "#303030"))
                button.setIconSize(QSize(25,25))
            button.clicked.connect(callback)
            row.addWidget(button)
            self.buttons[key] = button
        self.bar.adjustSize()
        self.palette_panel = QWidget(self.bar)
        self.palette_panel.hide()
        colors = QHBoxLayout(self.palette_panel)
        colors.setContentsMargins(4,4,4,4)
        for color in ("#202020", "#0078d4", "#e53935", "#26853c", "#ff9800", "#8e44ad", "#ffffff"):
            button = QPushButton(self.palette_panel)
            button.setFixedSize(30,26)
            button.setToolTip(color)
            button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            button.setStyleSheet(f"background:{color}; border:1px solid #999; border-radius:3px;")
            button.clicked.connect(lambda _=False,c=color:self.choose_color(c))
            colors.addWidget(button)
        row.addWidget(self.palette_panel)
        self.setMinimumSize(100,42)
        w,h = mark.text_box or (280,40)
        self.resize(round(w+30),max(48,round(h+12)))
        self.layout_children()
        origin = self.input.viewport().mapTo(self,QPoint(0,0))
        self.move(max(0,round(mark.points[0][0])-origin.x()),max(0,round(mark.points[0][1])-origin.y()))
        self.apply_style()
        self.input.document().documentLayout().documentSizeChanged.connect(self.grow_to_content)
        self.destroyed.connect(self.bar.deleteLater)

    def adjust(self,key,delta,minimum,maximum):
        self.styleChanged.emit({key:max(minimum,min(maximum,getattr(self.mark.text_style,key)+delta))})

    def toggle_palette(self):
        self.palette_panel.setVisible(not self.palette_panel.isVisible())
        self.bar.adjustSize()
        self.position_bar()

    def choose_color(self,color):
        self.styleChanged.emit({"color":color})
        self.palette_panel.hide()
        self.bar.adjustSize()
        self.position_bar()

    def layout_children(self):
        self.input.setGeometry(22,5,max(40,self.width()-32),max(26,self.height()-10))
        self.handle.setGeometry(0,0,18,self.height())
        self.grip.setGeometry(self.width()-14,(self.height()-14)//2,14,14)
        self.grip.raise_()

    def position_bar(self):
        if not hasattr(self,"bar"):
            return
        parent = self.parentWidget()
        x = max(0,min(self.x(),parent.rect().width()-self.bar.width()))
        y = self.y()-self.bar.height()-10
        if y < 0:
            y = min(parent.height()-self.bar.height(),self.y()+self.height()+10)
        # Search nearby positions, preferring directly above/below the text,
        # rather than jumping to the far edge of the desktop when obstructed.
        mask = parent.mask()
        if not mask.isEmpty():
            xs = [x]
            ys = [max(0,y), self.y()+self.height()+10]
            for child in parent.findChildren(QWidget, options=Qt.FindChildOption.FindDirectChildrenOnly):
                if child.isWindow() and child.isVisible():
                    obstacle = QRect(child.mapToGlobal(QPoint(0,0))-parent.pos(),child.size())
                    xs.extend((obstacle.right()+8,obstacle.left()-self.bar.width()-8))
                    ys.extend((obstacle.bottom()+8,obstacle.top()-self.bar.height()-8))
            candidates = []
            for candidate_y in ys:
                for candidate_x in xs:
                    rect = QRect(max(0,candidate_x),max(0,candidate_y),self.bar.width(),self.bar.height())
                    if parent.rect().contains(rect) and QRegion(rect).subtracted(mask).isEmpty():
                        candidates.append(rect)
            if candidates:
                rect = min(candidates,key=lambda r:abs(r.x()-self.x())+abs(r.y()-y))
                x,y = rect.x(),rect.y()
        self.bar.move(x,max(0,y))
        self.bar.raise_()
        parent.update()

    def resizeEvent(self,event):
        super().resizeEvent(event)
        if hasattr(self,"input"):
            self.layout_children()
            self.position_bar()

    def moveEvent(self,event):
        super().moveEvent(event)
        self.position_bar()

    def showEvent(self,event):
        super().showEvent(event)
        self.bar.show()
        self.position_bar()

    def hideEvent(self,event):
        self.bar.hide()
        super().hideEvent(event)

    def paintEvent(self,event):
        painter = QPainter(self)
        from PySide6.QtGui import QPen
        painter.setPen(QPen(QColor("#0085ed"),2,Qt.PenStyle.DashLine))
        painter.drawRect(18,1,self.width()-26,self.height()-3)

    def grow_to_content(self,size):
        target = min(max(42,self.parentWidget().height()-self.y()),max(48,round(size.height())+12))
        if target > self.height()+2:
            self.resize(self.width(),target)

    def apply_style(self):
        cursor = self.input.textCursor()
        format_document(self.input.document(),self.mark)
        self.input.setFont(text_font(self.mark.text_style))
        self.input.setTextCursor(cursor)
        background = self.mark.text_style.background or "transparent"
        self.input.setStyleSheet(f"background:{background}; color:{self.mark.color}; border:none; padding:0;")
        self.buttons["color"].setStyleSheet(f"border-bottom:4px solid {self.mark.color}; color:#303030;")
        self.buttons["larger"].setToolTip(f"Increase font size ({self.mark.text_style.size:g} pt)")

    def result(self) -> Mark:
        mark = deepcopy(self.mark)
        mark.text = self.input.toPlainText()
        origin = self.input.viewport().mapTo(self.parentWidget(),QPoint(0,0))
        mark.points = [(float(origin.x()),float(origin.y()))]
        width = max(40,self.input.viewport().width())
        mark.text_box = (float(width),0)
        mark.text_box = (float(width),max(24.0,text_document(mark).size().height()))
        return mark
