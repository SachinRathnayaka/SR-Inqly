import os,tempfile
os.environ.setdefault('QT_QPA_PLATFORM','windows')
from unittest.mock import patch
from PySide6.QtWidgets import QApplication,QPushButton,QLabel,QMessageBox
from PySide6.QtCore import Qt,QSettings,QTimer
from PySide6.QtTest import QTest
from branding_ui import Splash,developer_footer,show_about
from branding import GITHUB
from application import Overlay,Toolbar
from document_model import Document
import preferences
app=QApplication([]);s=Splash();s.show()
try:
 for value in (0,25,70,100):s.progress(value,'Stage');assert s.value==value
 s.grab().save('sr-inqly-splash-preview.png');s.finish();QTest.qWait(220);assert not s.isVisible()
 o=Overlay(Document());o.show();t=Toolbar(o);t.show();app.processEvents()
 with patch('branding_ui.QDesktopServices.openUrl',return_value=True) as open_url:
  label=t.developer_footer.findChild(QLabel,'developerName')
  QTest.mouseClick(label,Qt.LeftButton);assert open_url.call_count==0
  assert 'Click to visit' not in label.toolTip()
  for button in t.developer_footer.findChildren(QPushButton):
   before=open_url.call_count;QTest.mouseClick(button,Qt.LeftButton);assert open_url.call_count==before+1 and open_url.call_args.args[0].toString()==GITHUB
 for theme in ('#f4f6fa','#171d2b','#cc55aa'):
  t.appearance.background=theme;t.appearance.apply()
  def inspect_about():
   box=app.activeModalWidget();assert isinstance(box,QMessageBox)
   assert f'background-color:{theme}' in box.styleSheet()
   assert f'color:{t.appearance.foreground}' in box.styleSheet()
   box.grab().save('about-'+('light' if theme=='#f4f6fa' else 'dark' if theme=='#171d2b' else 'custom')+'-preview.png')
   box.accept()
  QTimer.singleShot(200,inspect_about);show_about(t)
 with tempfile.TemporaryDirectory() as folder:
  settings=QSettings(folder+'/settings.ini',QSettings.IniFormat)
  settings.setValue('pen_width','corrupt');settings.setValue('pen_color','invalid');settings.setValue('ui_scale',9999)
  with patch('preferences.settings',return_value=settings):
   preferences.restore(t);assert o.pen_width==4 and o.pen_color=='#ff4655' and t.scale_slider.value()==150
   t.choose_tool('highlight');t.set_width(33);t.set_color('#123456');preferences.save(t);preferences.restore(t);assert o.highlighter_width==33 and o.highlighter_color=='#123456'
 t.persist_settings=False;t.close()
 print('PASS: staged splash/fade, one-click official links, corrupted settings fallback and profile persistence')
finally:s.close()
