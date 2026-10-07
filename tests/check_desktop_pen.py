"""Native Windows click-through: passive raw input and an underlying window."""
import ctypes
import time
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QPoint
from application import Document,Overlay,Toolbar

app=QApplication([]);o=Overlay(Document());o.show();t=Toolbar(o);t.show();t.persist_settings=False
user32=ctypes.windll.user32
user32.CreateWindowExW.argtypes=[ctypes.c_ulong,ctypes.c_wchar_p,ctypes.c_wchar_p,ctypes.c_ulong,
                               ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_void_p,
                               ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p]
user32.CreateWindowExW.restype=ctypes.c_void_p
user32.DefWindowProcW.argtypes=[ctypes.c_void_p,ctypes.c_uint,ctypes.c_size_t,ctypes.c_ssize_t]
user32.DefWindowProcW.restype=ctypes.c_ssize_t
user32.SetWindowLongPtrW.argtypes=[ctypes.c_void_p,ctypes.c_int,ctypes.c_void_p]
user32.SetWindowLongPtrW.restype=ctypes.c_ssize_t
user32.DestroyWindow.argtypes=[ctypes.c_void_p]
user32.SetForegroundWindow.argtypes=[ctypes.c_void_p]
callback_type=ctypes.WINFUNCTYPE(ctypes.c_ssize_t,ctypes.c_void_p,ctypes.c_uint,ctypes.c_size_t,ctypes.c_ssize_t)
received=[]
@callback_type
def callback(hwnd,msg,wparam,lparam):
    if msg in (0x201,0x202):received.append(msg)
    return user32.DefWindowProcW(hwnd,msg,wparam,lparam)

original=QPoint(__import__('PySide6.QtGui',fromlist=['QCursor']).QCursor.pos())
window=None
def pump(seconds=.2):
    until=time.monotonic()+seconds
    while time.monotonic()<until:app.processEvents();time.sleep(.01)

try:
    pump();o.display_timer.stop();t.move(10,10)
    window=user32.CreateWindowExW(0,'STATIC','SR Inqly passive input verification',0x10000000|0x00CF0000,
                                650,300,350,250,None,None,None,None)
    assert window
    user32.SetWindowLongPtrW(window,-4,ctypes.cast(callback,ctypes.c_void_p))
    user32.SetForegroundWindow(window);pump()
    t.desktop_neon_check.setChecked(True);assert o.desktop_neon and t.desktop_pen.enabled and o.click_through
    user32.SetCursorPos(730,420);pump()
    user32.mouse_event(0x2,0,0,0,0);pump()
    for x in range(750,861,20):user32.SetCursorPos(x,420);pump(.04)
    user32.mouse_event(0x4,0,0,0,0);pump()
    assert 0x201 in received and 0x202 in received,received
    assert o.trails.trails and len(o.trails.trails[-1].points)>1
    assert o.trails.trails[-1].neon
    t.desktop_neon_check.setChecked(False);assert not t.desktop_pen.enabled
    print('PASS: underlying native window receives down/up; raw mouse draws neon while overlay stays click-through; clean unregister')
finally:
    user32.mouse_event(0x4,0,0,0,0)
    if hasattr(t,'desktop_pen'):t.desktop_pen.disable()
    if window:user32.DestroyWindow(window)
    user32.SetCursorPos(original.x(),original.y())
    t.close()
