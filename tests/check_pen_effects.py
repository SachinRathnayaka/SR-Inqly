"""Temporal pixels, glow bounds, normal history and passive mouse behavior."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QPoint, QRectF, Qt
from PySide6.QtGui import QImage, QPainter
from PySide6.QtTest import QTest
from application import Overlay, Toolbar, draw_mark
from document_model import Document, Mark
from pen_effects import PenTrails, remaining_alpha
from render_cache import RenderCache

app=QApplication([]);o=Overlay(Document());t=Toolbar(o);t.persist_settings=False
o.display_timer.stop();o.resize(800,500)
clock=[10.0];o.trails=PenTrails(o,lambda:clock[0])

def image():
    result=QImage(800,500,QImage.Format_ARGB32_Premultiplied);result.fill(Qt.transparent)
    painter=QPainter(result);painter.setRenderHint(QPainter.Antialiasing)
    o.trails.paint(painter,QRectF(0,0,800,500));painter.end();return result

try:
    assert abs(remaining_alpha(13.45,10,3,.9)-.5)<1e-9
    o.trails.begin((100,100),'#40b9ff',5,1,False,3)
    clock[0]=11;o.trails.append((200,100));o.trails.end()
    assert image().pixelColor(110,100).alpha()>200
    clock[0]=13.6;fading=image()
    assert fading.pixelColor(110,100).alpha()<fading.pixelColor(190,100).alpha()
    clock[0]=16;o.trails.tick();assert not o.trails.trails and not o.trails.timer.isActive()
    assert image().pixelColor(150,100).alpha()==0
    clock[0]=20;o.trails.begin((100,100),'#40b9ff',5,1,False,3)
    for x in range(101,401):o.trails.append((x,100))
    o.trails.end();clock[0]=23.45
    assert abs(image().pixelColor(250,100).alpha()-128)<=2
    o.trails.clear()
    t.neon_check.setChecked(True);t.fade_check.setChecked(True);t.choose_tool('pen')
    QTest.mousePress(o,Qt.LeftButton,pos=QPoint(200,250))
    QTest.mouseMove(o,QPoint(300,250));QTest.mouseRelease(o,Qt.LeftButton,pos=QPoint(350,250))
    assert o.trails.trails and not o.document.marks and not o.document._undo
    o.undo();assert not o.trails.trails
    t.fade_check.setChecked(False)
    QTest.mousePress(o,Qt.LeftButton,pos=QPoint(200,250));QTest.mouseRelease(o,Qt.LeftButton,pos=QPoint(350,250))
    assert o.document.marks[0].neon and o.document._undo
    o.undo();assert not o.document.marks;o.redo();assert o.document.marks[0].neon
    mark=o.document.marks[0];result=QImage(800,500,QImage.Format_ARGB32_Premultiplied);result.fill(Qt.transparent)
    painter=QPainter(result);RenderCache(draw_mark).paint(painter,[mark],QRectF(0,0,800,500));painter.end()
    assert result.pixelColor(270,256).alpha()>0
    assert mark.bounds()[1]<240
    assert not o.trails.timer.isActive()
    t.choose_tool('highlight');QTest.mousePress(o,Qt.LeftButton,pos=QPoint(200,300))
    assert not o.preview.neon;QTest.mouseRelease(o,Qt.LeftButton,pos=QPoint(350,300))
    from desktop_pen import DesktopPen
    raw=DesktopPen(t);raw.enabled=True;o.desktop_neon=True;o.set_click_through(True)
    raw.feed(o.mapToGlobal(QPoint(500,400)),down=True)
    raw.feed(o.mapToGlobal(QPoint(600,400)),up=True)
    assert o.trails.trails[-1].neon and not raw.dragging and o.click_through
    raw.enabled=False;o.trails.clear()
    o.trails.MAX_POINTS=64;o.trails.MAX_TRAILS=4
    for stroke in range(20):
        o.trails.begin((10,10),'#40b9ff',4,1,True,3)
        for point in range(20):o.trails.append((10+point*2,10+stroke))
        o.trails.end()
    assert len(o.trails.trails)<=4 and sum(len(t.points) for t in o.trails.trails)<=64
    clock[0]+=20;o.trails.tick();assert not o.trails.trails and not o.trails.timer.isActive()
    print('PASS: directional smooth fade, zero idle timer, temporary history isolation, neon cached pixels, highlighter independence and passive desktop input')
finally:
    t.close()
