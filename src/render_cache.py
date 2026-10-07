"""Bounded compiled drawing cache for committed, replace-on-edit marks."""
from collections import OrderedDict
from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QPainter, QPicture, QPainterPath, QPen, QColor, QImage


class StrokeCommand:
    def __init__(self,mark):
        self.path=QPainterPath()
        self.path.moveTo(*mark.points[0])
        for point in mark.points[1:]:self.path.lineTo(*point)
        color=QColor(mark.color)
        if mark.kind=='highlight':color.setAlpha(105)
        self.pen=QPen(color,mark.width,Qt.SolidLine,Qt.SquareCap if mark.kind=='highlight' else Qt.RoundCap,Qt.RoundJoin)
        self.opacity=mark.opacity
        self.neon=getattr(mark,'neon',False) and mark.kind=='pen'
    def size(self):return self.path.elementCount()*24+256
    def boundingRect(self):
        margin=self.pen.widthF()+2+(18 if self.neon else 0)
        return self.path.boundingRect().adjusted(-margin,-margin,margin,margin)
    def paint(self,painter):
        if self.neon:
            from pen_effects import paint_path
            paint_path(painter,self.path,self.pen.color().name(),self.pen.widthF(),self.opacity,True)
            return
        painter.save();painter.setOpacity(self.opacity);painter.setPen(self.pen);painter.setBrush(Qt.NoBrush);painter.drawPath(self.path);painter.restore()


class RenderCache:
    def __init__(self, draw):
        self.draw = draw
        self.entries = OrderedDict()
        self.bytes = 0
        self.budget = 16 * 1024 * 1024

    def get(self, mark):
        key = id(mark)
        if key in self.entries:
            self.entries.move_to_end(key)
            return self.entries[key]
        if mark.kind in ('pen','highlight') and len(mark.points)>=2:
            picture=StrokeCommand(mark)
        else:
            picture = QPicture()
            painter = QPainter(picture)
            self.draw(painter, mark)
            painter.end()
        if mark.kind == 'text':
            # QTextDocument records glyph runs whose QPicture bounds can be
            # empty. Use layout bounds so hiding/moving clears the old text.
            from text_editor import text_bounds
            bounds = text_bounds(mark).adjusted(-4,-4,4,4)
        else:
            bounds = QRectF(picture.boundingRect()).adjusted(-2,-2,2,2)
        record = (mark, picture, bounds)
        size = picture.size()
        # Bound both command bytes and retained Python point objects.
        cost = size + len(mark.points)*128 + 1024
        while self.entries and (self.bytes + cost > self.budget or len(self.entries) >= 2048):
            _, old = self.entries.popitem(last=False)
            self.bytes -= old[1].size()+len(old[0].points)*128+1024
        if cost <= self.budget:
            self.entries[key] = record
            self.bytes += cost
        return record

    def paint(self, painter, marks, region, skip=None, records=None):
        drawn = 0
        for index, mark in enumerate(marks):
            if index == skip:
                continue
            # Scene bounds survive command eviction. Cull before recompiling
            # commands, especially when a dense document exceeds the budget.
            if records is not None and not records[id(mark)][1].intersects(region):
                continue
            if mark.kind == 'image':
                from image_capture import image_path
                if image_path(mark).boundingRect().intersects(region):
                    self.draw(painter,mark)
                continue
            _, picture, bounds = self.get(mark)
            if bounds.intersects(region):
                if isinstance(picture,StrokeCommand):picture.paint(painter)
                else:painter.drawPicture(0,0,picture)
                drawn += 1
        return drawn

    def clear(self):
        self.entries.clear()
        self.bytes = 0


class SceneCache:
    """One bounded raster layer, updated only where committed objects changed."""
    def __init__(self,commands):
        self.commands=commands;self.image=None;self.state=();self.records={};self.budget=64*1024*1024
    def paint(self,painter,marks,region,size,dpr=1,skip=None):
        width,height=max(1,round(size.width()*dpr)),max(1,round(size.height()*dpr))
        if width*height*4>self.budget:
            self.image=None;self.state=();self.records={}
            return self.commands.paint(painter,marks,region,skip)
        visible=[m for i,m in enumerate(marks) if i!=skip]
        state=tuple(id(m) for m in visible)
        fresh=self.image is None or self.image.width()!=width or self.image.height()!=height or self.image.devicePixelRatio()!=dpr
        dirty=QRectF()
        if fresh:
            self.image=QImage(width,height,QImage.Format_ARGB32_Premultiplied);self.image.setDevicePixelRatio(dpr);self.image.fill(Qt.transparent)
            dirty=QRectF(0,0,size.width(),size.height())
        if state!=self.state or fresh:
            old_ids=set(self.state);new_ids=set(state);common=old_ids&new_ids
            reordered=tuple(i for i in self.state if i in common)!=tuple(i for i in state if i in common)
            records={}
            for mark in visible:
                key=id(mark)
                if key in self.records:records[key]=self.records[key]
                elif mark.kind=='image':
                    from image_capture import image_path
                    records[key]=(mark,image_path(mark).boundingRect().adjusted(-2,-2,2,2))
                else:records[key]=(mark,self.commands.get(mark)[2])
                if reordered or key not in old_ids:dirty=dirty.united(records[key][1])
            for key,(_,bounds) in self.records.items():
                if reordered or key not in new_ids:dirty=dirty.united(bounds)
            text_changed=any(mark.kind=='text' and (reordered or key not in old_ids)
                             for key,(mark,_) in records.items()) or any(
                             mark.kind=='text' and (reordered or key not in new_ids)
                             for key,(mark,_) in self.records.items())
            if text_changed:
                # A text edit changes glyph layout/clipping. Rebuild the scene
                # once on commit/hide to avoid stale glyphs and clipped AA seams.
                dirty=QRectF(0,0,size.width(),size.height())
            self.records=records;self.state=state
            if not dirty.isEmpty():
                dirty=dirty.adjusted(-2,-2,2,2).intersected(QRectF(0,0,size.width(),size.height()))
                layer=QPainter(self.image);layer.setClipRect(dirty.toAlignedRect());layer.setCompositionMode(QPainter.CompositionMode_Source)
                layer.fillRect(dirty.toAlignedRect(),Qt.transparent);layer.setCompositionMode(QPainter.CompositionMode_SourceOver);layer.setRenderHint(QPainter.Antialiasing)
                self.commands.paint(layer,visible,dirty,records=self.records)
                layer.end()
        painter.drawImage(0,0,self.image)
