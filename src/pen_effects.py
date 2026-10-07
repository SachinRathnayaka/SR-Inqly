"""Bounded temporary pen trails; no document snapshots or idle polling."""
from dataclasses import dataclass, field
import math
import time
from PySide6.QtCore import QObject, QTimer, QRectF, QPointF, Qt
from PySide6.QtGui import QColor, QPen, QPainterPath, QLinearGradient


def smooth_path(points):
    """Midpoint quadratic curves, preserving endpoints without overshooting."""
    path = QPainterPath(QPointF(*points[0]))
    if len(points) == 1:
        path.lineTo(points[0][0]+.01, points[0][1])
    elif len(points) == 2:
        path.lineTo(*points[1])
    else:
        path.lineTo((QPointF(*points[0])+QPointF(*points[1]))*.5)
        for i in range(1, len(points)-1):
            control=QPointF(*points[i]);following=QPointF(*points[i+1])
            path.quadTo(control,(control+following)*.5)
        path.lineTo(*points[-1])
    return path


GLOW_LAYERS = ((20,.015),(16,.025),(12,.045),(8,.075),(4,.13))


def paint_path(painter, path, color, width, opacity=1.0, neon=False):
    painter.save()
    painter.setBrush(Qt.NoBrush)
    if neon:
        for extra, alpha in GLOW_LAYERS:
            painter.setOpacity(opacity * alpha)
            painter.setPen(QPen(QColor(color), width + extra, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            painter.drawPath(path)
    painter.setOpacity(opacity)
    painter.setPen(QPen(QColor(color), width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    painter.drawPath(path)
    if neon:
        painter.setOpacity(opacity * .8)
        painter.setPen(QPen(QColor('#ffffff'), max(1, width * .3), Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        painter.drawPath(path)
    painter.restore()


def remaining_alpha(now, timestamp, delay, fade):
    progress = min(1.0, max(0.0, (now - timestamp - delay) / fade))
    return 1.0 - progress * progress * (3.0 - 2.0 * progress)


@dataclass
class Trail:
    color: str
    width: float
    opacity: float
    neon: bool
    delay: float
    points: list = field(default_factory=list)
    times: list = field(default_factory=list)
    fade: float = 1.8

    def bounds(self):
        if not self.points:
            return QRectF()
        xs, ys = zip(*self.points)
        margin = self.width + (18 if self.neon else 4)
        return QRectF(min(xs), min(ys), max(xs)-min(xs), max(ys)-min(ys)).adjusted(-margin,-margin,margin,margin)


class PenTrails(QObject):
    MAX_POINTS = 16384
    MAX_TRAILS = 64

    def __init__(self, overlay, clock=time.monotonic):
        super().__init__(overlay)
        self.overlay = overlay
        self.clock = clock
        self.trails = []
        self.active = None
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.setTimerType(Qt.PreciseTimer)
        self.timer.timeout.connect(self.tick)

    def begin(self, point, color, width, opacity, neon, delay):
        self.end()
        self.active = Trail(color,width,opacity,neon,delay)
        self.trails.append(self.active)
        self.append(point)
        self.limit()
        self.schedule()

    def append(self, point):
        if self.active is None:
            return
        x,y = point
        if self.active.points and math.dist(point,self.active.points[-1]) < .5:
            return
        self.active.points.append((x,y))
        self.active.times.append(self.clock())
        margin = self.active.width + (18 if self.active.neon else 4)
        xs,ys=zip(*self.active.points[-3:])
        dirty = QRectF(min(xs),min(ys),max(xs)-min(xs),max(ys)-min(ys)).adjusted(-margin,-margin,margin,margin)
        self.overlay.update(dirty.toAlignedRect())
        self.limit()
        if not self.timer.isActive():self.schedule()

    def end(self):
        self.active = None
        if self.trails:self.tick()

    def limit(self):
        while len(self.trails)>self.MAX_TRAILS or sum(len(t.points) for t in self.trails)>self.MAX_POINTS:
            if len(self.trails)>1:
                old = self.trails.pop(0)
                self.overlay.update(old.bounds().toAlignedRect())
            else:
                trail=self.trails[0]
                self.overlay.update(trail.bounds().toAlignedRect())
                del trail.points[:1024];del trail.times[:1024]

    def schedule(self):
        if not self.trails:
            self.timer.stop()
            return
        now=self.clock()
        if all(now>=t.times[-1]+t.delay+t.fade for t in self.trails if t.times):
            self.timer.stop()
            return
        earliest=min(t.times[0]+t.delay for t in self.trails if t.times)
        self.timer.start(8 if earliest<=now else max(1,math.ceil((earliest-now)*1000)))

    def tick(self):
        now=self.clock()
        kept=[]
        for trail in self.trails:
            if not trail.times:
                continue
            if now>=trail.times[0]+trail.delay:
                self.overlay.update(trail.bounds().toAlignedRect())
            # Keep one expired endpoint to interpolate the moving fade boundary.
            count=0
            while count+1<len(trail.times) and now>=trail.times[count+1]+trail.delay+trail.fade:
                count+=1
            if count:
                del trail.points[:count];del trail.times[:count]
            if now<trail.times[-1]+trail.delay+trail.fade or trail is self.active:
                kept.append(trail)
        self.trails=kept
        self.schedule()

    def clear(self):
        for trail in self.trails:
            self.overlay.update(trail.bounds().toAlignedRect())
        self.active=None;self.trails.clear();self.timer.stop()

    def undo(self):
        if not self.trails:
            return False
        trail=self.trails.pop()
        if trail is self.active:self.active=None
        self.overlay.update(trail.bounds().toAlignedRect())
        self.schedule()
        return True

    def paint(self, painter, region):
        now=self.clock()
        for trail in self.trails:
            if not trail.bounds().intersects(region):
                continue
            alphas=[remaining_alpha(now,t,trail.delay,trail.fade) for t in trail.times]
            # Full paths are cheap until their first endpoint starts fading.
            if min(alphas)==1:
                path=smooth_path(trail.points)
                paint_path(painter,path,trail.color,trail.width,trail.opacity,trail.neon)
                continue
            groups=[];group=None;bucket=None
            points=[QPointF(*p) for p in trail.points]
            for i,control in enumerate(points):
                a=points[0] if i==0 else (points[i-1]+control)*.5
                b=points[-1] if i==len(points)-1 else (control+points[i+1])*.5
                alpha_a=alphas[0] if i==0 else (alphas[i-1]+alphas[i])*.5
                alpha_b=alphas[-1] if i==len(points)-1 else (alphas[i]+alphas[i+1])*.5
                if max(alpha_a,alpha_b)<=0:continue
                key=round((alpha_a+alpha_b)*128)
                if group is None or key!=bucket:
                    group=[QPainterPath(a),a,b,alpha_a,alpha_b]
                    groups.append(group);bucket=key
                if i==0 or i==len(points)-1:
                    group[0].lineTo(b if a!=b else QPointF(a.x()+.01,a.y()))
                else:
                    group[0].quadTo(control,b)
                group[2]=b;group[4]=alpha_b
            # Join near-equal-age segments into continuous paths. Painting each
            # sampled segment separately makes round caps accumulate opacity
            # and prevents dense strokes from fading evenly.
            for path,a,b,alpha_a,alpha_b in groups:
                painter.save();painter.setOpacity(trail.opacity)
                layers=tuple((trail.width+extra,alpha,trail.color) for extra,alpha in GLOW_LAYERS) if trail.neon else ()
                layers+=((trail.width,1,trail.color),)
                if trail.neon:layers+=((max(1,trail.width*.3),.8,'#ffffff'),)
                for width,scale,color in layers:
                    gradient=QLinearGradient(a,b if a!=b else QPointF(a.x()+.01,a.y()))
                    first=QColor(color);first.setAlphaF(alpha_a*scale)
                    last=QColor(color);last.setAlphaF(alpha_b*scale)
                    gradient.setColorAt(0,first);gradient.setColorAt(1,last)
                    painter.setPen(QPen(gradient,width,Qt.SolidLine,Qt.RoundCap,Qt.RoundJoin))
                    painter.drawPath(path)
                painter.restore()
