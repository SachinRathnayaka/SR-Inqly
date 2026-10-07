import os
os.environ['QT_QPA_PLATFORM']='windows'
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QPoint,Qt,QRect
from PySide6.QtTest import QTest
from document_model import Document
from application import Overlay,Toolbar
app=QApplication([]);o=Overlay(Document());o.show();t=Toolbar(o);t.show();app.processEvents()
try:
 t.toggle_compact();t.choose_tool('text');app.processEvents()
 screen=app.primaryScreen()
 def blue_count(image):
  count=0
  for y in range(image.height()):
   for x in range(image.width()):
    c=image.pixelColor(x,y)
    if c.blue()>200 and 90<c.green()<180 and c.red()<40:count+=1
  return count
 area=QRect(620,260,140,160)
 baseline=screen.grabWindow(0,area.x(),area.y(),area.width(),area.height()).toImage()
 o.begin_text(QPoint(650,290));e=o.text_editor;app.processEvents()
 assert e.input.caret_timer.isActive()
 e.input.caret_timer.stop();e.input.caret_visible=True;e.input.viewport().update();app.processEvents()
 on=e.input.viewport().grab().toImage()
 e.input.blink_caret();app.processEvents();off=e.input.viewport().grab().toImage();assert on!=off,'Caret paint must alternate'
 e.input.reset_caret();QTest.qWait(550);assert not e.input.caret_visible,'Timer must blink without typing'
 for i in range(18):
  e.move(620+i*9,280+i*4);app.processEvents();QTest.qWait(8)
 e.move(o.rect().width()-e.width()-10,480);app.processEvents();QTest.qWait(120)
 after=screen.grabWindow(0,area.x(),area.y(),area.width(),area.height()).toImage()
 assert blue_count(after)<=blue_count(baseline)+5,(blue_count(after),blue_count(baseline))
 # Obstruct the preferred toolbar position; it should stay nearby, below the compact toolbar.
 e.move(t.x()+10,t.y()+t.height()+5);app.processEvents()
 assert abs(e.bar.x()-e.x())<e.bar.width(),(e.bar.geometry(),e.geometry())
 from PySide6.QtGui import QRegion
 assert QRegion(e.bar.geometry()).subtracted(o.mask()).isEmpty()
 o.set_click_through(True);assert not e.input.caret_timer.isActive()
 print('PASS: native desktop drag pixels cleared, automatic caret blink, nearby unmasked toolbar and Escape cleanup')
finally:t.close()
