import os
os.environ['QT_QPA_PLATFORM']='offscreen'
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QPainter,QImage
from PySide6.QtCore import Qt,QRectF
from document_model import Mark,TextStyle
from render_cache import RenderCache,SceneCache
from application import draw_mark
app=QApplication([])
marks=[Mark('text',[(60,100)],'#ff4655',text='ssachin',text_style=TextStyle(),text_box=(300,90))]
scene=SceneCache(RenderCache(draw_mark))
def check(skip=None):
 images=[]
 for cached in (False,True):
  image=QImage(900,600,QImage.Format_ARGB32_Premultiplied);image.fill(Qt.transparent)
  painter=QPainter(image);painter.setRenderHint(QPainter.Antialiasing)
  if cached:scene.paint(painter,marks,QRectF(image.rect()),image.size(),skip=skip)
  else:
   for i,mark in enumerate(marks):
    if i!=skip:draw_mark(painter,mark)
  painter.end();images.append(image)
 assert images[0]==images[1],('cache ghost',skip,marks[0].points,scene.records)
check()
for dx,dy in ((210,50),(-160,180),(300,-70)):
 check(0)
 marks[0]=marks[0].moved(dx,dy)
 check()
print('PASS: populated text hide/edit/move leaves exactly one rendered text object')
