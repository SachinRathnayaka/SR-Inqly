import os,tempfile
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from pathlib import Path
from unittest.mock import patch
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QImage
from document_model import Document
from application import Overlay,Toolbar
app=QApplication([]);o=Overlay(Document());o.show();t=Toolbar(o);t.show();app.processEvents()
try:
 with tempfile.TemporaryDirectory() as directory:
  image=QImage(20,20,QImage.Format_ARGB32);image.fill(0xffffffff)
  with patch('application.QStandardPaths.writableLocation',return_value=directory),patch.object(t,'capture',return_value=image):
   o.set_click_through(False)
   t.quick_screenshot();t.quick_screenshot()
   folder=Path(directory)/'SR Inqly Screenshots'
   assert len(list(folder.glob('*.png')))==2
   assert len(list(Path(directory).iterdir()))==1
   assert not o.click_through
   assert all(not QImage(str(p)).isNull() for p in folder.iterdir())
   t.toggle_compact();app.processEvents();assert t.appearance.quick_button.isVisible()
   t.quick_screenshot();assert len(list(folder.glob('*.png')))==3
   t.toggle_compact();assert t.appearance.quick_button.isVisible()
 print('PASS: same Pictures subfolder, unique PNGs, no dialog, mode preserved, both layouts')
finally:t.close()
