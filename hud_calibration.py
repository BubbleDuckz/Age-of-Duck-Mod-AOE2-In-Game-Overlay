"""Full-window set-up screen: point at each HUD item the overlay reads.

Designed to be easy to use with a mouse:
  * the game is frozen while you set up, so nothing moves under the boxes;
  * pick an item in the list, then just CLICK where it is on the HUD (drag to fine-tune);
  * numbers snap to their text automatically, so a rough click is enough;
  * scroll to resize, arrow keys nudge, round corner handles stretch the box.
"""
from PyQt5.QtCore import QPointF, QRectF, Qt, pyqtSignal
from PyQt5.QtGui import QColor, QFont, QImage, QPainter, QPainterPath, QPen, QPixmap
from PyQt5.QtWidgets import (QCheckBox, QFrame, QHBoxLayout, QLabel, QPushButton, QSizePolicy,
                             QVBoxLayout, QWidget)

from hud_regions import ORDER, REGIONS, describe, snap_to_text
from tc_reminder import native

COLORS = {
    'population': QColor('#4ADE80'),
    'villagers': QColor('#38BDF8'),
    'clock': QColor('#FACC15'),
    'queue': QColor('#F472B6'),
}
HANDLE_RADIUS = 7            # drawn size of the round corner handles, px
HANDLE_GRAB = 14             # how close counts as "on" a handle, px
GRAB_PADDING = 10            # pressing this close to a box picks it up
MIN_W, MIN_H = 14, 10
SNAPPABLE = ('population', 'villagers', 'clock')


def pil_to_pixmap(image):
    data = image.convert('RGBA').tobytes('raw', 'RGBA')
    qimage = QImage(data, image.width, image.height, 4 * image.width, QImage.Format_RGBA8888).copy()
    return QPixmap.fromImage(qimage)


class RegionRow(QFrame):
    """One selectable line in the control panel."""

    clicked = pyqtSignal(str)

    def __init__(self, key, parent=None):
        super().__init__(parent)
        self.key = key
        self.setObjectName('regionRow')
        self.setCursor(Qt.PointingHandCursor)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(10)
        self.dot = QLabel('●')
        self.dot.setStyleSheet(f'color:{COLORS[key].name()};font-size:16px;')
        text = QVBoxLayout()
        text.setSpacing(0)
        self.title = QLabel(REGIONS[key]['title'])
        self.title.setStyleSheet('font-weight:700;')
        self.hint = QLabel(REGIONS[key]['hint'])
        self.hint.setStyleSheet('color:#9FB3C8;font-size:11px;')
        self.hint.setWordWrap(True)
        text.addWidget(self.title)
        text.addWidget(self.hint)
        self.reading = QLabel('')
        self.reading.setStyleSheet(f'color:{COLORS[key].name()};font-weight:600;')
        self.reading.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        layout.addWidget(self.dot)
        layout.addLayout(text, 1)
        layout.addWidget(self.reading)
        self.set_selected(False)

    def set_selected(self, selected):
        color = COLORS[self.key]
        if selected:
            self.setStyleSheet(f'QFrame#regionRow{{background:rgba({color.red()},{color.green()},{color.blue()},46);'
                               f'border:1px solid {color.name()};border-radius:9px;}}QLabel{{background:transparent;color:#EEF6FF;}}')
        else:
            self.setStyleSheet('QFrame#regionRow{background:rgba(255,255,255,10);border:1px solid rgba(255,255,255,26);border-radius:9px;}'
                               'QFrame#regionRow:hover{background:rgba(255,255,255,24);}QLabel{background:transparent;color:#EEF6FF;}')
        self.dot.setStyleSheet(f'color:{color.name()};font-size:16px;')
        self.hint.setStyleSheet('color:#9FB3C8;font-size:11px;')
        self.reading.setStyleSheet(f'color:{color.name()};font-weight:600;')

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.key)


class HudCalibrator(QWidget):
    """Covers the game window. Boxes move and resize; Save stores them as window fractions."""

    saved = pyqtSignal()
    closed = pyqtSignal()

    def __init__(self, game, regions, detector, villager_reader, parent=None, frame=None):
        super().__init__(parent, Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.game = game
        self.regions = regions
        self.detector = detector
        self.villager_reader = villager_reader
        self.readouts = {}
        self.selected = ORDER[0]
        self.mode = None            # 'move' or 'resize'
        self.anchor = None          # fixed opposite corner while resizing
        self.grab_offset = QPointF()
        self.setWindowTitle('Age of Duck — set up HUD areas')
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)
        left, top, right, bottom = game[2]
        self.physical = (right - left, bottom - top)
        ratio = self.devicePixelRatioF()
        self.setFixedSize(round(self.physical[0] / ratio), round(self.physical[1] / ratio))
        # A frozen picture of the game: nothing moves while the boxes are placed, and it is what the
        # number snapping and "Test read" look at.
        self.frame = frame if frame is not None else self._grab_frame()
        self.background = pil_to_pixmap(self.frame).scaled(self.width(), self.height(), Qt.IgnoreAspectRatio, Qt.SmoothTransformation) if self.frame else None
        self.boxes = {}
        self._load_boxes()
        self._build_panel()
        self.select(self.selected)

    def _grab_frame(self):
        try:
            return native.grab_game(self.game)
        except Exception:
            return None

    # -- boxes ------------------------------------------------------------------
    def _load_boxes(self):
        w, h = self.width(), self.height()
        scale = self.physical[1] / 1440.0 / self.devicePixelRatioF()
        for key in ORDER:
            if self.regions.boxes and key in self.regions.boxes:
                fx0, fy0, fx1, fy1 = self.regions.boxes[key]
                self.boxes[key] = QRectF(fx0 * w, fy0 * h, (fx1 - fx0) * w, (fy1 - fy0) * h)
            else:
                x0, y0, x1, y1 = REGIONS[key]['default']
                self.boxes[key] = QRectF(x0 * scale, y0 * scale, (x1 - x0) * scale, (y1 - y0) * scale)

    def fractions(self):
        w, h = self.width(), self.height()
        return {k: (r.left() / w, r.top() / h, r.right() / w, r.bottom() / h) for k, r in self.boxes.items()}

    def reset_defaults(self):
        saved = self.regions.boxes
        self.regions.boxes = {}
        self._load_boxes()
        self.regions.boxes = saved
        self.readouts = {}
        for row in self.rows.values():
            row.reading.setText('')
        self._update_preview()
        self.update()

    def _clamp(self, rect):
        rect = QRectF(rect)
        rect.setWidth(max(MIN_W, min(rect.width(), self.width())))
        rect.setHeight(max(MIN_H, min(rect.height(), self.height())))
        rect.moveLeft(max(0.0, min(rect.left(), self.width() - rect.width())))
        rect.moveTop(max(0.0, min(rect.top(), self.height() - rect.height())))
        return rect

    # -- control panel ----------------------------------------------------------
    def _build_panel(self):
        self.panel = QFrame(self)
        self.panel.setObjectName('panel')
        self.panel.setStyleSheet(
            'QFrame#panel{background:rgba(14,22,34,238);border:1px solid rgba(255,255,255,70);border-radius:14px;}'
            'QLabel{color:#EEF6FF;background:transparent;font-family:"Segoe UI";}'
            'QCheckBox{color:#EEF6FF;font-family:"Segoe UI";spacing:8px;}'
            'QPushButton{background:rgba(255,255,255,18);border:1px solid rgba(255,255,255,45);border-radius:8px;'
            'color:#EEF6FF;padding:7px 14px;font-family:"Segoe UI";}'
            'QPushButton:hover{background:rgba(255,255,255,40);}'
            'QPushButton#primary{background:rgba(167,243,208,56);border:1px solid rgba(167,243,208,150);color:#A7F3D0;font-weight:700;}')
        layout = QVBoxLayout(self.panel)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(8)
        title = QLabel('Set up HUD areas')
        title.setFont(QFont('Segoe UI', 13, QFont.Bold))
        layout.addWidget(title)
        steps = QLabel('<b>1.</b> Pick an item below &nbsp; <b>2.</b> <b>Click</b> where it is on your HUD '
                       '(drag to fine-tune) &nbsp; <b>3.</b> Press <b>Test read</b>')
        steps.setStyleSheet('color:#EEF6FF;')
        steps.setWordWrap(True)
        layout.addWidget(steps)
        self.rows = {}
        for key in ORDER:
            row = RegionRow(key)
            row.clicked.connect(self.select)
            self.rows[key] = row
            layout.addWidget(row)
        self.preview = QLabel('')
        self.preview.setFixedHeight(54)
        self.preview.setAlignment(Qt.AlignCenter)
        self.preview.setStyleSheet('background:rgba(0,0,0,120);border:1px solid rgba(255,255,255,30);border-radius:8px;')
        self.preview.setToolTip('Close-up of what is inside the selected box')
        layout.addWidget(self.preview)
        tips = QLabel('Scroll to resize · arrow keys nudge (Shift = faster) · Tab switches item · drag a round handle to stretch')
        tips.setStyleSheet('color:#9FB3C8;font-size:11px;')
        tips.setWordWrap(True)
        layout.addWidget(tips)
        self.snap_check = QCheckBox('Snap numbers to their text automatically')
        self.snap_check.setChecked(True)
        self.snap_check.setFocusPolicy(Qt.NoFocus)
        layout.addWidget(self.snap_check)
        buttons = QHBoxLayout()
        buttons.setSpacing(8)
        self.snap_button = QPushButton('Snap to text')
        self.test_button = QPushButton('Test read')
        self.reset_button = QPushButton('Reset')
        cancel = QPushButton('Cancel')
        save = QPushButton('Save')
        save.setObjectName('primary')
        for b in (self.snap_button, self.test_button, self.reset_button, cancel, save):
            b.setCursor(Qt.PointingHandCursor)
            b.setFocusPolicy(Qt.NoFocus)
        buttons.addWidget(self.snap_button)
        buttons.addWidget(self.test_button)
        buttons.addWidget(self.reset_button)
        buttons.addStretch()
        buttons.addWidget(cancel)
        buttons.addWidget(save)
        layout.addLayout(buttons)
        self.snap_button.clicked.connect(lambda: self.snap(self.selected))
        self.test_button.clicked.connect(self.test_read)
        self.reset_button.clicked.connect(self.reset_defaults)
        cancel.clicked.connect(self.close)
        save.clicked.connect(self.save)
        self.panel.setFixedWidth(min(560, max(420, self.width() // 3)))
        self.panel.adjustSize()
        self.panel.move((self.width() - self.panel.width()) // 2, max(10, self.height() - self.panel.height() - 36))

    # -- selection ---------------------------------------------------------------
    def select(self, key):
        if key not in self.boxes:
            return
        self.selected = key
        for name, row in self.rows.items():
            row.set_selected(name == key)
        self._update_preview()
        self.update()

    def _update_preview(self):
        if not self.frame:
            self.preview.setText('(no game picture)')
            return
        rect = self.boxes[self.selected]
        sx = self.frame.width / self.width()
        sy = self.frame.height / self.height()
        pad = 6
        crop = self.frame.crop((max(0, int(rect.left() * sx) - pad), max(0, int(rect.top() * sy) - pad),
                                min(self.frame.width, int(rect.right() * sx) + pad), min(self.frame.height, int(rect.bottom() * sy) + pad)))
        if crop.width < 2 or crop.height < 2:
            self.preview.clear()
            return
        scale = max(1.0, min(5.0, min((self.panel.width() - 40) / crop.width, 46 / crop.height)))
        pix = pil_to_pixmap(crop).scaled(int(crop.width * scale), int(crop.height * scale), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.preview.setPixmap(pix)

    # -- actions ------------------------------------------------------------------
    def present(self):
        left, top, right, bottom = self.game[2]
        self.show()
        native.show_overlay(int(self.winId()), left, top, right - left, bottom - top)
        self.raise_()
        self.activateWindow()
        self.setFocus()

    def save(self):
        self.regions.set_boxes(self.fractions(), self.physical)
        self.saved.emit()
        self.close()

    def snap(self, key, quiet=False):
        """Fit a number box tightly around the text nearest to it."""
        if key not in SNAPPABLE or not self.frame:
            return False
        rect = self.boxes[key]
        sx = self.frame.width / self.width()
        sy = self.frame.height / self.height()
        fitted = snap_to_text(self.frame, (rect.left() * sx, rect.top() * sy, rect.right() * sx, rect.bottom() * sy), key)
        if fitted is None:
            return False
        x0, y0, x1, y1 = fitted
        self.boxes[key] = self._clamp(QRectF(x0 / sx, y0 / sy, (x1 - x0) / sx, (y1 - y0) / sy))
        self._update_preview()
        self.update()
        return True

    def test_read(self):
        """Read every box from the frozen picture."""
        raw = self.frame
        if raw is None:
            return
        self.readouts = describe(raw, self.fractions(), self.detector, self.villager_reader)
        for key, text in self.readouts.items():
            self.rows[key].reading.setText(text)
        self.update()

    def closeEvent(self, event):
        self.closed.emit()
        super().closeEvent(event)

    # -- keyboard ------------------------------------------------------------------
    def keyPressEvent(self, event):
        key = event.key()
        step = 10 if event.modifiers() & Qt.ShiftModifier else 1
        rect = QRectF(self.boxes[self.selected])
        if key == Qt.Key_Escape:
            self.close()
        elif key in (Qt.Key_Return, Qt.Key_Enter):
            self.save()
        elif key == Qt.Key_Tab or key == Qt.Key_Backtab:
            direction = -1 if (key == Qt.Key_Backtab or event.modifiers() & Qt.ShiftModifier) else 1
            self.select(ORDER[(ORDER.index(self.selected) + direction) % len(ORDER)])
        elif key in (Qt.Key_Left, Qt.Key_Right, Qt.Key_Up, Qt.Key_Down):
            dx = {Qt.Key_Left: -step, Qt.Key_Right: step}.get(key, 0)
            dy = {Qt.Key_Up: -step, Qt.Key_Down: step}.get(key, 0)
            rect.translate(dx, dy)
            self.boxes[self.selected] = self._clamp(rect)
        elif key in (Qt.Key_Plus, Qt.Key_Equal):
            self._scale_selected(1.06 if step == 1 else 1.2)
        elif key in (Qt.Key_Minus, Qt.Key_Underscore):
            self._scale_selected(1 / 1.06 if step == 1 else 1 / 1.2)
        elif key == Qt.Key_S:
            self.snap(self.selected)
        else:
            super().keyPressEvent(event)
            return
        self._update_preview()
        self.update()

    def _scale_selected(self, factor):
        rect = QRectF(self.boxes[self.selected])
        center = rect.center()
        rect.setWidth(max(MIN_W, rect.width() * factor))
        rect.setHeight(max(MIN_H, rect.height() * factor))
        rect.moveCenter(center)
        self.boxes[self.selected] = self._clamp(rect)

    def wheelEvent(self, event):
        steps = event.angleDelta().y() / 120.0
        if steps:
            self._scale_selected(1.07 ** steps)
            self._update_preview()
            self.update()
        event.accept()

    # -- painting -----------------------------------------------------------------
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        if self.background is not None:
            painter.drawPixmap(0, 0, self.background)
        veil = QPainterPath()
        veil.addRect(QRectF(self.rect()))
        for rect in self.boxes.values():
            hole = QPainterPath()
            hole.addRect(rect)
            veil = veil.subtracted(hole)
        painter.fillPath(veil, QColor(0, 0, 0, 105 if self.background is not None else 120))
        for key in ORDER:
            if key != self.selected:
                self._draw_box(painter, key, False)
        self._draw_box(painter, self.selected, True)

    def _draw_box(self, painter, key, selected):
        rect = self.boxes[key]
        color = COLORS[key]
        painter.setBrush(Qt.NoBrush)
        # A soft halo makes small boxes easy to see against a busy HUD.
        halo = QColor(color.red(), color.green(), color.blue(), 70 if selected else 35)
        painter.setPen(QPen(halo, 8 if selected else 5))
        painter.drawRect(rect)
        painter.setPen(QPen(color, 2.5 if selected else 1.5))
        painter.drawRect(rect)
        self._chip(painter, rect.left(), rect.top() - 5, REGIONS[key]['title'], color, above=True)
        if key in self.readouts:
            self._chip(painter, rect.left(), rect.bottom() + 5, self.readouts[key], color, above=False)
        if selected:
            radius = max(3.0, min(HANDLE_RADIUS, min(rect.width(), rect.height()) * 0.3))
            for corner in self._corners(rect).values():
                painter.setPen(QPen(color, 1.6))
                painter.setBrush(QColor(255, 255, 255))
                painter.drawEllipse(corner, radius, radius)

    @staticmethod
    def _corners(rect):
        return {'tl': rect.topLeft(), 'tr': rect.topRight(), 'bl': rect.bottomLeft(), 'br': rect.bottomRight()}

    def _chip(self, painter, x, y, text, color, above):
        painter.setFont(QFont('Segoe UI', 9, QFont.DemiBold))
        metrics = painter.fontMetrics()
        w, h = metrics.horizontalAdvance(text) + 14, metrics.height() + 5
        x = max(2, min(x, self.width() - w - 2))
        rect = QRectF(x, y - h if above else y, w, h)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(color.red(), color.green(), color.blue(), 240))
        painter.drawRoundedRect(rect, 6, 6)
        painter.setPen(QColor(10, 14, 20))
        painter.drawText(rect, Qt.AlignCenter, text)

    # -- mouse --------------------------------------------------------------------
    def _handle_at(self, pos):
        rect = self.boxes[self.selected]
        # Small boxes get a smaller handle zone so most of the box stays a "move" area.
        grab = max(5.0, min(HANDLE_GRAB, min(rect.width(), rect.height()) * 0.5))
        for name, corner in self._corners(rect).items():
            if abs(pos.x() - corner.x()) <= grab and abs(pos.y() - corner.y()) <= grab:
                return name
        return None

    def _box_at(self, pos):
        """The selected box wins; otherwise the nearest box within a generous grab margin."""
        order = [self.selected] + [k for k in reversed(ORDER) if k != self.selected]
        for key in order:
            if self.boxes[key].adjusted(-GRAB_PADDING, -GRAB_PADDING, GRAB_PADDING, GRAB_PADDING).contains(pos):
                return key
        return None

    def mousePressEvent(self, event):
        if event.button() != Qt.LeftButton:
            return
        pos = QPointF(event.pos())
        handle = self._handle_at(pos)
        if handle:
            rect = self.boxes[self.selected]
            opposite = {'tl': rect.bottomRight(), 'tr': rect.bottomLeft(), 'bl': rect.topRight(), 'br': rect.topLeft()}[handle]
            self.mode, self.anchor = 'resize', opposite
            return
        key = self._box_at(pos)
        if key:
            self.select(key)
            self.grab_offset = pos - self.boxes[key].topLeft()
        else:
            # Click anywhere: put the selected box right there (centred on the cursor) and keep dragging.
            rect = QRectF(self.boxes[self.selected])
            rect.moveCenter(pos)
            self.boxes[self.selected] = self._clamp(rect)
            self.grab_offset = pos - self.boxes[self.selected].topLeft()
        self.mode = 'move'
        self._update_preview()
        self.update()

    def mouseMoveEvent(self, event):
        pos = QPointF(event.pos())
        if self.mode == 'move':
            rect = QRectF(self.boxes[self.selected])
            rect.moveTopLeft(pos - self.grab_offset)
            self.boxes[self.selected] = self._clamp(rect)
            self._update_preview()
            self.update()
        elif self.mode == 'resize':
            rect = QRectF(self.anchor, pos).normalized()
            if rect.width() < MIN_W:
                rect.setWidth(MIN_W)
            if rect.height() < MIN_H:
                rect.setHeight(MIN_H)
            self.boxes[self.selected] = self._clamp(rect)
            self._update_preview()
            self.update()
        else:
            if self._handle_at(pos):
                self.setCursor(Qt.SizeFDiagCursor)
            elif self._box_at(pos):
                self.setCursor(Qt.SizeAllCursor)
            else:
                self.setCursor(Qt.CrossCursor)

    def mouseReleaseEvent(self, event):
        if self.mode and self.snap_check.isChecked() and self.selected in SNAPPABLE:
            self.snap(self.selected, quiet=True)
        self.mode = None
        self.anchor = None
