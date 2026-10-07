import os
os.environ['QT_QPA_PLATFORM']='windows'
import ctypes
from PySide6.QtWidgets import QApplication,QWidget
from PySide6.QtGui import QPainter,QColor
from PySide6.QtCore import Qt,QRectF
from PySide6.QtTest import QTest
from application import Overlay,Toolbar
from document_model import Document
from image_capture import IMAGES
class Pattern(QWidget):
 def paintEvent(self,e):
  p=QPainter(self);p.fillRect(0,0,100,100,QColor('red'));p.fillRect(100,0,100,100,QColor('blue'))
app=QApplication([]);pattern=Pattern(None,Qt.FramelessWindowHint|Qt.WindowStaysOnTopHint);area=app.primaryScreen().availableGeometry();px=area.right()-239;py=min(350,area.bottom()-149);pattern.setGeometry(px,py,200,100);pattern.show();pattern.raise_()
assert QTest.qWaitForWindowExposed(pattern)
# Validate the actual desktop fixture before creating the annotation overlay.
# A normal window can be covered by another application or still awaiting DWM.
from image_capture import capture_region
from PySide6.QtCore import QPoint
for attempt in range(20):
 QTest.qWait(50)
 reference=capture_region(QRectF(px,py,200,100),QPoint())
 if reference.pixelColor(reference.width()//4,reference.height()//2)==QColor('red') and reference.pixelColor(reference.width()*3//4,reference.height()//2)==QColor('blue'):break
else:raise AssertionError('Desktop test pattern is not visible before app capture')
o=Overlay(Document());o.show();t=Toolbar(o);t.show();app.processEvents()
try:
 t.choose_tool('fetcher');o.fetcher.capture(QRectF(px-o.x(),py-o.y(),200,100));QTest.qWait(350)
 assert len(o.document.marks)==1
 im=IMAGES.images[o.document.marks[0].image_id]
 if im.pixelColor(im.width()//4,im.height()//2)!=QColor('red') or im.pixelColor(im.width()*3//4,im.height()//2)!=QColor('blue'):
  im.save('native-capture-diagnostic.png')
 assert im.pixelColor(im.width()//4,im.height()//2)==QColor('red')
 assert im.pixelColor(im.width()*3//4,im.height()//2)==QColor('blue')
 o.fetcher.copy();app.processEvents();assert ctypes.windll.user32.IsClipboardFormatAvailable(8) or ctypes.windll.user32.IsClipboardFormatAvailable(17)
 t.grab().save('sr-inqly-main-preview.png')
 print('PASS: native capture matches exact red/blue desktop region at current DPI; Windows image clipboard available',im.width(),im.height())
finally:t.close();pattern.close()
