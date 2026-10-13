"""Age of Duck styled, non-activating Idle / Housed status panel."""
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QPoint, QRectF
from PyQt5.QtGui import QPainter, QLinearGradient, QColor, QPen, QFont, QCursor, QPainterPath
from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout, QHBoxLayout, QFrame
from . import native
from ui_bits import SizeButton, SpeakerButton


class TCPanel(QWidget):
    mute_requested = pyqtSignal()
    scale_requested = pyqtSignal(int)
    position_changed = pyqtSignal(object)

    def __init__(self):
        super().__init__(None, Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.WindowDoesNotAcceptFocus)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowTitle('Age of Duck - Idle / Housed')
        self.scale = 1.
        self.offset = None
        self.game = None
        self.drag_origin = None
        self.flashing = False
        self.phase = False
        self.outer = QVBoxLayout(self)
        self.outer.setContentsMargins(0, 0, 0, 0)
        self.outer.setSpacing(0)

        # Translucent title bar: caption, sound toggle and size controls; drag to move.
        self.drag_bar = QWidget()
        self.drag_bar.setCursor(Qt.SizeAllCursor)
        self.drag_bar.setToolTip('Drag to reposition Idle / Housed')
        bar = QHBoxLayout(self.drag_bar)
        bar.setContentsMargins(10, 4, 6, 4)
        bar.setSpacing(5)
        self.caption = QLabel('IDLE / HOUSED')
        self.caption.setObjectName('caption')
        self.caption.setAttribute(Qt.WA_TransparentForMouseEvents)
        bar.addWidget(self.caption, 1)
        self.mute_button = SpeakerButton()
        self.mute_button.setToolTip('Mute / unmute all reminder voices')
        self.mute_button.clicked.connect(self.mute_requested)
        self.minus = SizeButton(False)
        self.plus = SizeButton(True)
        self.minus.setToolTip('Smaller Idle / Housed and build order windows')
        self.plus.setToolTip('Larger Idle / Housed and build order windows')
        self.minus.clicked.connect(lambda: self.scale_requested.emit(-1))
        self.plus.clicked.connect(lambda: self.scale_requested.emit(1))
        for widget in (self.mute_button, self.minus, self.plus):
            bar.addWidget(widget)
        self.drag_bar.mousePressEvent = self.drag_press
        self.drag_bar.mouseMoveEvent = self.drag_move
        self.drag_bar.mouseReleaseEvent = self.drag_release
        self.outer.addWidget(self.drag_bar)

        # Two stat tiles.
        tiles = QHBoxLayout()
        tiles.setContentsMargins(8, 6, 8, 4)
        tiles.setSpacing(6)
        self.headings = []
        self.values = []
        self.tiles = []
        for title in ['Available', 'Idle']:
            tile = QFrame()
            tile.setObjectName('tile')
            column = QVBoxLayout(tile)
            column.setContentsMargins(4, 3, 4, 3)
            column.setSpacing(0)
            value = QLabel('?')
            value.setAlignment(Qt.AlignCenter)
            heading = QLabel(title)
            heading.setAlignment(Qt.AlignCenter)
            heading.setObjectName('heading')
            column.addWidget(value)
            column.addWidget(heading)
            tiles.addWidget(tile, 1)
            self.headings.append(heading)
            self.values.append(value)
            self.tiles.append(tile)
        self.outer.addLayout(tiles)

        alert_row = QHBoxLayout()
        alert_row.setContentsMargins(8, 0, 8, 8)
        self.alert = QLabel('Select your Town Centres')
        self.alert.setAlignment(Qt.AlignCenter)
        alert_row.addWidget(self.alert)
        self.outer.addLayout(alert_row)

        self.setStyleSheet(
            'QLabel {color:#EEF6FF;background:transparent;}'
            'QLabel#caption {color:#9FB3C8;font-weight:700;}'
            'QLabel#heading {color:#9FB3C8;}'
            'QFrame#tile {background:rgba(255,255,255,0.055);border:1px solid rgba(255,255,255,0.09);border-radius:9px;}'
        )
        self.hwnd = int(self.winId())
        flags = native.u.GetWindowLongPtrW(self.hwnd, -20) | 0x80000 | 0x20 | 0x80 | 0x08000000
        native.u.SetWindowLongPtrW(self.hwnd, -20, flags)
        self.flash_timer = QTimer(self)
        self.flash_timer.timeout.connect(self.flash)
        self.flash_timer.start(650)
        self.hit_timer = QTimer(self)
        self.hit_timer.timeout.connect(self.update_input)
        self.hit_timer.start(25)
        self.set_scale(1.)

    def set_scale(self, value):
        self.scale = value
        self.setFixedWidth(round(236 * value))

        def font(pixels, bold=False, spacing=0.0):
            f = QFont('Segoe UI')
            f.setPixelSize(max(7, round(pixels * value)))
            f.setBold(bold)
            if spacing:
                f.setLetterSpacing(QFont.AbsoluteSpacing, spacing)
            return f
        self.caption.setFont(font(10, True, 1.2))
        for heading in self.headings:
            heading.setFont(font(10))
        for number in self.values:
            number.setFont(font(21, True))
        self.alert.setFont(font(11, True))
        self.alert.setFixedHeight(round(22 * value))
        side = max(18, round(20 * value))
        for button in (self.minus, self.plus):
            button.setFixedSize(side, side)
        self.mute_button.setFixedSize(round(26 * value), side)
        self.adjustSize()
        self.place()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        radius = 13
        g = QLinearGradient(r.topLeft(), r.bottomRight())
        g.setColorAt(0, QColor(18, 29, 40, 224))
        g.setColorAt(1, QColor(28, 43, 59, 218))
        p.setBrush(g)
        p.setPen(QPen(QColor(255, 255, 255, 52), 1))
        p.drawRoundedRect(r, radius, radius)
        bar = QRectF(r.left(), r.top(), r.width(), self.drag_bar.height())
        strip = QPainterPath()
        strip.addRoundedRect(bar.adjusted(0, 0, 0, radius), radius, radius)
        clip = QPainterPath()
        clip.addRect(bar)
        p.setClipPath(strip.intersected(clip))
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(255, 255, 255, 26))
        p.drawRect(bar)
        p.setClipping(False)
        p.setPen(QPen(QColor(255, 255, 255, 36), 1))
        p.drawLine(int(bar.left() + 8), int(bar.bottom()), int(bar.right() - 8), int(bar.bottom()))

    def flash(self):
        self.phase = not self.phase
        text = self.alert.text()
        # "Build House" alone is an early warning (amber); Housed or an idle TC is urgent (red).
        early = 'Build House' in text and 'Housed' not in text and 'Idle' not in text
        bright, dim = ('rgba(232,150,30,225)', 'rgba(122,78,20,160)') if early else ('rgba(205,53,65,210)', 'rgba(115,30,43,150)')
        color = bright if self.flashing and self.phase else dim if self.flashing else 'rgba(167,243,208,16)'
        self.alert.setStyleSheet(f'background:{color};border:1px solid rgba(255,255,255,28);border-radius:7px;color:#EEF6FF;')

    def present(self, game, total, idle, alert, muted=False, warning=False):
        self.game = game
        self.values[0].setText('?' if total is None else str(total))
        self.values[1].setText(str(idle))
        # An idle Town Centre is the thing to notice: tint the number.
        self.values[1].setStyleSheet('color:#FCA5A5;' if str(idle) not in ('0', '?') else '')
        self.alert.setText(alert)
        self.alert.setToolTip(alert)
        self.mute_button.set_state(muted, 0 if muted else 100)
        changed = self.flashing != warning
        self.flashing = warning
        if changed:
            self.phase = False
            self.flash()
        self.adjustSize()
        self.show()
        self.place()

    def place(self):
        if not self.game or not self.isVisible() or self.drag_origin is not None:
            return
        ratio = self.devicePixelRatioF()
        w = round(self.width() * ratio)
        h = round(self.height() * ratio)
        l, t, r, b = self.game[2]
        dx, dy = self.offset if self.offset is not None else ((r - l - w) // 2, 70)
        dx = max(0, min(dx, r - l - w))
        dy = max(0, min(dy, b - t - h))
        native.show_overlay(self.hwnd, l + int(dx), t + int(dy), w, h)

    def update_input(self):
        pos = self.mapFromGlobal(QCursor.pos())
        interactive = self.drag_origin is not None
        for widget in (self.drag_bar, self.mute_button, self.minus, self.plus):
            local = widget.mapFrom(self, pos)
            interactive |= widget.isEnabled() and widget.rect().contains(local)
        flags = native.u.GetWindowLongPtrW(self.hwnd, -20)
        wanted = flags & ~0x20 if interactive and self.isVisible() else flags | 0x20
        if flags != wanted:
            native.u.SetWindowLongPtrW(self.hwnd, -20, wanted)

    def drag_press(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_origin = event.globalPos() - self.pos()
            event.accept()

    def drag_move(self, event):
        if self.drag_origin is not None:
            self.move(event.globalPos() - self.drag_origin)
            event.accept()

    def drag_release(self, event):
        if self.drag_origin is not None:
            self.drag_origin = None
            if self.game:
                ratio = self.devicePixelRatioF()
                self.offset = (round(self.x() * ratio) - self.game[2][0], round(self.y() * ratio) - self.game[2][1])
                self.position_changed.emit(self.offset)
            self.place()
        event.accept()
