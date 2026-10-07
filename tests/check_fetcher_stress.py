import json,time
from PySide6.QtGui import QImage,QColor
from document_model import Document,Mark
from image_capture import IMAGES
from performance_diagnostics import memory
d=Document();samples=[];start=time.perf_counter()
for i in range(240):
 image=QImage(640,480,QImage.Format_ARGB32);image.fill(QColor.fromHsv(i%360,200,200))
 key=IMAGES.add(image,d);d.checkpoint();d.marks.append(Mark('image',[(0,0)],image_id=key,image_size=(640,480)))
 d.delete(0);IMAGES.collect(d)
 if i%20==0:samples.append({'cycle':i,'assets':len(IMAGES.images),'asset_bytes':sum(x.sizeInBytes() for x in IMAGES.images.values()),**memory()})
 assert len(IMAGES.images)<=51
 assert sum(x.sizeInBytes() for x in IMAGES.images.values())<=IMAGES.budget
 if i%15==0:assert d.undo();assert d.marks;assert d.redo();assert not d.marks
retained=len(IMAGES.images);d._undo.clear();d._redo.clear();d._trim_history();IMAGES.collect(d);assert not IMAGES.images
result={'cycles':240,'seconds':time.perf_counter()-start,'samples':samples,'retained_for_undo_before_history_clear':retained,'assets_after_history_clear':len(IMAGES.images)}
open('performance-fetcher.json','w').write(json.dumps(result,indent=2))
print(json.dumps(result))
