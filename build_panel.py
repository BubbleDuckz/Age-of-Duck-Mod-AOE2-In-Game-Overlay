"""In-game build-order window: translucent title bar, done / current / upcoming steps."""
from PyQt5.QtCore import QRectF, Qt, QTimer
from PyQt5.QtGui import QColor, QCursor, QFont, QLinearGradient, QPainter, QPainterPath, QPen
from PyQt5.QtWidgets import QApplication, QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from screen_placement import visible_position
from tc_reminder import native
from ui_bits import ElidedLabel, SizeButton

GOLD = "#FFD166"
GOLD_TEXT = "#FFF0BC"


class StepRow(QFrame):
    """One build-order step: a villager-count badge and the instruction text."""

    def __init__(self, kind, parent=None):
        super().__init__(parent)
        self.kind = kind
        self.setObjectName("step_" + kind)
        layout = QHBoxLayout(self)
        layout.setSpacing(8)
        self.badge = QLabel("")
        self.badge.setAlignment(Qt.AlignCenter)
        self.badge.setObjectName("badge_" + kind)
        self.label = QLabel("")
        self.label.setTextFormat(Qt.PlainText)
        self.label.setWordWrap(True)
        self.label.setObjectName("text_" + kind)
        layout.addWidget(self.badge, 0, Qt.AlignTop)
        layout.addWidget(self.label, 1)
        self._id = ""
        self._text = ""
        self.set_metrics(1.0)

    def set_metrics(self, scale):
        margin = round((7 if self.kind == "current" else 3) * scale)
        self.layout().setContentsMargins(round(7 * scale), margin, round(7 * scale), margin)
        self.badge.setFixedWidth(round(38 * scale))

    def set_step(self, step):
        self._id, self._text = step.id, step.text
        self.badge.setText(step.id)
        self.badge.show()
        self.label.setText(step.text)

    def setText(self, text):
        """Plain message without a badge (used for waiting / empty states)."""
        self._id, self._text = "", text
        self.badge.hide()
        self.label.setText(text)

    def text(self):
        return f"{self._id}  ·  {self._text}" if self._id else self._text

    def setFont(self, font):
        super().setFont(font)
        self.label.setFont(font)
        badge = QFont(font)
        badge.setStrikeOut(False)
        badge.setBold(True)
        badge.setPointSize(max(7, font.pointSize() - 1))
        self.badge.setFont(badge)


class BuildPanel(QWidget):
    def __init__(self, owner):
        super().__init__(None, Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.WindowDoesNotAcceptFocus)
        self.owner = owner
        self.drag = None
        self.setWindowTitle("Age of Duck — Build Orders")
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet(f"""
            QLabel {{ background: transparent; color: #EEF6FF; }}
            QLabel#caption {{ color: #9FB3C8; font-weight: 700; }}
            QLabel#count {{ color: #A7F3D0; background: rgba(167, 243, 208, 0.12);
                border: 1px solid rgba(167, 243, 208, 0.30); border-radius: 9px; padding: 1px 8px; font-weight: 700; }}
            QLabel#status {{ color: #9FB3C8; }}
            QFrame#step_done, QFrame#step_next {{ background: transparent; border: none; }}
            QFrame#step_current {{ background: rgba(255, 209, 102, 0.13); border: 1px solid rgba(255, 209, 102, 0.55);
                border-radius: 9px; }}
            QLabel#badge_done {{ color: #7D8B98; background: rgba(255, 255, 255, 0.07); border-radius: 6px; padding: 1px 0; }}
            QLabel#badge_next {{ color: #C9D6E2; border: 1px solid rgba(255, 255, 255, 0.24); border-radius: 6px; padding: 0px; }}
            QLabel#badge_current {{ color: #2A2100; background: {GOLD}; border-radius: 6px; padding: 2px 0; }}
            QLabel#text_done {{ color: #7D8B98; }}
            QLabel#text_next {{ color: #D2DCE5; }}
            QLabel#text_current {{ color: {GOLD_TEXT}; }}
        """)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Translucent title bar: also the drag handle.
        self.bar = QWidget()
        self.bar.setCursor(Qt.SizeAllCursor)
        self.bar.setToolTip("Drag to reposition the build order")
        bar_layout = QHBoxLayout(self.bar)
        bar_layout.setContentsMargins(11, 6, 7, 6)
        bar_layout.setSpacing(6)
        titles = QVBoxLayout()
        titles.setSpacing(0)
        self.caption = QLabel("BUILD ORDER")
        self.caption.setObjectName("caption")
        self.title = ElidedLabel("Select a build order")
        titles.addWidget(self.caption)
        titles.addWidget(self.title)
        bar_layout.addLayout(titles, 1)
        self.count = QLabel("Villagers ?")
        self.count.setObjectName("count")
        bar_layout.addWidget(self.count, 0, Qt.AlignVCenter)
        self.minus = SizeButton(False)
        self.plus = SizeButton(True)
        self.minus.setToolTip("Smaller build order and Idle / Housed windows")
        self.plus.setToolTip("Larger build order and Idle / Housed windows")
        self.minus.clicked.connect(lambda: owner.change_panel_scale(-1))
        self.plus.clicked.connect(lambda: owner.change_panel_scale(1))
        bar_layout.addWidget(self.minus)
        bar_layout.addWidget(self.plus)
        for label in (self.caption, self.title, self.count):
            label.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.bar.mousePressEvent = self.press
        self.bar.mouseMoveEvent = self.move_drag
        self.bar.mouseReleaseEvent = self.release
        root.addWidget(self.bar)

        body = QVBoxLayout()
        body.setContentsMargins(8, 6, 8, 9)
        body.setSpacing(3)
        self.body_layout = body
        self.previous = [StepRow("done") for _ in range(3)]
        for row in self.previous:
            body.addWidget(row)
        self.instruction = StepRow("current")
        body.addWidget(self.instruction)
        self.next = QLabel("")
        self.next.setObjectName("status")
        self.next.setTextFormat(Qt.PlainText)
        self.next.setWordWrap(True)
        self.next.setContentsMargins(8, 0, 8, 2)
        body.addWidget(self.next)
        self.upcoming = [StepRow("next") for _ in range(3)]
        for row in self.upcoming:
            body.addWidget(row)
        root.addLayout(body)

        self.hwnd = int(self.winId())
        flags = native.u.GetWindowLongPtrW(self.hwnd, -20) | 0x80000 | 0x20 | 0x80 | 0x08000000
        native.u.SetWindowLongPtrW(self.hwnd, -20, flags)
        self.hit = QTimer(self)
        self.hit.timeout.connect(self.hit_test)
        self.hit.start(40)
        self.set_scale(owner.scale)

    # -- painting -------------------------------------------------------------
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        radius = 12
        body = QLinearGradient(rect.topLeft(), rect.bottomRight())
        body.setColorAt(0, QColor(14, 23, 33, 168))
        body.setColorAt(1, QColor(24, 38, 53, 158))
        painter.setBrush(body)
        painter.setPen(QPen(QColor(255, 255, 255, 46), 1))
        painter.drawRoundedRect(rect, radius, radius)
        # Lighter, more transparent strip behind the title bar.
        bar_rect = QRectF(rect.left(), rect.top(), rect.width(), self.bar.height())
        strip = QPainterPath()
        strip.addRoundedRect(bar_rect.adjusted(0, 0, 0, radius), radius, radius)
        clip = QPainterPath()
        clip.addRect(bar_rect)
        painter.setClipPath(strip.intersected(clip))
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(255, 255, 255, 30))
        painter.drawRect(bar_rect)
        painter.setClipping(False)
        painter.setPen(QPen(QColor(255, 255, 255, 38), 1))
        painter.drawLine(int(bar_rect.left() + 8), int(bar_rect.bottom()), int(bar_rect.right() - 8), int(bar_rect.bottom()))

    # -- behaviour ------------------------------------------------------------
    def hit_test(self):
        pos = self.mapFromGlobal(QCursor.pos())
        interactive = self.bar.geometry().contains(pos) or self.drag is not None
        flags = native.u.GetWindowLongPtrW(self.hwnd, -20)
        native.u.SetWindowLongPtrW(self.hwnd, -20, flags & ~0x20 if interactive else flags | 0x20)

    def set_scale(self, scale):
        self.setFixedWidth(round(350 * scale))
        base = max(8, round(10 * scale))
        self.title.setFont(QFont("Segoe UI", base + 1, QFont.Bold))
        caption = QFont("Segoe UI", max(7, base - 2), QFont.Bold)
        caption.setLetterSpacing(QFont.AbsoluteSpacing, 1.3)
        self.caption.setFont(caption)
        self.count.setFont(QFont("Segoe UI", max(7, base - 1), QFont.Bold))
        self.next.setFont(QFont("Segoe UI", max(7, base - 1)))
        for row in self.previous:
            font = QFont("Segoe UI", base)
            font.setStrikeOut(True)
            row.setFont(font)
            row.set_metrics(scale)
        for row in self.upcoming:
            row.setFont(QFont("Segoe UI", base, QFont.Normal))
            row.set_metrics(scale)
        self.instruction.setFont(QFont("Segoe UI", max(9, round(12 * scale)), QFont.Bold))
        self.instruction.set_metrics(scale)
        side = max(18, round(20 * scale))
        for button in (self.minus, self.plus):
            button.setFixedSize(side, side)
        self.adjustSize()

    def show_progress(self, progress, safe):
        anchor = progress.current or progress.last
        steps = progress.order.steps
        if anchor:
            index = steps.index(anchor)
            previous = steps[max(0, index - 3):index]
            upcoming = steps[index + 1:index + 4]
            self.instruction.set_step(anchor)
        else:
            previous = []
            upcoming = [s for s in steps if progress.high is None or s.villagers > progress.high][:3]
            self.instruction.setText("Waiting for the next villager" if upcoming else "Build order complete")
        # Newest "done" step sits next to the current one, so right-align the shorter lists.
        for rows, items, align_end in ((self.previous, previous, True), (self.upcoming, upcoming, False)):
            for i, row in enumerate(rows):
                source = i - (len(rows) - len(items)) if align_end else i
                if 0 <= source < len(items):
                    row.set_step(items[source])
                    row.setVisible(True)
                else:
                    row.setVisible(False)
        self.layout().activate()
        self.adjustSize()

    def press(self, event):
        if event.button() == Qt.LeftButton:
            self.drag = event.globalPos() - self.pos()

    def move_drag(self, event):
        if self.drag is not None:
            self.move(event.globalPos() - self.drag)

    def release(self, event):
        if self.drag is not None:
            self.owner.prefs["position"] = [self.x(), self.y()]
            self.owner.save()
        self.drag = None

    def place(self):
        if self.drag is not None:
            return
        pos = self.owner.prefs.get("position")
        if isinstance(pos, list) and len(pos) == 2:
            self.move(*map(int, pos))
        else:
            area = QApplication.primaryScreen().availableGeometry()
            self.move(area.left() + 20, area.top() + 160)
        self.move(visible_position(self.geometry(), [s.availableGeometry() for s in QApplication.screens()]))
