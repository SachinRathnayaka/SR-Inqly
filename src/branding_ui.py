"""Startup progress and lightweight developer information."""
import logging
from PySide6 import __version__ as PYSIDE_VERSION
from PySide6.QtCore import qVersion, Qt, QUrl, QPropertyAnimation, QEventLoop
from PySide6.QtGui import QColor, QPainter, QLinearGradient, QPixmap, QDesktopServices, QIcon
from PySide6.QtWidgets import QWidget, QApplication, QLabel, QPushButton, QHBoxLayout, QMessageBox
from branding import NAME, VERSION, DEVELOPER, GITHUB, COPYRIGHT, SOURCE_MODEL, LICENSE_SUMMARY, resource


def open_profile(parent=None):
    if parent is not None:
        parent.overlay.set_click_through(True)
    if not QDesktopServices.openUrl(QUrl(GITHUB)):
        QMessageBox.warning(None, NAME, 'Could not open the default browser.\n'+GITHUB)


def developer_footer(parent):
    footer = QWidget(parent)
    row = QHBoxLayout(footer);row.setContentsMargins(0,0,0,0);row.setSpacing(4)
    row.addWidget(QLabel('Developed by'))
    name = QLabel(DEVELOPER);github = QPushButton('GitHub')
    name.setObjectName('developerName')
    name.setToolTip(f'<b>Developer</b><br>{DEVELOPER}<br><br><b>Application</b><br>{NAME}<br>{COPYRIGHT}<br><br><b>{SOURCE_MODEL}</b><br>{LICENSE_SUMMARY}')
    name.setCursor(Qt.ArrowCursor)
    row.addWidget(name)
    github.setToolTip('Open GitHub Profile')
    github.setCursor(Qt.PointingHandCursor)
    github.setFocusPolicy(Qt.NoFocus)
    github.setStyleSheet('QPushButton {border:none;background:transparent;padding:0;font-size:10px;} QPushButton:hover {text-decoration:underline;}')
    github.clicked.connect(lambda: open_profile(parent));row.addWidget(github)
    footer.setStyleSheet('QLabel {font-size:9px;}')
    return footer


def show_about(parent):
    parent.overlay.set_click_through(True)
    box = QMessageBox(parent)
    box.setWindowTitle('About '+NAME)
    box.setIconPixmap(QPixmap(str(resource('assets/sr-inqly-logo.png'))).scaled(180,110,Qt.KeepAspectRatio,Qt.SmoothTransformation))
    bg=parent.appearance.background
    fg=parent.appearance.foreground
    box.setStyleSheet(f'QMessageBox {{background-color:{bg};color:{fg};}} QLabel {{background:transparent;color:{fg};}} QPushButton {{background:{bg};color:{fg};border:1px solid {fg};padding:6px 18px;}}')
    box.setTextFormat(Qt.RichText)
    box.setText(f'<h2>{NAME} {VERSION}</h2>Developed by {DEVELOPER}<br><a style="color:{fg}" href="{GITHUB}">GitHub</a><br><br>{COPYRIGHT}<br>{SOURCE_MODEL}<br><br>{LICENSE_SUMMARY}<br><br>Uses Qt {qVersion()} / PySide6 {PYSIDE_VERSION}.<br>Qt &copy; The Qt Company Ltd. and contributors.<br>Third-party license texts and source links: THIRD_PARTY_NOTICES.md and licenses/ in the application folder.')
    box.exec()


class Splash(QWidget):
    def __init__(self):
        super().__init__(None,Qt.SplashScreen|Qt.FramelessWindowHint|Qt.WindowStaysOnTopHint)
        self.setFixedSize(640,450)
        self.setWindowTitle(NAME+' — starting')
        self.logo=QPixmap(str(resource('assets/sr-inqly-logo.png')))
        self.value=0;self.message='Starting '+NAME
        self.move(QApplication.primaryScreen().availableGeometry().center()-self.rect().center())

    def progress(self,value,message):
        self.value=value;self.message=message;self.update()
        QApplication.processEvents(QEventLoop.ExcludeUserInputEvents)

    def paintEvent(self,event):
        p=QPainter(self);p.setRenderHint(QPainter.Antialiasing)
        bg=QLinearGradient(0,0,640,450);bg.setColorAt(0,QColor('#020919'));bg.setColorAt(1,QColor('#170c2b'));p.fillRect(self.rect(),bg)
        logo=self.logo.scaled(360,205,Qt.KeepAspectRatio,Qt.SmoothTransformation)
        p.drawPixmap((640-logo.width())//2,12,logo)
        font=p.font();font.setPointSize(34);font.setBold(True);p.setFont(font);p.setPen(QColor('white'));p.drawText(0,219,640,55,Qt.AlignCenter,NAME)
        font.setPointSize(10);font.setBold(False);p.setFont(font);p.drawText(0,278,640,24,Qt.AlignCenter,'WRITE • DRAW • HIGHLIGHT • ANNOTATE • ANYWHERE')
        p.fillRect(60,321,520,9,QColor('#263349'))
        gradient=QLinearGradient(60,0,580,0)
        for at,color in ((0,'#00e5ff'),(.3,'#1265ff'),(.55,'#9639ff'),(.8,'#ff31dd'),(1,'#ffae35')):gradient.setColorAt(at,QColor(color))
        p.fillRect(60,321,round(520*self.value/100),9,gradient)
        p.drawText(0,340,640,25,Qt.AlignCenter,f'{self.value}% · {self.message}')
        p.setPen(QColor('#85dcff'));p.drawText(0,380,640,24,Qt.AlignCenter,'Created by '+DEVELOPER)
        p.setPen(QColor('#b8b4ce'));p.drawText(0,411,640,24,Qt.AlignCenter,SOURCE_MODEL+' · © 2026 '+DEVELOPER)

    def finish(self):
        self.progress(100,'Ready')
        self.fade=QPropertyAnimation(self,b'windowOpacity',self)
        self.fade.setDuration(160);self.fade.setStartValue(1.0);self.fade.setEndValue(0.0)
        self.fade.finished.connect(self.close);self.fade.start()
