import os
os.environ.setdefault('QT_QPA_PLATFORM','windows')
from PySide6.QtWidgets import QApplication,QMenu
from PySide6.QtCore import Qt,QPoint
from PySide6.QtTest import QTest
from application import Overlay,Toolbar
from document_model import Document
from appearance import luminance
app=QApplication([]);o=Overlay(Document());o.show();t=Toolbar(o);t.show();app.processEvents()
a=t.appearance;original=a.background
try:
 for color in ('#f4f6fa','#171d2b','#ffff00','#f00088','#00aa88','#808080'):
  a.background=color;a.apply()
  ratio=(max(luminance(color),luminance(a.foreground))+.05)/(min(luminance(color),luminance(a.foreground))+.05)
  assert ratio>=4.5,(color,ratio)
 t.toggle_compact();app.processEvents()
 assert a.panel.isVisible() and not t.scale_slider.isVisible() and not t.scroll_area.isVisible()
 for tool,b in a.tools.items():
  QTest.mouseClick(b,Qt.LeftButton);assert o.tool==tool
 a.open_shapes();app.processEvents();menu=t.findChildren(QMenu)[-1]
 assert len(menu.actions())==6
 menu.actions()[4].trigger();menu.close();assert o.tool=='arrow'
 a.open_colors();app.processEvents();menu=next(m for m in t.findChildren(QMenu) if any(a.text()=='Red' for a in m.actions()))
 assert [a.text() for a in menu.actions()[:7]]==['Red','Yellow','Green','Blue','Purple','White','Black']
 assert any(a.text()=='Neon pen' and a.isCheckable() for a in menu.actions())
 menu.actions()[1].trigger();menu.close();assert o.color=='#ffcb3d'
 for scale in (75,150,100):
  t.apply_ui_scale(scale);app.processEvents();assert not t.scale_slider.isVisible()
  assert not o.mask().contains(t.mapToGlobal(QPoint(20,20))-o.pos())
 a.background='#f4f6fa';a.apply();app.processEvents();t.grab().save('compact-light-1.6.png')
 a.background='#171d2b';a.apply();app.processEvents();t.grab().save('compact-dark-1.6.png')
 t.toggle_compact();app.processEvents();assert t.scale_slider.isVisible() and not a.panel.isVisible()
 t.choose_tool('text');o.begin_text(QPoint(500,300));e=o.text_editor
 assert e.input.font().pointSizeF()==e.mark.text_style.size and e.input.cursorWidth()==0
 print('PASS: theme contrast, compact tools, menus, scaling, input mask and placeholder font')
finally:
 a.background=original;t.close()
