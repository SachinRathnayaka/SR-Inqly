"""Validated local preferences; invalid settings never prevent startup."""
from PySide6.QtCore import QSettings,QPoint
from PySide6.QtGui import QColor

def settings():return QSettings('SRInqly','Preferences')

def restore(toolbar):
    s=settings();o=toolbar.overlay
    def number(key,default,low,high):
        try:return max(low,min(high,float(s.value(key,default))))
        except (TypeError,ValueError):return default
    for key,default in (('pen_color','#ff4655'),('highlighter_color','#ffcb3d')):
        value=str(s.value(key,default));setattr(o,key,value if QColor(value).isValid() else default)
    o.pen_width=round(number('pen_width',4,1,20));o.highlighter_width=round(number('highlighter_width',20,1,80))
    o.opacity=number('opacity',1,.01,1);o.highlight_opacity=number('highlight_opacity',1,.01,1)
    toolbar.neon_check.setChecked(str(s.value('pen_neon','false')).lower()=='true')
    toolbar.fade_check.setChecked(str(s.value('pen_auto_fade','false')).lower()=='true')
    toolbar.fade_seconds.setValue(round(number('pen_fade_delay',3,1,15)))
    # Passive desktop observation is always opt-in for each app session.
    o.text_defaults.opacity=o.opacity;o.width=o.pen_width;o.color=o.pen_color
    toolbar.scale_slider.setValue(round(number('ui_scale',100,75,150)))
    toolbar.move(QPoint(round(number('x',28,-100000,100000)),round(number('y',28,-100000,100000))))
    toolbar.persist_settings=True;toolbar.refresh();toolbar.fit_toolbar()

def save(toolbar):
    o=toolbar.overlay;s=settings()
    if o.tool=='highlight':o.highlighter_color,o.highlighter_width=o.color,o.width
    else:o.pen_color,o.pen_width=o.color,o.width
    for key in ('pen_color','pen_width','highlighter_color','highlighter_width','opacity','highlight_opacity'):s.setValue(key,getattr(o,key))
    for key in ('pen_neon','pen_auto_fade','pen_fade_delay'):s.setValue(key,getattr(o,key))
    s.setValue('ui_scale',toolbar.scale_slider.value());s.setValue('x',toolbar.x());s.setValue('y',toolbar.y());s.sync()
