"""Opt-in passive Windows raw mouse input. Never suppresses desktop clicks."""
import ctypes
import sys
from PySide6.QtCore import QAbstractNativeEventFilter
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import QApplication

class Device(ctypes.Structure):
    _fields_=[('page',ctypes.c_ushort),('usage',ctypes.c_ushort),('flags',ctypes.c_uint),('target',ctypes.c_void_p)]

class Header(ctypes.Structure):
    _fields_=[('kind',ctypes.c_uint),('size',ctypes.c_uint),('device',ctypes.c_void_p),('param',ctypes.c_size_t)]

class Mouse(ctypes.Structure):
    _fields_=[('flags',ctypes.c_ushort),('padding',ctypes.c_ushort),('buttons',ctypes.c_uint),
             ('raw_buttons',ctypes.c_uint),('x',ctypes.c_int),('y',ctypes.c_int),('extra',ctypes.c_uint)]

class DesktopPen(QAbstractNativeEventFilter):
    def __init__(self, toolbar):
        super().__init__()
        self.toolbar=toolbar;self.enabled=False;self.dragging=False

    def enable(self):
        if self.enabled:return True
        if sys.platform!='win32':return False
        user32=ctypes.windll.user32
        user32.RegisterRawInputDevices.argtypes=[ctypes.POINTER(Device),ctypes.c_uint,ctypes.c_uint]
        user32.RegisterRawInputDevices.restype=ctypes.c_bool
        user32.GetRawInputData.argtypes=[ctypes.c_void_p,ctypes.c_uint,ctypes.c_void_p,ctypes.POINTER(ctypes.c_uint),ctypes.c_uint]
        user32.GetRawInputData.restype=ctypes.c_uint
        device=Device(1,2,0x100,int(self.toolbar.winId()))
        if not user32.RegisterRawInputDevices(ctypes.byref(device),1,ctypes.sizeof(Device)):return False
        QApplication.instance().installNativeEventFilter(self)
        self.enabled=True
        return True

    def disable(self):
        if self.enabled:
            device=Device(1,2,1,None)
            ctypes.windll.user32.RegisterRawInputDevices(ctypes.byref(device),1,ctypes.sizeof(Device))
            QApplication.instance().removeNativeEventFilter(self)
        self.enabled=False;self.dragging=False

    def feed(self, point, down=False, up=False):
        o=self.toolbar.overlay
        if not self.enabled or not o.desktop_neon or not o.click_through:
            if self.dragging:o.trails.end()
            self.dragging=False
            return
        own_ui=any(w is not o and w.isVisible() and w.frameGeometry().contains(point)
                   for w in QApplication.topLevelWidgets())
        local=o.mapFromGlobal(point);position=(local.x(),local.y())
        if up:
            if self.dragging:o.trails.append(position);o.trails.end();o.trails.schedule()
            self.dragging=False
        elif down and not own_ui:
            o.trails.begin(position,o.pen_color,o.pen_width,o.opacity,True,o.pen_fade_delay)
            self.dragging=True
        elif self.dragging and not own_ui:
            o.trails.append(position)

    def nativeEventFilter(self, event_type, message):
        try:
            from application import WINMSG
            msg=WINMSG.from_address(int(message))
            if msg.message!=0xFF or not self.enabled:return False,0
            size=ctypes.c_uint(0);user32=ctypes.windll.user32;handle=ctypes.c_void_p(msg.lParam)
            if user32.GetRawInputData(handle,0x10000003,None,ctypes.byref(size),ctypes.sizeof(Header))==0xFFFFFFFF:return False,0
            if size.value<ctypes.sizeof(Header)+ctypes.sizeof(Mouse) or size.value>4096:return False,0
            buffer=ctypes.create_string_buffer(size.value)
            if user32.GetRawInputData(handle,0x10000003,buffer,ctypes.byref(size),ctypes.sizeof(Header))==0xFFFFFFFF:return False,0
            if Header.from_buffer(buffer).kind!=0:return False,0
            mouse=Mouse.from_buffer(buffer,ctypes.sizeof(Header));flags=mouse.buttons&0xFFFF
            self.feed(QCursor.pos(),bool(flags&1),bool(flags&2))
        except Exception:
            self.disable();self.toolbar.overlay.desktop_neon=False
            self.toolbar.overlay.message.emit('Desktop neon stopped; normal mouse input is unaffected')
        return False,0
