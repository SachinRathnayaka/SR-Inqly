"""Minimal Qt bootstrap: show branded progress before loading the drawing UI."""
import sys
if '--performance-check' in sys.argv:
    from application import main
    raise SystemExit(main())
from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtGui import QIcon
from branding import NAME, resource
from branding_ui import Splash
app=QApplication(sys.argv)
app.setApplicationName(NAME)
app.setWindowIcon(QIcon(str(resource('assets/sr-inqly.ico'))))
splash=Splash();splash.show();splash.progress(5,'Loading application')
try:
    from application import main
    splash.progress(35,'Resources loaded')
    raise SystemExit(main(splash))
except Exception:
    import logging
    from PySide6.QtCore import QStandardPaths
    from pathlib import Path
    folder=Path(QStandardPaths.writableLocation(QStandardPaths.AppLocalDataLocation));folder.mkdir(parents=True,exist_ok=True)
    logging.basicConfig(filename=str(folder/'startup.log'),level=logging.ERROR)
    logging.exception('Startup failed');splash.close()
    QMessageBox.critical(None,NAME,'Startup failed. Diagnostic log: '+str(folder/'startup.log'))
    raise SystemExit(1)
