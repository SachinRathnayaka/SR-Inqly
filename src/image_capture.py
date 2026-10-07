"""Non-destructive captured image objects, transforms and contextual editing."""
from copy import deepcopy
from uuid import uuid4
import math
from PySide6.QtCore import Qt, QRectF, QPointF, QPoint, QTimer
from PySide6.QtGui import QImage, QPainter, QPainterPath, QTransform, QColor, QPen, QGuiApplication
from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QApplication, QDialog, QDialogButtonBox, QLabel
from document_model import Mark
from icons import icon


class ImageStore:
    def __init__(self):
        self.images={}
        self.budget=128*1024*1024
    def add(self,image,document=None):
        if image.isNull():raise ValueError('Screen capture returned no pixels')
        while document is not None and sum(im.sizeInBytes() for im in self.images.values())+image.sizeInBytes()>self.budget and (document._undo or document._redo):
            (document._undo if document._undo else document._redo).pop(0)
            document._trim_history();self.collect(document)
        if sum(im.sizeInBytes() for im in self.images.values())+image.sizeInBytes()>self.budget:
            raise ValueError('Capture memory limit reached. Clear unneeded images/history before capturing more.')
        key=uuid4().hex;self.images[key]=image.copy();return key
    def collect(self,document):
        used={m.image_id for m in document.marks+document.clipboard if m.image_id}|set(document._image_refs.values())
        self.images={key:value for key,value in self.images.items() if key in used}

IMAGES=ImageStore()


def transform(mark):
    w,h=mark.image_size;x,y=mark.points[0]
    t=QTransform();t.translate(x+w/2,y+h/2);t.rotate(mark.rotation)
    return t


def image_path(mark):
    w,h=mark.image_size;p=QPainterPath();p.addRect(QRectF(-w/2,-h/2,w,h))
    return transform(mark).map(p)


def draw_image(painter,mark):
    source=IMAGES.images.get(mark.image_id)
    if source is None:return
    w,h=mark.image_size;l,t,r,b=mark.crop
    painter.save();painter.setRenderHint(QPainter.SmoothPixmapTransform)
    painter.setWorldTransform(transform(mark),True)
    painter.scale(-1 if mark.flip_x else 1,-1 if mark.flip_y else 1)
    painter.drawImage(QRectF(-w/2,-h/2,w,h),source,QRectF(l*source.width(),t*source.height(),(r-l)*source.width(),(b-t)*source.height()))
    painter.restore()


def clipboard_image(mark):
    bounds=image_path(mark).boundingRect();source=IMAGES.images[mark.image_id]
    l,t,r,b=mark.crop
    scale=max(1,min(4,source.width()*(r-l)/max(1,mark.image_size[0])))
    width,height=math.ceil(bounds.width()*scale),math.ceil(bounds.height()*scale)
    if width*height>32_000_000:raise ValueError('Transformed clipboard image is too large')
    image=QImage(width,height,QImage.Format_ARGB32_Premultiplied);image.fill(Qt.transparent)
    p=QPainter(image);p.scale(scale,scale);p.translate(-bounds.topLeft());draw_image(p,mark);p.end()
    return image


def capture_region(local_rect,overlay_origin):
    """Composite intersecting screens in logical space at the highest source DPR."""
    global_rect=QRectF(local_rect).translated(overlay_origin)
    screens=[s for s in QGuiApplication.screens() if QRectF(s.geometry()).intersects(global_rect)]
    if not screens:raise ValueError('Selection does not intersect a display')
    scale=max(s.devicePixelRatio() for s in screens)
    width,height=math.ceil(global_rect.width()*scale),math.ceil(global_rect.height()*scale)
    if width*height>32_000_000:raise ValueError('Capture too large; select a smaller region')
    image=QImage(width,height,QImage.Format_ARGB32_Premultiplied);image.fill(Qt.transparent)
    p=QPainter(image)
    try:
        for screen in screens:
            geometry=QRectF(screen.geometry());part=geometry.intersected(global_rect)
            shot=screen.grabWindow(0).toImage()
            if shot.isNull():raise ValueError('Windows did not provide screen pixels')
            sx,sy=shot.width()/geometry.width(),shot.height()/geometry.height()
            source=QRectF((part.x()-geometry.x())*sx,(part.y()-geometry.y())*sy,part.width()*sx,part.height()*sy)
            dest=QRectF((part.x()-global_rect.x())*scale,(part.y()-global_rect.y())*scale,part.width()*scale,part.height()*scale)
            p.drawImage(dest,shot,source)
    finally:p.end()
    return image


class CropCanvas(QWidget):
    def __init__(self,image,crop):
        super().__init__();self.image=image;self.crop=QRectF(crop[0],crop[1],crop[2]-crop[0],crop[3]-crop[1]);self.drag=None
        self.setMinimumSize(500,330)
    def box(self):
        size=self.image.size().scaled(self.size(),Qt.KeepAspectRatio)
        return QRectF((self.width()-size.width())/2,(self.height()-size.height())/2,size.width(),size.height())
    def paintEvent(self,e):
        p=QPainter(self);p.fillRect(self.rect(),QColor('#161d2c'));r=self.box();p.drawImage(r,self.image)
        c=QRectF(r.x()+self.crop.x()*r.width(),r.y()+self.crop.y()*r.height(),self.crop.width()*r.width(),self.crop.height()*r.height())
        p.setPen(QPen(QColor('#00cfff'),2,Qt.DashLine));p.drawRect(c)
        p.setBrush(QColor('#00cfff'))
        for point in (c.topLeft(),c.topRight(),c.bottomLeft(),c.bottomRight(),QPointF(c.center().x(),c.top()),QPointF(c.center().x(),c.bottom()),QPointF(c.left(),c.center().y()),QPointF(c.right(),c.center().y())):p.drawEllipse(point,5,5)
    def mousePressEvent(self,e):
        r=self.box();point=QPointF((e.position().x()-r.x())/r.width(),(e.position().y()-r.y())/r.height())
        distances={'left':abs(point.x()-self.crop.left())*r.width(),'right':abs(point.x()-self.crop.right())*r.width(),'top':abs(point.y()-self.crop.top())*r.height(),'bottom':abs(point.y()-self.crop.bottom())*r.height()}
        edges=[key for key,value in distances.items() if value<12]
        self.drag=(edges or ['new'],point)
    def mouseMoveEvent(self,e):
        if not self.drag:return
        r=self.box();x=max(0,min(1,(e.position().x()-r.x())/r.width()));y=max(0,min(1,(e.position().y()-r.y())/r.height()))
        edges,start=self.drag
        if edges==['new']:self.crop=QRectF(start,QPointF(x,y)).normalized().intersected(QRectF(0,0,1,1))
        else:
            if 'left' in edges:self.crop.setLeft(min(x,self.crop.right()-.01))
            if 'right' in edges:self.crop.setRight(max(x,self.crop.left()+.01))
            if 'top' in edges:self.crop.setTop(min(y,self.crop.bottom()-.01))
            if 'bottom' in edges:self.crop.setBottom(max(y,self.crop.top()+.01))
        self.update()
    def mouseReleaseEvent(self,e):self.drag=None


class Fetcher:
    def __init__(self,overlay):
        self.o=overlay;self.drag=None;self.start=None;self.selection=None;self.busy=False
        self.bar=QWidget(overlay);self.bar.setObjectName('fetcherContext')
        self.bar.setStyleSheet('QWidget#fetcherContext {background:#172437;border:1px solid #547090;border-radius:6px;} QPushButton {background:#283e58;border:0;border-radius:4px;padding:4px;} QPushButton:hover {background:#426588;}')
        layout=QVBoxLayout(self.bar);layout.setContentsMargins(4,4,4,4);layout.setSpacing(3)
        self.buttons={}
        self.bar.setCursor(Qt.ArrowCursor)
        row=QHBoxLayout();row.setSpacing(3)
        actions=(
            ('crop','Crop','Re-crop',self.crop),
            ('rotate_right','Rotate','Rotate 90 degrees per click  /  Shift: reverse  /  Ctrl: reset orientation',self.rotate_click),
            ('flip_h','Flip horizontal','Flip horizontal  /  click again to restore',lambda:self.flip('flip_x')),
            ('flip_v','Flip vertical','Flip vertical  /  click again to restore',lambda:self.flip('flip_y')),
            ('copy','Copy','Copy image  /  Shift+click: duplicate  /  Ctrl+D: duplicate',self.copy_click),
            ('up','Forward','One layer forward  /  Shift+click: bring to front',lambda:self.layer_click(1)),
            ('down','Backward','One layer backward  /  Shift+click: send to back',lambda:self.layer_click(-1)),
            ('delete','Delete','Delete selected image',overlay.delete_selected))
        for name,label,tip,callback in actions:
            button=QPushButton();button.setIcon(icon(name));button.setFixedSize(32,34)
            button.setToolTip(tip);button.setAccessibleName(label);button.setFocusPolicy(Qt.NoFocus)
            button.clicked.connect(callback);row.addWidget(button);self.buttons[label]=button
        layout.addLayout(row)
        self.bar.adjustSize();self.bar.hide();overlay.changed.connect(self.refresh)
    def rotate_click(self):
        modifiers=QApplication.keyboardModifiers()
        if modifiers & Qt.ControlModifier:
            self.edit(rotation=0,flip_x=False,flip_y=False)
        else:
            self.edit(rotation=-90 if modifiers & Qt.ShiftModifier else 90,relative=True)
    def copy_click(self):
        if QApplication.keyboardModifiers() & Qt.ShiftModifier:self.o.duplicate()
        else:self.copy()
    def layer_click(self,direction):
        self.layer(direction*(99999 if QApplication.keyboardModifiers() & Qt.ShiftModifier else 1))
    def selected(self):
        if len(self.o.selected)==1:
            index=next(iter(self.o.selected))
            if 0<=index<len(self.o.document.marks) and self.o.document.marks[index].kind=='image':return index,self.o.document.marks[index]
        return None,None
    def refresh(self,collect=True,repaint=True):
        if collect:IMAGES.collect(self.o.document)
        index,mark=self.selected()
        show=mark is not None and not self.o.click_through and self.o.tool=='select'
        self.bar.setVisible(show)
        if show:
            r=image_path(mark).boundingRect();x=max(0,min(round(r.x()),self.o.rect().width()-self.bar.width()));y=round(r.top()-self.bar.height()-12)
            if y<0:y=min(self.o.height()-self.bar.height(),round(r.bottom()+12))
            from PySide6.QtGui import QRegion
            for cy in (y,round(r.bottom()+12),self.o.height()-self.bar.height()-8):
                rect=QRectF(x,max(0,cy),self.bar.width(),self.bar.height()).toRect()
                if QRegion(rect).subtracted(self.o.mask()).isEmpty():y=max(0,cy);break
            self.bar.move(x,y);self.bar.raise_()
        if repaint:self.o.update()
    def edit(self,relative=False,**values):
        index,mark=self.selected()
        if mark is None:return
        new=deepcopy(mark)
        for key,value in values.items():setattr(new,key,(getattr(new,key)+value)%360 if relative else value)
        self.o.document.checkpoint();self.o.document.marks[index]=new;self.o.changed.emit()
    def flip(self,key):
        _,mark=self.selected()
        if mark:self.edit(**{key:not getattr(mark,key)})
    def layer(self,amount):
        index,mark=self.selected()
        if mark is None:return
        target=max(0,min(len(self.o.document.marks)-1,index+amount))
        if target==index:return
        self.o.document.checkpoint();self.o.document.marks.pop(index);self.o.document.marks.insert(target,mark);self.o.selected={target};self.o.changed.emit()
    def copy(self):
        _,mark=self.selected()
        if mark:
            try:QApplication.clipboard().setImage(clipboard_image(mark));self.o.message.emit('Image copied to clipboard')
            except Exception as error:self.o.message.emit(str(error))
    def crop(self):
        index,mark=self.selected()
        if mark is None:return
        self.o.set_click_through(True)
        dialog=QDialog(self.o);dialog.setWindowTitle('Re-crop  /  SR Inqly');layout=QVBoxLayout(dialog)
        layout.addWidget(QLabel('Drag an edge/handle, or draw a crop rectangle. Original pixels remain available.'))
        canvas=CropCanvas(IMAGES.images[mark.image_id],mark.crop);layout.addWidget(canvas)
        reset=QPushButton('Restore full image');reset.clicked.connect(lambda:(setattr(canvas,'crop',QRectF(0,0,1,1)),canvas.update()));layout.addWidget(reset)
        buttons=QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel);buttons.accepted.connect(dialog.accept);buttons.rejected.connect(dialog.reject);layout.addWidget(buttons)
        if dialog.exec()==QDialog.Accepted and canvas.crop.width()>.005 and canvas.crop.height()>.005:
            self.o.selected={index};c=canvas.crop;self.edit(crop=(c.left(),c.top(),c.right(),c.bottom()))
        self.o.set_click_through(False);self.o.selected={index};self.o.changed.emit()
        dialog.deleteLater()
    def handles(self,mark):
        w,h=mark.image_size;t=transform(mark)
        return [t.map(p) for p in (QPointF(-w/2,-h/2),QPointF(w/2,-h/2),QPointF(w/2,h/2),QPointF(-w/2,h/2),QPointF(0,-h/2-28))]
    def paint(self,p):
        if self.selection is not None:
            p.setPen(QPen(QColor('#00cfff'),2,Qt.DashLine));p.setBrush(QColor(0,160,255,30));p.drawRect(self.selection)
        _,mark=self.selected()
        if mark and self.o.tool=='select' and not self.o.click_through:
            p.setPen(QPen(QColor('#00cfff'),1.5));p.setBrush(Qt.NoBrush);p.drawPath(image_path(mark));p.setBrush(QColor('white'))
            handles=self.handles(mark)
            p.drawLine(transform(mark).map(QPointF(0,-mark.image_size[1]/2)),handles[-1])
            for point in handles:p.drawEllipse(point,5,5)
    def press(self,event):
        if self.busy:return True
        point=event.position()
        if self.o.tool=='fetcher':self.start=point;self.selection=QRectF(point,point);return True
        index,mark=self.selected()
        if mark and self.o.tool=='select':
            for i,handle in enumerate(self.handles(mark)):
                if (handle-point).manhattanLength()<16:
                    self.drag=(index,deepcopy(mark),i,False);return True
        return False
    def move(self,event):
        point=event.position()
        if self.start is not None:
            old=QRectF(self.selection) if self.selection is not None else QRectF(self.start,self.start)
            self.selection=QRectF(self.start,point).normalized()
            self.o.update(old.united(self.selection).adjusted(-3,-3,3,3).toAlignedRect())
            return True
        if not self.drag:return False
        index,original,handle,checkpoint=self.drag
        dirty=image_path(self.o.document.marks[index]).boundingRect().united(QRectF(self.bar.geometry()))
        if not checkpoint:self.o.document.checkpoint();self.drag=(index,original,handle,True)
        new=deepcopy(original);w,h=original.image_size;center=transform(original).map(QPointF())
        if handle==4:new.rotation=(math.degrees(math.atan2(point.y()-center.y(),point.x()-center.x()))+90)%360
        else:
            fixed=self.handles(original)[(handle+2)%4]
            rotation=QTransform().rotate(-original.rotation);v=rotation.map(point-fixed)
            sx=-1 if handle in (0,3) else 1;sy=-1 if handle in (0,1) else 1
            nw=max(24,v.x()*sx);nh=max(24,v.y()*sy)
            if not event.modifiers()&Qt.ShiftModifier:
                factor=max(nw/w,nh/h);nw=w*factor;nh=h*factor
            nw=min(nw,16384);nh=min(nh,16384)
            center=fixed+QTransform().rotate(original.rotation).map(QPointF(sx*nw/2,sy*nh/2))
            new.image_size=(nw,nh);new.points=[(center.x()-nw/2,center.y()-nh/2)]
        self.o.document.marks[index]=new;self.refresh(False,False)
        dirty=dirty.united(image_path(new).boundingRect()).united(QRectF(self.bar.geometry())).adjusted(-40,-40,40,40)
        self.o.update(dirty.toAlignedRect());return True
    def release(self,event):
        if self.drag:self.drag=None;self.o.changed.emit();return True
        if self.start is not None:
            rect=QRectF(self.start,event.position()).normalized().intersected(QRectF(self.o.rect()));self.start=None;self.selection=None
            if rect.width()>=3 and rect.height()>=3:self.capture(rect)
            else:self.o.set_tool('select')
            self.o.update();return True
        return False
    def cancel(self):
        self.start=None;self.selection=None;self.drag=None;self.bar.hide()
    def capture(self,rect):
        self.busy=True
        windows=[child for child in self.o.findChildren(QWidget,options=Qt.FindDirectChildrenOnly) if child.isWindow() and child.isVisible()]
        for window in windows:window.hide()
        self.o.hide()
        def finish():
            try:
                image=capture_region(rect,self.o.pos());key=IMAGES.add(image,self.o.document)
                self.o.document.checkpoint();self.o.document.marks.append(Mark('image',[(rect.x(),rect.y())],image_id=key,image_size=(rect.width(),rect.height())))
                self.o.selection_mode='smart';self.o.selection_operation='replace'
                self.o.set_tool('select');self.o.selected={len(self.o.document.marks)-1}
            except Exception as error:self.o.message.emit('Capture failed: '+str(error));self.o.set_click_through(True)
            finally:
                self.busy=False;self.o.show()
                for window in windows:window.show()
                self.o.changed.emit();self.o.update()
        # Yield to DWM without blocking the input/UI thread.
        QTimer.singleShot(150,self.o,finish)
