import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from copy import deepcopy
from unittest.mock import patch
from PySide6.QtWidgets import QApplication,QDialog
from PySide6.QtCore import Qt,QPoint,QPointF,QRectF,QTimer,QEvent
from PySide6.QtGui import QImage,QColor,QPainter,QMouseEvent
from PySide6.QtTest import QTest
from document_model import Document,Mark
from image_capture import IMAGES,clipboard_image,image_path,CropCanvas,capture_region
from application import Overlay,Toolbar
app=QApplication([]);d=Document();o=Overlay(d);o.show();t=Toolbar(o);t.show();app.processEvents()
source=QImage(160,100,QImage.Format_ARGB32);source.fill(QColor('red'));p=QPainter(source);p.fillRect(80,0,80,100,QColor('blue'));p.end()
def event(kind,point,mod=Qt.NoModifier):return QMouseEvent(kind,point,point,Qt.LeftButton,Qt.LeftButton,mod)
try:
 t.choose_tool('fetcher')
 with patch('image_capture.capture_region',return_value=source):
  QTest.mousePress(o,Qt.LeftButton,pos=QPoint(500,300));QTest.mouseRelease(o,Qt.LeftButton,pos=QPoint(660,400));QTest.qWait(220)
 assert len(d.marks)==1 and d.marks[0].kind=='image' and o.selected=={0} and o.tool=='select'
 m=d.marks[0];key=m.image_id;assert IMAGES.images[key]==source
 f=o.fetcher;count=len(d._undo);h=f.handles(m)[2]
 assert f.press(event(QEvent.MouseButtonPress,h));f.move(event(QEvent.MouseMove,h+QPointF(80,50)));f.release(event(QEvent.MouseButtonRelease,h+QPointF(80,50)))
 assert len(d._undo)==count+1 and d.marks[0].image_size==(240,150)
 assert d.undo() and d.marks[0].image_size==(160,100);assert d.redo()
 assert len(f.buttons)==8 and all(button.menu() is None for button in f.buttons.values())
 for angle in (90,180,270,0,90):
  QTest.mouseClick(f.buttons['Rotate'],Qt.LeftButton);assert d.marks[0].rotation==angle
 QTest.mouseClick(f.buttons['Rotate'],Qt.LeftButton,Qt.ShiftModifier);assert d.marks[0].rotation==0
 for label in ('Flip horizontal','Flip vertical'):
  QTest.mouseClick(f.buttons[label],Qt.LeftButton)
 assert d.marks[0].flip_x and d.marks[0].flip_y
 QTest.mouseClick(f.buttons['Rotate'],Qt.LeftButton,Qt.ControlModifier)
 assert d.marks[0].rotation==0 and not d.marks[0].flip_x and not d.marks[0].flip_y
 QTest.mouseClick(f.buttons['Rotate'],Qt.LeftButton)
 for label in ('Flip horizontal','Flip vertical'):
  for _ in range(3):QTest.mouseClick(f.buttons[label],Qt.LeftButton)
 assert d.marks[0].flip_x and d.marks[0].flip_y
 f.edit(crop=(.5,0,1,1));assert IMAGES.images[key]==source
 image=clipboard_image(d.marks[0]);assert not image.isNull()
 QTest.mouseClick(f.buttons['Copy'],Qt.LeftButton,Qt.ShiftModifier);assert len(d.marks)==2 and d.marks[0].image_id==d.marks[1].image_id
 f.edit(rotation=180);assert d.marks[0].rotation==90 and d.marks[1].rotation==180
 QTest.mouseClick(f.buttons['Backward'],Qt.LeftButton,Qt.ShiftModifier);assert o.selected=={0} and d.marks[0].rotation==180
 QTest.mouseClick(f.buttons['Forward'],Qt.LeftButton,Qt.ShiftModifier);assert o.selected=={1}
 QTest.mouseClick(f.buttons['Backward'],Qt.LeftButton);assert o.selected=={0}
 QTest.mouseClick(f.buttons['Forward'],Qt.LeftButton);assert o.selected=={1}
 QTest.mouseClick(f.buttons['Copy'],Qt.LeftButton);assert not QApplication.clipboard().image().isNull()
 def accept_crop():
  for w in app.topLevelWidgets():
   if isinstance(w,QDialog):
    canvas=w.findChild(CropCanvas);canvas.crop=QRectF(0,0,1,1);w.accept()
 QTimer.singleShot(20,accept_crop);f.buttons['Crop'].click();assert d.marks[1].crop==(0,0,1,1)
 f.bar.grab().save('fetcher-compact-preview.png')
 f.buttons['Delete'].click();assert len(d.marks)==1;o.undo();assert len(d.marks)==2;o.redo();assert len(d.marks)==1
 o.set_tool('fetcher');QTest.mousePress(o,Qt.LeftButton,pos=QPoint(400,300));QTest.keyClick(o,Qt.Key_Escape);assert f.start is None and o.click_through
 t.choose_tool('pen');t.set_color('#ff0000');t.set_width(3);t.choose_tool('highlight');assert o.width==20 and o.color=='#ffcb3d'
 t.set_width(32);t.set_color('#00ff00');t.choose_tool('pen');assert o.width==3 and o.color=='#ff0000'
 t.choose_tool('highlight');assert o.width==32 and o.color=='#00ff00'
 # Capturing left-of-primary with non-unit DPR maps to the exact source pixels.
 class Shot:
  def toImage(self):return source
 class Screen:
  def geometry(self):return QRectF(-80,0,80,50).toRect()
  def devicePixelRatio(self):return 2
  def grabWindow(self,n):return Shot()
 with patch('image_capture.QGuiApplication.screens',return_value=[Screen()]):
  cropped=capture_region(QRectF(40,0,40,50),QPoint(-80,0))
  assert cropped.size().width()==80 and cropped.pixelColor(0,0)==QColor('blue')
 print('PASS: Fetcher capture/cancel, resize/undo, transforms, crop restore, duplicate isolation, clipboard, layers, DPI mapping and independent marker settings')
finally:t.close()

