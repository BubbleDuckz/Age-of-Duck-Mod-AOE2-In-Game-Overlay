"""Full-window set-up screen: drag a box over each HUD item the overlay reads."""
from PyQt5.QtCore import QPointF, QRectF, Qt, QThread, pyqtSignal
from PyQt5.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PyQt5.QtWidgets import QApplication, QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from hud_regions import ORDER, REGIONS, describe
from tc_reminder import native

COLORS = {
    'population': QColor('#4ADE80'),
    'villagers': QColor('#38BDF8'),
    'clock': QColor('#FACC15'),
    'queue': QColor('#F472B6'),
}
HANDLE = 7           # grab margin around edges, px
MIN_W, MIN_H = 14, 10


class HudCalibrator(QWidget):
    """Covers the game window. Boxes move and resize; Save stores them as window fractions."""

    saved = pyqtSignal()
    closed = pyqtSignal()

    def __init__(self, game, regions, detector, villager_reader, parent=None):
        super().__init__(parent, Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.game = game
        self.regions = regions
        self.detector = detector
        self.villager_reader = villager_reader
        self.readouts = {}
        self.active = None       # key being dragged
        self.mode = None         # 'move' or a set of edges
        self.grab_origin = None
        self.box_origin = None
        self.setWindowTitle('Age of Duck — set up HUD areas')
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setMouseTracking(True)
        left, top, right, bottom = game[2]
        self.physical = (right - left, bottom - top)
        ratio = self.devicePixelRatioF()
        self.setFixedSize(round(self.physical[0] / ratio), round(self.physical[1] / ratio))
        self.boxes = {}
        self._load_boxes()
        self._build_panel()

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
        self.update()

    # -- control panel ----------------------------------------------------------
    def _build_panel(self):
        self.panel = QFrame(self)
        self.panel.setObjectName('panel')
        self.panel.setStyleSheet(
            'QFrame#panel{background:rgba(18,29,40,235);border:1px solid rgba(255,255,255,70);border-radius:12px;}'
            'QLabel{color:#EEF6FF;background:transparent;font-family:"Segoe UI";}'
            'QPushButton{background:rgba(255,255,255,18);border:1px solid rgba(255,255,255,45);border-radius:7px;'
            'color:#EEF6FF;padding:6px 14px;font-family:"Segoe UI";}'
            'QPushButton:hover{background:rgba(255,255,255,40);}'
            'QPushButton#primary{background:rgba(167,243,208,56);border:1px solid rgba(167,243,208,150);color:#A7F3D0;font-weight:700;}')
        layout = QVBoxLayout(self.panel)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)
        title = QLabel('Set up HUD areas')
        title.setFont(QFont('Segoe UI', 13, QFont.Bold))
        layout.addWidget(title)
        intro = QLabel('Drag each coloured box over the matching part of your in-game HUD. '
                       'Drag the edges to resize. Press Test read to check what the overlay sees.')
        intro.setWordWrap(True)
        intro.setStyleSheet('color:#9FB3C8;')
        layout.addWidget(intro)
        for key in ORDER:
            row = QHBoxLayout()
            dot = QLabel('■')
            dot.setStyleSheet(f'color:{COLORS[key].name()};')
            name = QLabel(f"<b>{REGIONS[key]['title']}</b> — {REGIONS[key]['hint']}")
            name.setWordWrap(True)
            row.addWidget(dot, 0, Qt.AlignTop)
            row.addWidget(name, 1)
            layout.addLayout(row)
        self.result_label = QLabel('')
        self.result_label.setStyleSheet('color:#A7F3D0;')
        self.result_label.setWordWrap(True)
        layout.addWidget(self.result_label)
        buttons = QHBoxLayout()
        buttons.setSpacing(8)
        self.test_button = QPushButton('Test read')
        self.reset_button = QPushButton('Reset boxes')
        cancel = QPushButton('Cancel')
        save = QPushButton('Save')
        save.setObjectName('primary')
        for b in (self.test_button, self.reset_button, cancel, save):
            b.setCursor(Qt.PointingHandCursor)
            b.setFocusPolicy(Qt.NoFocus)
        buttons.addWidget(self.test_button)
        buttons.addWidget(self.reset_button)
        buttons.addStretch()
        buttons.addWidget(cancel)
        buttons.addWidget(save)
        layout.addLayout(buttons)
        self.test_button.clicked.connect(self.test_read)
        self.reset_button.clicked.connect(self.reset_defaults)
        cancel.clicked.connect(self.close)
        save.clicked.connect(self.save)
        self.panel.setFixedWidth(min(520, max(380, self.width() // 3)))
        self.panel.adjustSize()
        self.panel.move((self.width() - self.panel.width()) // 2, max(10, self.height() // 2 - self.panel.height() // 2))

    # -- actions ------------------------------------------------------------------
    def present(self):
        left, top, right, bottom = self.game[2]
        self.show()
        native.show_overlay(int(self.winId()), left, top, right - left, bottom - top)
        self.raise_()

    def save(self):
        self.regions.set_boxes(self.fractions(), self.physical)
        self.saved.emit()
        self.close()

    def test_read(self):
        """Capture the game without this window in the way, then read every box."""
        self.setWindowOpacity(0.0)
        QApplication.processEvents()
        QThread.msleep(150)
        try:
            raw = native.grab_game(self.game)
        finally:
            self.setWindowOpacity(1.0)
        self.readouts = describe(raw, self.fractions(), self.detector, self.villager_reader)
        self.result_label.setText('   '.join(f"{REGIONS[k]['title']}: {v}" for k, v in self.readouts.items()))
        self.update()

    def closeEvent(self, event):
        self.closed.emit()
        super().closeEvent(event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()

    # -- painting -----------------------------------------------------------------
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        veil = QPainterPath()
        veil.addRect(QRectF(self.rect()))
        for rect in self.boxes.values():
            hole = QPainterPath()
            hole.addRect(rect)
            veil = veil.subtracted(hole)
        painter.fillPath(veil, QColor(0, 0, 0, 120))
        for key in ORDER:
            rect = self.boxes[key]
            color = COLORS[key]
            painter.setBrush(Qt.NoBrush)
            painter.setPen(QPen(color, 2))
            painter.drawRect(rect)
            painter.setPen(Qt.NoPen)
            painter.setBrush(color)
            for corner in (rect.topLeft(), rect.topRight(), rect.bottomLeft(), rect.bottomRight()):
                painter.drawRect(QRectF(corner.x() - 3, corner.y() - 3, 6, 6))
            self._chip(painter, rect.left(), rect.top() - 4, REGIONS[key]['title'], color, above=True)
            if key in self.readouts:
                self._chip(painter, rect.left(), rect.bottom() + 4, self.readouts[key], color, above=False)

    def _chip(self, painter, x, y, text, color, above):
        font = QFont('Segoe UI', 9, QFont.DemiBold)
        painter.setFont(font)
        metrics = painter.fontMetrics()
        w, h = metrics.horizontalAdvance(text) + 12, metrics.height() + 4
        rect = QRectF(x, y - h if above else y, w, h)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(color.red(), color.green(), color.blue(), 235))
        painter.drawRoundedRect(rect, 5, 5)
        painter.setPen(QColor(10, 14, 20))
        painter.drawText(rect, Qt.AlignCenter, text)

    # -- mouse --------------------------------------------------------------------
    def _hit(self, pos):
        for key in reversed(ORDER):
            rect = self.boxes[key]
            outer = rect.adjusted(-HANDLE, -HANDLE, HANDLE, HANDLE)
            if not outer.contains(pos):
                continue
            edges = set()
            if abs(pos.x() - rect.left()) <= HANDLE:
                edges.add('l')
            elif abs(pos.x() - rect.right()) <= HANDLE:
                edges.add('r')
            if abs(pos.y() - rect.top()) <= HANDLE:
                edges.add('t')
            elif abs(pos.y() - rect.bottom()) <= HANDLE:
                edges.add('b')
            return key, (frozenset(edges) if edges else 'move')
        return None, None

    def _cursor_for(self, mode):
        if mode == 'move':
            return Qt.SizeAllCursor
        if mode in (frozenset('lt'), frozenset('rb')):
            return Qt.SizeFDiagCursor
        if mode in (frozenset('rt'), frozenset('lb')):
            return Qt.SizeBDiagCursor
        if mode in (frozenset('l'), frozenset('r')):
            return Qt.SizeHorCursor
        if mode in (frozenset('t'), frozenset('b')):
            return Qt.SizeVerCursor
        return Qt.ArrowCursor

    def mousePressEvent(self, event):
        if event.button() != Qt.LeftButton:
            return
        key, mode = self._hit(QPointF(event.pos()))
        if key:
            self.active, self.mode = key, mode
            self.grab_origin = QPointF(event.pos())
            self.box_origin = QRectF(self.boxes[key])

    def mouseMoveEvent(self, event):
        pos = QPointF(event.pos())
        if self.active is None:
            _key, mode = self._hit(pos)
            self.setCursor(self._cursor_for(mode))
            return
        dx, dy = pos.x() - self.grab_origin.x(), pos.y() - self.grab_origin.y()
        r = QRectF(self.box_origin)
        if self.mode == 'move':
            r.translate(dx, dy)
            r.moveLeft(max(0, min(r.left(), self.width() - r.width())))
            r.moveTop(max(0, min(r.top(), self.height() - r.height())))
        else:
            if 'l' in self.mode:
                r.setLeft(min(r.left() + dx, r.right() - MIN_W))
            if 'r' in self.mode:
                r.setRight(max(r.right() + dx, r.left() + MIN_W))
            if 't' in self.mode:
                r.setTop(min(r.top() + dy, r.bottom() - MIN_H))
            if 'b' in self.mode:
                r.setBottom(max(r.bottom() + dy, r.top() + MIN_H))
            r = r.intersected(QRectF(self.rect()))
        self.boxes[self.active] = r
        self.update()

    def mouseReleaseEvent(self, event):
        self.active = self.mode = None
