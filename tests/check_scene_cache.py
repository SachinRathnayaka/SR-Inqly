import os,copy
os.environ['QT_QPA_PLATFORM']='offscreen'
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt,QRectF,QSize
from PySide6.QtGui import QImage,QPainter
from document_model import Mark
from render_cache import RenderCache,SceneCache
from application import draw_mark
from image_capture import IMAGES
app=QApplication([])
for dpr in (1,1.25,2):
 cache=SceneCache(RenderCache(draw_mark));marks=[]
 def check(skip=None):
  images=[]
  for cached in (False,True):
   im=QImage(round(320*dpr),round(240*dpr),QImage.Format_ARGB32_Premultiplied);im.setDevicePixelRatio(dpr);im.fill(Qt.transparent)
   p=QPainter(im);p.setRenderHint(QPainter.Antialiasing)
   if cached:cache.paint(p,marks,QRectF(0,0,320,240),QSize(320,240),dpr,skip)
   else:
    for i,m in enumerate(marks):
     if i!=skip:draw_mark(p,m)
   p.end();images.append(im)
  assert images[0]==images[1],(dpr,len(marks),skip)
 check()
 for k in ('pen','highlight','line','arrow','rectangle','ellipse','text'):
  marks.append(Mark(k,[(30,40),(100,100)],'#4488ff',6,opacity=.35));check()
 source=QImage(30,20,QImage.Format_ARGB32_Premultiplied);source.fill(Qt.red)
 marks.append(Mark('image',[(130,80)],image_id=IMAGES.add(source),image_size=(90,60),rotation=33,flip_x=True));check()
 check();check(2);check()
 marks.reverse();check()
 marks[1]=marks[1].moved(70,20);check()
 del marks[2];check()
 marks.clear();check()
 cache.budget=1;marks.append(Mark('pen',[(10,10),(90,80)]));check();assert cache.image is None
print('PASS: raster cache exact pixels at 100/125/200%, edits, reorder, skip, clear and budget fallback')
