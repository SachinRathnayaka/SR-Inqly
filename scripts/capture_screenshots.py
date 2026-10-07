"""Capture real Qt app controls on a private, generated demonstration canvas."""
from pathlib import Path
from dataclasses import replace
import math
import sys
from PySide6.QtCore import Qt,QPointF,QRectF,QSettings
from PySide6.QtGui import QImage,QPainter,QColor,QFont,QLinearGradient,QPen
from PySide6.QtWidgets import QApplication

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'src'))
from application import Overlay,Toolbar
from document_model import Document,Mark,TextStyle
from image_capture import IMAGES
from branding_ui import Splash
from branding import VERSION,resource

output=ROOT/'docs/images';output.mkdir(parents=True,exist_ok=True)
app=QApplication([])
app.setQuitOnLastWindowClosed(False)

def text(p,x,y,content,size,color='#dbe6fa',bold=False):
    p.setFont(QFont('Segoe UI',size,QFont.Bold if bold else QFont.Normal))
    p.setPen(QColor(color));p.drawText(x,y,content)

def canvas():
    image=QImage(1440,900,QImage.Format_ARGB32_Premultiplied)
    p=QPainter(image);p.setRenderHint(QPainter.Antialiasing)
    gradient=QLinearGradient(0,0,1440,900)
    gradient.setColorAt(0,QColor('#07111f'));gradient.setColorAt(1,QColor('#19223a'))
    p.fillRect(image.rect(),gradient)
    p.setPen(QPen(QColor('#203047'),1))
    for x in range(0,1440,40):p.drawLine(x,0,x,900)
    for y in range(0,900,40):p.drawLine(0,y,1440,y)
    text(p,530,98,'A clearer way to explain.',30,bold=True)
    text(p,532,136,'Your screen. Your ideas. A little ink.',16,'#91a6c3')
    p.setPen(Qt.NoPen);p.setBrush(QColor('#14243a'));p.drawRoundedRect(QRectF(510,200,850,260),18,18)
    text(p,550,251,'Presentation notes',18,bold=True)
    for y,label in ((305,'Highlight the idea that matters.'),(358,'Draw attention with arrows and shapes.'),(411,'Write directly on your screen.')):
        text(p,553,y,label,20)
    p.setBrush(QColor('#14243a'));p.drawRoundedRect(QRectF(510,505,850,305),18,18)
    text(p,550,557,'A small sketch can make a big difference.',18,bold=True)
    text(p,530,859,'SR Inqly '+VERSION+'  /  Demonstration canvas',11,'#879fbd')
    p.end();return image

doc=Document();o=Overlay(doc);o.setGeometry(0,0,1440,900);o.show()
t=Toolbar(o);t.persist_settings=False;t.show()
settings_folder=ROOT/'build';settings_folder.mkdir(exist_ok=True)
t.appearance.settings=QSettings(str(settings_folder/'screenshots.ini'),QSettings.IniFormat)
t.appearance.background='#171d2b';t.appearance.apply();t.apply_ui_scale(90);t.move(40,50)

def screenshot(filename):
    app.processEvents()
    o.display_timer.stop()
    o.set_click_through(False)
    app.processEvents()
    image=canvas();p=QPainter(image)
    p.drawPixmap(0,0,o.grab())
    p.drawPixmap(t.x()-o.x(),t.y()-o.y(),t.grab())
    p.end();assert image.save(str(output/filename))

try:
    doc.marks=[
        Mark('highlight',[(550,296),(1160,296)],'#ffcb3d',28,opacity=.75),
        Mark('rectangle',[(543,330),(1280,378)],'#40b9ff',3),
        Mark('arrow',[(1295,205),(1240,289)],'#ff4655',5),
        Mark('text',[(565,590)],'#57dd9b',text='Explain it visually.',text_style=TextStyle(size=25),text_box=(620,65)),
        Mark('pen',[(565+i*7,700+math.sin(i/7)*33) for i in range(80)],'#a895ff',5),
    ]
    t.choose_tool('pen');screenshot('interface-full.png')
    t.toggle_compact();t.move(40,50);screenshot('interface-compact.png')
    t.appearance.background='#f4f6fa';t.appearance.apply();screenshot('interface-light.png')
    t.appearance.background='#171d2b';t.appearance.apply()
    # Leave clear space for the editing toolbar below the demonstration heading.
    original_sketch = doc.marks[4]
    doc.marks[4] = replace(original_sketch, points=[(565+i*7,775+math.sin(i/7)*18) for i in range(80)])
    t.choose_tool('text');o.begin_text(index=3);o.text_editor.move(570,650)
    o.text_editor.input.caret_timer.stop();o.text_editor.input.caret_visible=True
    screenshot('inline-text.png');o.finish_text()
    doc.marks[4] = original_sketch
    captured=QImage(500,220,QImage.Format_ARGB32_Premultiplied);captured.fill(QColor('#edf3ff'))
    p=QPainter(captured);p.setRenderHint(QPainter.Antialiasing)
    text(p,25,45,'A captured reference',18,'#172033',True)
    for i,height in enumerate((45,80,58,105,122,92,146)):
        p.fillRect(35+i*62,190-height,35,height,QColor('#1595df' if i%2 else '#6355df'))
    p.end()
    doc.marks.append(Mark('image',[(650,560)],image_id=IMAGES.add(captured),image_size=(600,264),rotation=-4))
    t.choose_tool('select');o.selected={len(doc.marks)-1};o.changed.emit()
    screenshot('image-fetcher.png')
    splash=Splash();splash.show();splash.progress(100,'Ready')
    assert splash.grab().save(str(output/'splash.png'));splash.close()
    banner=QImage(1440,470,QImage.Format_ARGB32_Premultiplied)
    p=QPainter(banner);p.setRenderHint(QPainter.Antialiasing)
    gradient=QLinearGradient(0,0,1440,470);gradient.setColorAt(0,QColor('#061022'));gradient.setColorAt(1,QColor('#211036'));p.fillRect(banner.rect(),gradient)
    logo=QImage(str(resource('assets/sr-inqly-logo.png')))
    p.drawImage(QRectF(70,35,430,330),logo)
    text(p,540,180,'SR Inqly',58,'#ffffff',True)
    text(p,544,236,'Write. Draw. Highlight. Annotate. Anywhere.',22,'#a9dfff')
    text(p,544,292,'A Windows screen annotation workspace',16,'#a8b9d4')
    text(p,544,385,'Created by Sachin Rathnayaka  •  Source Available',14,'#b2a5d2')
    p.end();assert banner.save(str(output/'banner.png'))
    print('Saved actual UI captures and banner:',output)
finally:
    t.persist_settings=False;t.close();o.close()
