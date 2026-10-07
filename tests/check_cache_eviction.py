"""Small edits must remain correct and local after compiled commands are evicted."""
import os
os.environ['QT_QPA_PLATFORM']='offscreen'
from unittest.mock import patch
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt,QRectF
from PySide6.QtGui import QImage,QPainter
from document_model import Mark
from render_cache import RenderCache,SceneCache
from application import draw_mark
app=QApplication([])
marks=[Mark('pen',[(x,10),(x+3,50)],width=2) for x in range(10,1900,10)]
commands=RenderCache(draw_mark);commands.budget=2000
scene=SceneCache(commands)
def render(cached):
 image=QImage(1920,100,QImage.Format_ARGB32_Premultiplied);image.fill(Qt.transparent)
 p=QPainter(image);p.setRenderHint(QPainter.Antialiasing)
 if cached:scene.paint(p,marks,QRectF(image.rect()),image.size())
 else:
  for mark in marks:draw_mark(p,mark)
 p.end();return image
assert render(True)==render(False)
marks[0]=marks[0].moved(1,1)
with patch.object(commands,'get',wraps=commands.get) as calls:
 assert render(True)==render(False)
 assert calls.call_count<10,(calls.call_count,len(marks))
 print('PASS: exact pixels after eviction; command lookups for one edit:',calls.call_count,'of',len(marks),'marks')
