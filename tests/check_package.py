"""Smoke-test the shipped EXE, including native input release and clean exit."""

import ctypes
from ctypes import wintypes as W
from pathlib import Path
import subprocess
import time
import json
import os


class Point(ctypes.Structure):
    _fields_ = [("x", W.LONG), ("y", W.LONG)]


class Rect(ctypes.Structure):
    _fields_ = [("l", W.LONG), ("t", W.LONG), ("r", W.LONG), ("b", W.LONG)]


def run():
    root = Path(os.environ.get("SR_INQLY_TEST_ROOT", str(Path(__file__).resolve().parent.parent / "dist" / "SR Inqly")))
    assert (root / "_internal/PySide6/QtSvg.pyd").exists()
    assert not (root / "_internal/icuuc.dll").exists()
    user32 = ctypes.windll.user32
    user32.WindowFromPoint.argtypes = [Point]
    user32.WindowFromPoint.restype = W.HWND
    start_time = time.perf_counter()
    process = subprocess.Popen([str(root / "SR Inqly.exe")])
    found = []
    callback_type = ctypes.WINFUNCTYPE(W.BOOL, W.HWND, W.LPARAM)

    def visit(hwnd, _):
        pid = W.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value == process.pid and user32.IsWindowVisible(hwnd):
            title = ctypes.create_unicode_buffer(200)
            user32.GetWindowTextW(hwnd, title, 200)
            if title.value == "SR Inqly":
                rect = Rect()
                user32.GetWindowRect(hwnd, ctypes.byref(rect))
                found.append((int(hwnd), rect))
        return True

    callback = callback_type(visit)
    try:
        for _ in range(60):
            found.clear()
            user32.EnumWindows(callback, 0)
            if len(found) == 2:
                break
            time.sleep(0.1)
        assert len(found) == 2, "Packaged toolbar / overlay did not open"
        startup_seconds = time.perf_counter()-start_time
        def cpu_time():
            creation, exit_time, kernel, user = W.FILETIME(), W.FILETIME(), W.FILETIME(), W.FILETIME()
            fn = ctypes.windll.kernel32.GetProcessTimes
            fn.argtypes = [W.HANDLE] + [ctypes.POINTER(W.FILETIME)]*4
            assert fn(W.HANDLE(int(process._handle)),ctypes.byref(creation),ctypes.byref(exit_time),ctypes.byref(kernel),ctypes.byref(user))
            return sum((v.dwHighDateTime<<32)+v.dwLowDateTime for v in (kernel,user))/1e7
        before_cpu = cpu_time()
        before_wall = time.perf_counter()
        time.sleep(12)
        idle = 100*(cpu_time()-before_cpu)/(time.perf_counter()-before_wall)
        report_dir = Path(__file__).resolve().parent.parent / 'build' / 'test-artifacts'
        report_dir.mkdir(parents=True, exist_ok=True)
        (report_dir / 'performance-startup-idle.json').write_text(json.dumps({'startup_seconds':startup_seconds,'idle_one_core_cpu_percent':idle,'idle_window_seconds':12},indent=2))
        found.sort(key=lambda item: (item[1].r-item[1].l) * (item[1].b-item[1].t))
        toolbar, toolbar_rect = found[0]
        overlay, _ = found[1]
        assert user32.GetWindowLongW(overlay, -20) & 0x20, "Must start in desktop mode"
        user32.PostMessageW(toolbar, 0x0312, 101, 0)
        time.sleep(0.15)
        assert not user32.GetWindowLongW(overlay, -20) & 0x20
        user32.SetForegroundWindow(overlay)
        time.sleep(0.1)
        assert user32.WindowFromPoint(Point(toolbar_rect.l+70, toolbar_rect.t+95)) == toolbar
        user32.PostMessageW(overlay, 0x0100, 0x1B, 0)
        user32.PostMessageW(overlay, 0x0101, 0x1B, 0)
        time.sleep(0.15)
        assert user32.GetWindowLongW(overlay, -20) & 0x20, "Escape must release input"
        user32.PostMessageW(toolbar, 0x0010, 0, 0)
        assert process.wait(timeout=5) == 0, "Normal close must exit the process"
        print("PASS packaged EXE: icon DLLs, desktop startup, toolbar reachability, Escape and clean exit")
    finally:
        if process.poll() is None:
            process.terminate()
            process.wait(timeout=5)


if __name__ == "__main__":
    run()
