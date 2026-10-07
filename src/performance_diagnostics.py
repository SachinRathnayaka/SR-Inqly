"""Reproducible benchmark, also callable inside the shipped frozen executable."""
import json,time,statistics,ctypes,sys,platform
from pathlib import Path
from ctypes import wintypes
from PySide6.QtCore import Qt,QRectF
from PySide6.QtGui import QImage,QPainter,QGuiApplication
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
from document_model import Document,Mark
from render_cache import RenderCache,SceneCache

def memory():
 class Counters(ctypes.Structure):
  _fields_=[('cb',wintypes.DWORD),('PageFaultCount',wintypes.DWORD)]+[(name,ctypes.c_size_t) for name in ('PeakWorkingSetSize','WorkingSetSize','QuotaPeakPagedPoolUsage','QuotaPagedPoolUsage','QuotaPeakNonPagedPoolUsage','QuotaNonPagedPoolUsage','PagefileUsage','PeakPagefileUsage','PrivateUsage')]
 c=Counters();c.cb=ctypes.sizeof(c)
 fn=ctypes.windll.psapi.GetProcessMemoryInfo
 fn.argtypes=[wintypes.HANDLE,ctypes.POINTER(Counters),wintypes.DWORD]
 fn.restype=wintypes.BOOL
 if not fn(wintypes.HANDLE(-1),ctypes.byref(c),c.cb):raise ctypes.WinError()
 return {'working_set':c.WorkingSetSize,'private_bytes':c.PrivateUsage}

def run(draw_mark,Overlay,Toolbar,output,seconds=120):
 app=QApplication.instance() or QApplication([])
 doc=Document();overlay=Overlay(doc);overlay.show();overlay.set_click_through(True)
 toolbar=Toolbar(overlay);toolbar.show();app.processEvents()
 result={'scene_raster_cache':True,'antialiasing':True,'frozen':bool(getattr(sys,'frozen',False)),'python':platform.python_version(),
         'displays':[{'width':s.geometry().width(),'height':s.geometry().height(),'dpr':s.devicePixelRatio(),'hz':s.refreshRate()} for s in app.screens()]}
 cpu=time.process_time();wall=time.perf_counter();QTest.qWait(12000)
 result['idle_seconds']=time.perf_counter()-wall
 result['idle_one_core_cpu_percent']=100*(time.process_time()-cpu)/result['idle_seconds']
 overlay.hide();toolbar.hide()
 marks=[Mark('pen',[(float((i%40)*45+j%30),float((i//40)*30+j%23)) for j in range(100)]) for i in range(1000)]
 doc.marks=marks;times=[]
 for _ in range(15):
  start=time.perf_counter();doc.checkpoint();times.append((time.perf_counter()-start)*1000)
 result['checkpoint_median_ms_no_tracemalloc']=statistics.median(times)
 cache=RenderCache(draw_mark);scene=SceneCache(cache);image=QImage(1920,1080,QImage.Format_ARGB32_Premultiplied)
 def paint(region):
  image.fill(Qt.transparent);p=QPainter(image);p.setRenderHint(QPainter.Antialiasing);p.setClipRect(region.toAlignedRect())
  start=time.perf_counter();scene.paint(p,doc.marks,region,image.size());elapsed=(time.perf_counter()-start)*1000;p.end();return elapsed
 result['cold_full_paint_ms']=paint(QRectF(image.rect()))
 values=[paint(QRectF(300,300,80,80)) for _ in range(100)]
 result['warm_region_median_ms']=statistics.median(values);result['warm_region_p95_ms']=sorted(values)[94]
 result['warm_full_median_ms']=statistics.median(paint(QRectF(image.rect())) for _ in range(20))
 samples=[];cycles=0;start=time.perf_counter();next_sample=0
 while time.perf_counter()-start<seconds:
  doc.checkpoint();doc.marks=marks+[Mark('line',[(10,10),(100+cycles%100,100)])]
  doc.delete_many(range(0,len(doc.marks),5));doc.undo();doc.redo();doc.clear();doc.undo()
  paint(QRectF(300,300,80,80));cycles+=1
  if time.perf_counter()-start>=next_sample:
   samples.append({'seconds':round(time.perf_counter()-start,2),**memory(),'history_bytes':doc.history_bytes,'cache_bytes':cache.bytes})
   next_sample+=10
  app.processEvents();QTest.qWait(5)
 result.update(stress_seconds=time.perf_counter()-start,stress_cycles=cycles,memory_samples=samples,history_states=len(doc._undo),history_bytes=doc.history_bytes,cache_bytes=cache.bytes)
 Path(output).write_text(json.dumps(result,indent=2),encoding='utf-8')
 toolbar.close();return 0
