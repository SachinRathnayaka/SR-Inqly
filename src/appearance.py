"""Compact controls and contrast-aware toolbar themes."""
import re
from PySide6.QtCore import QPoint, QSettings, Qt
from PySide6.QtGui import QColor, QPixmap
from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QMenu, QColorDialog, QLabel, QPushButton, QDialog, QDialogButtonBox, QFormLayout, QSpinBox
from icons import icon, crosshair_cursor


def mix(a, b, amount):
    a, b = QColor(a), QColor(b)
    return QColor(*(round(x*(1-amount)+y*amount) for x,y in zip(a.getRgb()[:3],b.getRgb()[:3]))).name()


def luminance(color):
    values = [v/12.92 if v <= .04045 else ((v+.055)/1.055)**2.4 for v in QColor(color).getRgbF()[:3]]
    return sum(a*b for a,b in zip(values,(.2126,.7152,.0722)))


class Appearance:
    def __init__(self, toolbar, root, header, scale_row):
        self.t = toolbar
        self.settings = QSettings('SRInqly', 'Appearance')
        self.restore_cursor()
        self.background = str(self.settings.value('background', '#171d2b'))
        if not QColor(self.background).isValid():
            self.background = '#171d2b'
        self.compact = False
        self.scale_widgets = [scale_row.itemAt(i).widget() for i in range(scale_row.count())]
        self.theme_button = toolbar.button('Theme',self.open_theme,'Theme','palette')
        self.theme_button.setFixedWidth(32)
        header.insertWidget(2,self.theme_button)
        self.quick_button = toolbar.button('Quick screenshot',toolbar.quick_screenshot,'Quick screenshot → Pictures','screenshot')
        self.quick_button.setFixedWidth(32)
        header.insertWidget(3,self.quick_button)
        self.panel = QWidget()
        layout = QVBoxLayout(self.panel)
        layout.setContentsMargins(0,0,0,0)
        self.tools = {}
        row = QHBoxLayout()
        for tool in ('pen','highlight','eraser','text'):
            button = toolbar.button(tool.title(),lambda _=False,t=tool:toolbar.toggle_tool(t),tool.title(),tool)
            button.setCheckable(True)
            self.tools[tool] = button
            row.addWidget(button)
        layout.addLayout(row)
        row = QHBoxLayout()
        for tool,callback in (('undo',toolbar.overlay.undo),('redo',toolbar.overlay.redo)):
            row.addWidget(toolbar.button(tool.title(),callback,tool.title(),tool))
        self.shape = toolbar.button('Shapes',self.open_shapes,'More tools','rectangle')
        self.shape.setCheckable(True)
        self.shape.setText('▾')
        row.addWidget(self.shape)
        self.color = QPushButton('▾')
        self.color.setToolTip('Color')
        self.color.setFocusPolicy(Qt.NoFocus)
        self.color.clicked.connect(self.open_colors)
        row.addWidget(self.color)
        layout.addLayout(row)
        row = QHBoxLayout()
        self.neon = QPushButton('Neon')
        self.desktop_neon = QPushButton('Desktop neon')
        for button,checkbox in ((self.neon,toolbar.neon_check),(self.desktop_neon,toolbar.desktop_neon_check)):
            button.setCheckable(True)
            button.setMinimumHeight(32)
            button.setFocusPolicy(Qt.NoFocus)
            button.setCursor(Qt.ArrowCursor)
            button.clicked.connect(lambda checked=False,c=checkbox:c.setChecked(checked))
            row.addWidget(button)
        self.neon.setToolTip('Toggle pen glow; turning off also stops Desktop neon')
        self.desktop_neon.setToolTip('Toggle temporary desktop neon; normal clicks pass through')
        layout.addLayout(row)
        root.insertWidget(1,self.panel)
        self.panel.hide()

    def menu(self, button):
        menu = QMenu(self.t)
        menu.setStyleSheet(f'QMenu {{background:{self.surface}; color:{self.foreground}; border:1px solid {self.foreground}; padding:5px;}} QMenu::item {{padding:7px 18px;}} QMenu::item:selected {{background:{self.foreground}; color:{self.surface};}}')
        menu.aboutToHide.connect(menu.deleteLater)
        return menu

    def open_theme(self):
        menu = self.menu(self.theme_button)
        for label,color in (('Light','#f4f6fa'),('Dark','#171d2b')):
            menu.addAction(label,lambda c=color:self.set_theme(c))
        menu.addSeparator()
        menu.addAction('Custom color…',self.custom)
        menu.addAction('Cursor…',self.custom_cursor)
        from branding_ui import show_about
        menu.addSeparator()
        menu.addAction('About SR Inqly',lambda:show_about(self.t))
        menu.popup(self.theme_button.mapToGlobal(QPoint(0,self.theme_button.height())))

    def restore_cursor(self):
        o = self.t.overlay
        color = str(self.settings.value('cursor_color', '#172033'))
        o.cursor_color = QColor(color).name() if QColor(color).isValid() else '#172033'
        for key, default, low, high in (('cursor_width', 2, 1, 6), ('cursor_size', 20, 12, 40)):
            try:
                value = int(self.settings.value(key, default))
            except (TypeError, ValueError, OverflowError):
                value = default
            setattr(o, key, max(low, min(high, value)))
        o.update_cursor()

    def custom_cursor(self):
        o = self.t.overlay
        was = o.click_through
        o.set_click_through(True)
        dialog = QDialog(self.t)
        dialog.setWindowTitle('Cursor')
        dialog.setMinimumWidth(320)
        dialog.setStyleSheet(f'QDialog {{background:{self.background};color:{self.foreground};}} QLabel, QSpinBox, QPushButton {{color:{self.foreground};background:{self.surface};}}')
        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel('Customize the + drawing cursor'))
        preview = QLabel()
        preview.setObjectName('cursorPreview')
        preview.setAlignment(Qt.AlignCenter)
        preview.setMinimumHeight(90)
        layout.addWidget(preview)
        form = QFormLayout()
        color = QPushButton()
        color.setObjectName('cursorColor')
        selected = [o.cursor_color]
        width = QSpinBox()
        width.setObjectName('cursorWidth')
        width.setRange(1, 6)
        width.setSuffix(' px')
        width.setValue(o.cursor_width)
        size = QSpinBox()
        size.setObjectName('cursorSize')
        size.setRange(12, 40)
        size.setSuffix(' px')
        size.setValue(o.cursor_size)
        def stepper(spin, label):
            row = QWidget(dialog)
            controls = QHBoxLayout(row)
            controls.setContentsMargins(0, 0, 0, 0)
            controls.setSpacing(6)
            spin.setButtonSymbols(QSpinBox.NoButtons)
            spin.setMinimumHeight(34)
            controls.addWidget(spin, 1)
            for text, suffix, step in (('−', 'Decrease', -1), ('+', 'Increase', 1)):
                button = QPushButton(text, row)
                button.setObjectName(spin.objectName() + suffix)
                button.setAccessibleName(suffix + ' ' + label)
                button.setToolTip(suffix + ' ' + label)
                button.setFixedSize(38, 34)
                button.setCursor(Qt.ArrowCursor)
                button.setFocusPolicy(Qt.NoFocus)
                button.setAutoDefault(False)
                button.clicked.connect(lambda _=False, delta=step: spin.stepBy(delta))
                controls.addWidget(button)
            return row
        form.addRow('Color', color)
        form.addRow('Line thickness', stepper(width, 'line thickness'))
        form.addRow('Size', stepper(size, 'size'))
        layout.addLayout(form)
        def refresh():
            cursor = crosshair_cursor(selected[0], width.value(), size.value())
            preview.setPixmap(cursor.pixmap())
            preview.setCursor(cursor)
            color.setText(selected[0].upper())
            foreground = '#000000' if luminance(selected[0]) > .179 else '#ffffff'
            color.setStyleSheet(f'background:{selected[0]};color:{foreground};padding:6px;')
        def pick():
            chosen = QColorDialog.getColor(QColor(selected[0]), dialog, 'Cursor color')
            if chosen.isValid():
                selected[0] = chosen.name()
                refresh()
        def reset():
            selected[0] = '#172033'
            width.setValue(2)
            size.setValue(20)
            refresh()
        color.clicked.connect(pick)
        width.valueChanged.connect(refresh)
        size.valueChanged.connect(refresh)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel | QDialogButtonBox.RestoreDefaults)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        buttons.button(QDialogButtonBox.RestoreDefaults).clicked.connect(reset)
        layout.addWidget(buttons)
        refresh()
        try:
            if dialog.exec() == QDialog.Accepted:
                o.cursor_color, o.cursor_width, o.cursor_size = selected[0], width.value(), size.value()
                for key in ('cursor_color', 'cursor_width', 'cursor_size'):
                    self.settings.setValue(key, getattr(o, key))
                self.settings.sync()
        finally:
            dialog.deleteLater()
            o.set_click_through(was)

    def custom(self):
        was = self.t.overlay.click_through
        self.t.overlay.set_click_through(True)
        color = QColorDialog.getColor(QColor(self.background),self.t,'UI color')
        if color.isValid():
            self.set_theme(color.name())
        self.t.overlay.set_click_through(was)

    def set_theme(self,color):
        self.background = color
        self.settings.setValue('background',color)
        self.apply()

    def open_shapes(self):
        if not self.t.overlay.click_through and self.t.overlay.tool in ('select','line','rectangle','ellipse','arrow','fetcher'):
            self.t.overlay.set_click_through(True)
            return
        menu = self.menu(self.shape)
        for tool in ('select','line','rectangle','ellipse','arrow','fetcher'):
            action = menu.addAction(icon(tool,self.foreground),tool.title())
            action.triggered.connect(lambda _=False,t=tool:self.t.toggle_tool(t))
        menu.popup(self.shape.mapToGlobal(QPoint(0,self.shape.height())))

    def open_colors(self):
        SWATCHES = ['#ff4655','#ffcb3d','#57dd9b','#40b9ff','#a895ff','#ffffff','#111827']
        menu = self.menu(self.color)
        for name,color in zip(('Red','Yellow','Green','Blue','Purple','White','Black'),SWATCHES):
            pixmap = QPixmap(20,20)
            pixmap.fill(QColor(color))
            from PySide6.QtGui import QIcon
            action = menu.addAction(QIcon(pixmap),name)
            action.triggered.connect(lambda _=False,c=color:self.t.set_color(c))
        menu.addSeparator()
        for text,checkbox in (('Neon pen',self.t.neon_check),('Temporary pen fade',self.t.fade_check),
                              ('Desktop neon · clicks pass through',self.t.desktop_neon_check)):
            action=menu.addAction(text)
            action.setCheckable(True);action.setChecked(checkbox.isChecked())
            action.toggled.connect(checkbox.setChecked)
        delays=menu.addMenu('Fade delay')
        for seconds in (1,3,5,10,15):
            action=delays.addAction(f'{seconds} seconds')
            action.setCheckable(True);action.setChecked(self.t.fade_seconds.value()==seconds)
            action.triggered.connect(lambda _=False,s=seconds:self.t.fade_seconds.setValue(s))
        widths=menu.addMenu('Pen / neon width')
        for width in (1,2,4,6,8,12,16,20):
            action=widths.addAction(f'{width} px')
            action.setCheckable(True);action.setChecked(self.t.overlay.pen_width==width)
            action.triggered.connect(lambda _=False,w=width:self.set_pen_width(w))
        menu.popup(self.color.mapToGlobal(QPoint(0,self.color.height())))

    def set_pen_width(self,width):
        o=self.t.overlay
        o.pen_width=width
        if o.tool!='highlight':
            self.t.set_width(width)
            self.t.refresh()

    def toggle(self):
        self.compact = not self.compact
        self.t.scroll_area.setVisible(not self.compact)
        self.panel.setVisible(self.compact)
        for widget in self.scale_widgets:
            widget.setVisible(not self.compact)
        self.t.status.setVisible(not self.compact)
        self.t.minimize_button.setProperty('inkIcon','expand' if self.compact else 'collapse')
        self.apply()
        self.t.fit_toolbar()

    def apply(self):
        t = self.t
        self.neon.setChecked(t.neon_check.isChecked())
        self.desktop_neon.setChecked(t.desktop_neon_check.isChecked())
        shape_active = t.overlay.tool in ('select','line','rectangle','ellipse','arrow','fetcher')
        if shape_active:
            self.shape.setProperty('inkIcon',t.overlay.tool)
            self.shape.setToolTip(t.overlay.tool.title()+' / More tools')
        self.shape.setChecked(shape_active and not t.overlay.click_through)
        dark = luminance(self.background) < .179
        self.foreground = '#ffffff' if dark else '#000000'
        self.surface = mix(self.background,'#ffffff' if dark else '#000000',.10)
        hover = mix(self.background,'#ffffff' if dark else '#000000',.18)
        # Choose foreground again against the button surface for reliable contrast.
        button_fg = '#ffffff' if luminance(self.surface) < .179 else '#000000'
        mapping = {c:self.foreground for c in ('#edf3ff','#e9f0fa','#d8f5ff','#9db2ca','#afc0d6','#67d9ff')}
        mapping.update({'#171d2b':self.background,'#293348':self.surface,'#3b4d69':hover,
                        '#212a3b':self.surface,'#40506a':hover,'#43516a':hover,'#313d51':hover,
                        '#49566a':hover})
        theme_key = (self.background, t.ui_scale)
        if getattr(self, '_applied_key', None) != theme_key:
            self._applied_key = theme_key
            for widget,css,*_ in t._scale_snapshot:
                if css:
                    # Preserve annotation swatches; those colors are independent of the UI theme.
                    if 'border: 2px solid #75869b' in css:
                        continue
                    css = re.sub(r'#[0-9a-fA-F]{6}',lambda m:mapping.get(m[0],m[0]),css)
                    css = re.sub(r'(-?\d+(?:\.\d+)?)px',lambda m:f'{round(float(m[1])*t.ui_scale)}px',css)
                    widget.setStyleSheet(css)
            t.setStyleSheet(t.styleSheet()+f' QPushButton {{color:{button_fg};}} QPushButton:checked {{background:#bfeaff;color:#102337;}} QToolTip {{background:{self.surface};color:{button_fg};border:1px solid {button_fg};padding:4px;}}')
        for button in t.findChildren(QPushButton):
            name = button.property('inkIcon')
            if name and button.property('inkApplied') != (name,button_fg):
                button.setIcon(icon(name,button_fg))
                button.setProperty('inkApplied',(name,button_fg))
        for tool,button in self.tools.items():
            button.setChecked(t.overlay.tool==tool and not t.overlay.click_through)
        self.color.setStyleSheet(f'background:{t.overlay.color};color:{"#111111" if luminance(t.overlay.color)>.179 else "#ffffff"};')
        for label in t.findChildren(QLabel):
            if not label.pixmap().isNull() and not label.property('brandLogo'):
                label.setPixmap(icon('size',self.foreground).pixmap(round(20*t.ui_scale),round(20*t.ui_scale)))
