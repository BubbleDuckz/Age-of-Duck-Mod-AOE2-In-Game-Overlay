"""Small painted widgets shared by the in-game companion windows and controls."""
from PyQt5.QtCore import QPointF, QRectF, QSize, Qt
from PyQt5.QtGui import QBrush, QColor, QFontMetrics, QPainter, QPainterPath, QPen, QPolygonF, QRadialGradient
from PyQt5.QtWidgets import QLabel, QPushButton

GREEN = QColor("#4ADE80")
RED = QColor("#F87171")
FG = QColor("#EEF6FF")
MUTED = QColor("#9FB3C8")


def _alpha(color, alpha):
    result = QColor(color)
    result.setAlpha(alpha)
    return result


class StatusLightButton(QPushButton):
    """Pill button with a green/red status light: green = shown, red = hidden."""

    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.light_on = False
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.NoFocus)

    def set_light(self, on):
        on = bool(on)
        if on != self.light_on:
            self.light_on = on
            self.update()

    def sizeHint(self):
        metrics = QFontMetrics(self.font())
        return QSize(metrics.horizontalAdvance(self.text()) + 38, max(24, metrics.height() + 10))

    def minimumSizeHint(self):
        return self.sizeHint()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHints(QPainter.Antialiasing | QPainter.TextAntialiasing)
        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        enabled = self.isEnabled()
        hover = enabled and self.underMouse()
        pressed = enabled and self.isDown()
        painter.setBrush(QColor(255, 255, 255, 52 if pressed else 36 if hover else 17 if enabled else 8))
        painter.setPen(QPen(QColor(255, 255, 255, 60 if hover else 36 if enabled else 18), 1))
        painter.drawRoundedRect(rect, 7, 7)

        color = GREEN if self.light_on else RED
        cx, cy, radius = rect.left() + 14, rect.center().y(), 4.5
        if enabled:
            glow = QRadialGradient(QPointF(cx, cy), radius * 2.6)
            glow.setColorAt(0, _alpha(color, 120))
            glow.setColorAt(1, _alpha(color, 0))
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(glow))
            painter.drawEllipse(QPointF(cx, cy), radius * 2.6, radius * 2.6)
        painter.setBrush(_alpha(color, 255 if enabled else 90))
        painter.setPen(QPen(_alpha(QColor(0, 0, 0), 90), 1))
        painter.drawEllipse(QPointF(cx, cy), radius, radius)

        painter.setPen(FG if enabled else QColor(101, 113, 125))
        text_rect = rect.adjusted(26, 0, -8, 0)
        painter.drawText(text_rect, Qt.AlignVCenter | Qt.AlignLeft, self.text())


class SizeButton(QPushButton):
    """Tiny square +/- control drawn with crisp strokes."""

    def __init__(self, plus, parent=None):
        super().__init__(parent)
        self.plus = plus
        self.setFixedSize(20, 20)
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.NoFocus)

    def sizeHint(self):
        return self.size()

    def minimumSizeHint(self):
        return self.size()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        hover = self.underMouse()
        painter.setBrush(QColor(255, 255, 255, 40 if hover else 16))
        painter.setPen(QPen(QColor(255, 255, 255, 70 if hover else 36), 1))
        painter.drawRoundedRect(rect, 6, 6)
        painter.setPen(QPen(FG if hover else MUTED, 1.6, Qt.SolidLine, Qt.RoundCap))
        c = rect.center()
        arm = rect.width() * 0.2
        painter.drawLine(QPointF(c.x() - arm, c.y()), QPointF(c.x() + arm, c.y()))
        if self.plus:
            painter.drawLine(QPointF(c.x(), c.y() - arm), QPointF(c.x(), c.y() + arm))


class SpeakerButton(QPushButton):
    """Speaker glyph: waves grow with volume; muted draws a red slash."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.muted = False
        self.volume = 100
        self.setFixedSize(26, 22)
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.NoFocus)

    def sizeHint(self):
        return self.size()

    def minimumSizeHint(self):
        return self.size()

    def set_state(self, muted, volume):
        muted, volume = bool(muted), int(volume)
        if (muted, volume) != (self.muted, self.volume):
            self.muted, self.volume = muted, volume
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        hover = self.underMouse()
        if hover:
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(255, 255, 255, 26))
            painter.drawRoundedRect(QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5), 6, 6)
        silent = self.muted or self.volume <= 0
        tone = RED if self.muted else (FG if hover else MUTED)
        cx, cy = self.width() / 2.0 - 2, self.height() / 2.0
        painter.setPen(Qt.NoPen)
        painter.setBrush(tone)
        body = QPainterPath()
        body.addPolygon(QPolygonF([
            QPointF(cx - 7, cy - 2.6), QPointF(cx - 3.6, cy - 2.6), QPointF(cx + 0.8, cy - 6.4),
            QPointF(cx + 0.8, cy + 6.4), QPointF(cx - 3.6, cy + 2.6), QPointF(cx - 7, cy + 2.6),
        ]))
        painter.drawPath(body)
        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(tone, 1.5, Qt.SolidLine, Qt.RoundCap))
        if silent:
            painter.drawLine(QPointF(cx + 3.6, cy - 3.4), QPointF(cx + 9.2, cy + 3.4))
            painter.drawLine(QPointF(cx + 9.2, cy - 3.4), QPointF(cx + 3.6, cy + 3.4))
        else:
            waves = 1 if self.volume < 34 else 2 if self.volume < 67 else 3
            for index in range(waves):
                reach = 2.6 + index * 2.5
                painter.drawArc(QRectF(cx + 1.4 - reach, cy - reach, reach * 2, reach * 2), -45 * 16, 90 * 16)


class ElidedLabel(QLabel):
    """Single-line label that shortens with an ellipsis rather than widening its window."""

    def __init__(self, text="", parent=None):
        super().__init__(parent)
        self._full = ""
        self.setMinimumWidth(0)
        self.setText(text)

    def setText(self, text):
        self._full = text or ""
        super().setText(self._full)
        self.setToolTip(self._full)
        self.update()

    def text(self):
        return self._full

    def minimumSizeHint(self):
        return QSize(0, super().minimumSizeHint().height())

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setFont(self.font())
        painter.setPen(self.palette().color(self.foregroundRole()))
        shown = QFontMetrics(self.font()).elidedText(self._full, Qt.ElideRight, self.width())
        painter.drawText(self.rect(), int(self.alignment()) | Qt.AlignVCenter, shown)
