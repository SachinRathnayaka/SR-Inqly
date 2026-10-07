import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QImage,QPainter,QColor
from PySide6.QtTest import QTest
from document_model import Document,Mark
from text_editor import text_font
from application import Overlay,Toolbar,draw_mark
app=QApplication([])
o=Overlay(Document());o.show();t=Toolbar(o);t.show();app.processEvents()
t.choose_tool('text');o.begin_text(QPointF(400,260));e=o.text_editor
o.activateWindow();e.input.setFocus();app.processEvents()
QTest.keyClicks(e.input,'Start typing here...')
QTest.mouseClick(e.buttons['larger'],Qt.LeftButton)
assert e.mark.text_style.size==22
QTest.mouseClick(e.buttons['wider'],Qt.LeftButton)
assert text_font(e.mark.text_style).letterSpacing()==0.5
QTest.mouseClick(e.buttons['color'],Qt.LeftButton);assert e.palette_panel.isVisible()
e.choose_color('#0078d4');assert e.mark.color=='#0078d4'
assert e.input.hasFocus()
t.opacity_slider.setValue(35);assert o.opacity==0.35 and e.mark.text_style.opacity==0.35
app.processEvents()
img=QImage(800,450,QImage.Format_ARGB32);img.fill(QColor('white'));p=QPainter(img)
e.bar.render(p,e.bar.pos());e.render(p,e.pos());p.end();img.save('inline-text-1.4-preview.png')
bar=e.bar;o.finish_text();assert not bar.isVisible()
assert o.document.marks[0].text_style.letter_spacing==0.5
o.begin_text(index=0);QTest.mouseClick(o.text_editor.buttons['delete'],Qt.LeftButton)
assert not o.document.marks;o.document.undo();assert len(o.document.marks)==1
o.begin_text(QPointF(400,250));QTest.mouseClick(o.text_editor.buttons['delete'],Qt.LeftButton);assert len(o.document.marks)==1
for opacity,expected in [(1.0,255),(0.35,89)]:
 image=QImage(50,50,QImage.Format_ARGB32);image.fill(Qt.transparent);p=QPainter(image)
 draw_mark(p,Mark('line',[(5,25),(45,25)],'#ff0000',10,opacity=opacity));p.end()
 assert abs(image.pixelColor(25,25).alpha()-expected)<=1
t.close()
print('PASS: context controls, focus, spacing, delete/undo, bar cleanup and opacity pixel rendering')


