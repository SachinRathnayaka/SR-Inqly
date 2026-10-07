"""Bounded temporary pen trails; no document snapshots or idle polling."""
from dataclasses import dataclass, field
import math
import time
from PySide6.QtCore import QObject, QTimer, QRectF, QPointF, Qt
from PySide6.QtGui import QColor, QPen, QPainterPath, QLinearGradient


def paint_path(painter, path, color, width, opacity=1.0, neon=False):
    painter.save()
    painter.setBrush(Qt.NoBrush)
    if neon:
        for extra, alpha in ((14, .07), (8, .13), (4, .23)):
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
    fade: float = .9

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
        previous = self.active.points[-1] if self.active.points else point
        self.active.points.append((x,y))
        self.active.times.append(self.clock())
        margin = self.active.width + (18 if self.active.neon else 4)
        dirty = QRectF(QPointF(*previous),QPointF(x,y)).normalized().adjusted(-margin,-margin,margin,margin)
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
        self.timer.start(16 if earliest<=now else max(1,math.ceil((earliest-now)*1000)))

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
                path=QPainterPath(QPointF(*trail.points[0]))
                for point in trail.points[1:]:path.lineTo(*point)
                if len(trail.points)==1:path.lineTo(trail.points[0][0]+.01,trail.points[0][1])
                paint_path(painter,path,trail.color,trail.width,trail.opacity,trail.neon)
                continue
            groups=[];group=None;bucket=None
            for i in range(max(1,len(trail.points)-1)):
                a=QPointF(*trail.points[i]);b=QPointF(*trail.points[min(i+1,len(trail.points)-1)])
                alpha_a=alphas[i];alpha_b=alphas[min(i+1,len(alphas)-1)]
                if max(alpha_a,alpha_b)<=0:continue
                key=round((alpha_a+alpha_b)*32)
                if group is None or key!=bucket:
                    group=[QPainterPath(a),a,b,alpha_a,alpha_b]
                    groups.append(group);bucket=key
                group[0].lineTo(b if a!=b else QPointF(a.x()+.01,a.y()))
                group[2]=b;group[4]=alpha_b
            # Join near-equal-age segments into continuous paths. Painting each
            # sampled segment separately makes round caps accumulate opacity
            # and prevents dense strokes from fading evenly.
            for path,a,b,alpha_a,alpha_b in groups:
                painter.save();painter.setOpacity(trail.opacity)
                layers=((trail.width+14,.07,trail.color),(trail.width+8,.13,trail.color),(trail.width+4,.23,trail.color)) if trail.neon else ()
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
