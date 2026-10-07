"""Bounded background PNG encoding; GUI completion is delivered by Qt."""
from PySide6.QtCore import QObject,QRunnable,QThreadPool,Signal,Qt

class Result(QObject):
    finished=Signal(str,bool,str)

class Job(QRunnable):
    def __init__(self,image,path,result):
        super().__init__();self.image=image;self.path=path;self.result=result
    def run(self):
        try:
            ok=self.image.save(self.path,'PNG')
            error='' if ok else 'Could not save '+self.path
        except Exception as exc:ok=False;error=str(exc)
        self.result.finished.emit(self.path,ok,error)

class PngWriter(QObject):
    def __init__(self,parent):
        super().__init__(parent);self.pool=QThreadPool(self);self.pool.setMaxThreadCount(1)
        self.result=Result(self);self.result.finished.connect(self.complete,Qt.QueuedConnection)
        self.pending={};self.sizes={}
    def submit(self,image,path,callback):
        if len(self.pending)>=2:raise RuntimeError('Screenshot saving is busy; try again shortly')
        if path in self.pending:raise RuntimeError('This screenshot is already being saved')
        if image.isNull():raise ValueError('Capture produced no pixels')
        size=image.sizeInBytes()
        if sum(self.sizes.values())+size>128*1024*1024:raise RuntimeError('Screenshot memory budget is busy; try again shortly')
        self.sizes[path]=size
        # QImage's shared pixel data is immutable for this job.
        self.pending[path]=callback;self.pool.start(Job(image,path,self.result))
    def complete(self,path,ok,error):
        self.sizes.pop(path,None)
        callback=self.pending.pop(path,None)
        if callback:callback(path,ok,error)
