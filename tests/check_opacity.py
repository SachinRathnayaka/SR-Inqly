import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
from PySide6.QtCore import QPoint,Qt
from document_model import Document
from application import Overlay,Toolbar
app=QApplication([]);o=Overlay(Document());o.show();t=Toolbar(o);t.show();app.processEvents()
try:
 t.choose_tool('pen');t.opacity_slider.setValue(72)
 for tool in ('line','rectangle','ellipse','arrow','pen'):
  t.choose_tool(tool);assert t.opacity_slider.value()==72
  QTest.mousePress(o,Qt.LeftButton,pos=QPoint(450,250))
  assert o.preview.opacity==.72
  QTest.mouseRelease(o,Qt.LeftButton,pos=QPoint(470,270))
 t.choose_tool('highlight');assert t.opacity_slider.value()==100
 t.opacity_slider.setValue(24)
 assert o.opacity==.72 and o.text_defaults.opacity==.72
 QTest.mousePress(o,Qt.LeftButton,pos=QPoint(500,300));assert o.preview.opacity==.24
 QTest.mouseRelease(o,Qt.LeftButton,pos=QPoint(520,320))
 t.choose_tool('text');assert t.opacity_slider.value()==72
 QTest.mouseClick(o,Qt.LeftButton,pos=QPoint(600,350));assert o.text_editor.mark.text_style.opacity==.72
 o.finish_text(False)
 t.choose_tool('pen');t.opacity_slider.setValue(89)
 t.choose_tool('highlight');assert t.opacity_slider.value()==24
 t.choose_tool('pen');assert t.opacity_slider.value()==89
 print('PASS: separate highlighter opacity, shared pen/shapes/text, stroke values and tool switching')
finally:
 t.close()
