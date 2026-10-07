"""Reproduce the review's geometry, capture and renderer-cache defects."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from unittest.mock import patch,MagicMock
from PySide6.QtCore import QPointF,QRect,QRectF,Qt,QTimer
from PySide6.QtGui import QImage,QPainter,QPainterPath
from PySide6.QtWidgets import QApplication
from application import Overlay,Toolbar,Document,draw_mark
from document_model import Mark
from selection_tools import indices_in_region
from pen_effects import PenTrails
app=QApplication([]);o=Overlay(Document());o.show();t=Toolbar(o);t.show();t.persist_settings=False;app.processEvents()
try:
 m=Mark('pen',[(100,100),(200,300),(300,100)],width=4,neon=True)
 assert m.hit(200,250) and not m.hit(200,300)
 region=QPainterPath();region.addRect(QRectF(198,248,4,4))
 assert indices_in_region([m],region)=={0}
 o.document.marks=[m];o.erase_at(200,250);assert not o.document.marks
 o.set_click_through(False)
 fake=MagicMock();fake.devicePixelRatio.return_value=1
 fake.geometry.return_value=QRect(0,0,100,100)
 with patch('application.QGuiApplication.screens',return_value=[fake]),patch('application.virtual_geometry',return_value=QRect(0,0,100000,100000)):
  try:t.capture();raise AssertionError('Capture limit not enforced')
  except ValueError:pass
  assert not fake.grabWindow.called and t.isVisible() and o.isVisible()
 fake.grabWindow.side_effect=RuntimeError('Injected screen failure')
 responsive=[];QTimer.singleShot(20,lambda:responsive.append(True))
 with patch('application.QGuiApplication.screens',return_value=[fake]),patch('application.virtual_geometry',return_value=QRect(0,0,100,100)):
  try:t.capture();raise AssertionError('Injected failure not raised')
  except RuntimeError:pass
 assert responsive and t.isVisible() and o.isVisible() and not o.click_through and not t._capture_busy
 clock=[10.];trails=PenTrails(o,lambda:clock[0]);trails.begin((100,100),'#40b9ff',4,1,True,3)
 for x in range(101,1001):clock[0]+=.001;trails.append((x,100))
 trails.end();clock[0]+=3.5
 image=QImage(1200,250,QImage.Format_ARGB32_Premultiplied);image.fill(Qt.transparent)
 p=QPainter(image);trails.paint(p,QRectF(image.rect()));p.end()
 cached=trails.trails[0].geometry()
 p=QPainter(image);trails.paint(p,QRectF(image.rect()));p.end()
 assert trails.trails[0].geometry() is cached
 assert len(cached[1])<50
 clock[0]+=10;trails.tick();assert not trails.trails and not trails.timer.isActive()
 fake.grabWindow.reset_mock()
 def closing():t._closing=True
 QTimer.singleShot(20,closing)
 with patch('application.QGuiApplication.screens',return_value=[fake]),patch('application.virtual_geometry',return_value=QRect(0,0,100,100)):
  try:t.capture();raise AssertionError('Closing capture accepted')
  except RuntimeError:pass
 assert not fake.grabWindow.called and not t.isVisible() and not o.isVisible() and not t._capture_busy
 print('PASS: neon curve hit/area/erase, capture allocation guard and error restoration, responsive DWM wait, reused time-binned fade geometry')
finally:t.close()
