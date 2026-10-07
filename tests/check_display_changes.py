import os
os.environ['QT_QPA_PLATFORM']='offscreen'
from unittest.mock import patch
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QRect
from document_model import Document
from application import Overlay,Toolbar
app=QApplication([]);o=Overlay(Document());o.show();t=Toolbar(o);t.show();app.processEvents()
try:
 o.set_click_through(False)
 with patch('application.virtual_geometry',return_value=QRect(-100,0,1280,720)):
  o.refresh_displays()
  assert o.geometry()==QRect(-100,0,1280,720) and o.click_through
 o.display_dpi=();o.set_click_through(False);o.refresh_displays();assert o.click_through
 print('PASS: simulated virtual desktop and DPI change release input and refresh bounds')
finally:t.close()
