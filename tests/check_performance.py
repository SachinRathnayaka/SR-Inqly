import os,random
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QImage,QPainter
from PySide6.QtCore import Qt,QRectF
from document_model import Document,Mark,TextStyle
from application import draw_mark
from render_cache import RenderCache
app=QApplication([])
marks=[Mark(k,[(30,40),(100,100)],'#4488ff',6,'test',TextStyle(),(120,40),.35) for k in ('pen','highlight','line','arrow','rectangle','ellipse','text')]
for mark in marks:
 images=[]
 for cached in (False,True):
  image=QImage(300,200,QImage.Format_ARGB32_Premultiplied);image.fill(Qt.transparent)
  p=QPainter(image);p.setRenderHint(QPainter.Antialiasing)
  if cached:RenderCache(draw_mark).paint(p,[mark],QRectF(image.rect()))
  else:draw_mark(p,mark)
  p.end();images.append(image)
 assert images[0]==images[1],mark.kind
# Snapshot integrity even for callers mutating points/styles in place.
d=Document();d.marks=marks;d.checkpoint();d.marks[0].points[0]=(999,999);d.marks[-1].text_style.size=45
assert d.undo() and d.marks[0].points[0]==(30,40) and d.marks[-1].text_style.size==20
assert d.redo() and d.marks[0].points[0]==(999,999) and d.marks[-1].text_style.size==45
d.history_budget=20000
for i in range(200):
 d.checkpoint();d.marks=[Mark('pen',[(i,j) for j in range(100)])]
 assert len(d._undo)<=100 and d.history_bytes<=d.history_budget
cache=RenderCache(draw_mark);cache.budget=40000
for i in range(300):cache.get(Mark('pen',[(i,j) for j in range(100)]))
assert cache.bytes<=cache.budget
print('PASS: cached pixels match every tool, isolated mutable undo/redo, history/cache budgets')
