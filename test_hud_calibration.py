import unittest
from pathlib import Path

from PIL import Image
from PyQt5.QtCore import QPoint, QPointF, Qt
from PyQt5.QtGui import QMouseEvent
from PyQt5.QtWidgets import QApplication

from hud_calibration import HudCalibrator
from hud_regions import HudRegions, REGIONS, snap_to_text
from tc_reminder.vision import Detector
from villager_reader import VillagerReader

app = QApplication.instance() or QApplication([])
ROOT = Path(__file__).parent


def game_frame():
    strip = Image.open(ROOT / 'fixtures' / 'hud-strip-normal.png').convert('RGB')
    raw = Image.new('RGB', (2560, 1440))
    raw.paste(strip, (0, 0))
    return raw


def mouse(kind, x, y):
    return QMouseEvent(kind, QPointF(x, y), Qt.LeftButton, Qt.LeftButton, Qt.NoModifier)


class CalibratorTests(unittest.TestCase):
    def make(self):
        regions = HudRegions()
        regions.boxes = {}
        cal = HudCalibrator((0, 0, (0, 0, 2560, 1440)), regions, Detector(), VillagerReader(), frame=game_frame())
        self.addCleanup(cal.close)
        cal.snap_check.setChecked(False)
        return cal

    def drag(self, cal, start, end):
        cal.mousePressEvent(mouse(QMouseEvent.MouseButtonPress, *start))
        cal.mouseMoveEvent(mouse(QMouseEvent.MouseMove, *end))
        cal.mouseReleaseEvent(mouse(QMouseEvent.MouseButtonRelease, *end))

    def test_clicking_empty_space_puts_selected_box_there(self):
        cal = self.make()
        cal.select('clock')
        before = cal.boxes['clock'].size()
        self.drag(cal, (cal.width() * 0.5, cal.height() * 0.5), (cal.width() * 0.5, cal.height() * 0.5))
        center = cal.boxes['clock'].center()
        self.assertAlmostEqual(center.x(), cal.width() * 0.5, delta=1)
        self.assertAlmostEqual(center.y(), cal.height() * 0.5, delta=1)
        self.assertEqual(cal.boxes['clock'].size(), before)

    def test_small_box_can_be_grabbed_slightly_outside_and_moved(self):
        cal = self.make()
        rect = cal.boxes['villagers']
        start = (rect.left() - 6, rect.top() - 6)     # outside the box, inside the grab margin
        cal.select('population')
        self.drag(cal, start, (start[0] + 30, start[1] + 20))
        self.assertEqual(cal.selected, 'villagers')
        self.assertAlmostEqual(cal.boxes['villagers'].left(), rect.left() + 30, delta=1)

    def test_corner_handle_resizes_and_keys_and_wheel_work(self):
        cal = self.make()
        cal.select('queue')
        rect = cal.boxes['queue']
        self.drag(cal, (rect.right(), rect.bottom()), (rect.right() + 40, rect.bottom() + 12))
        self.assertAlmostEqual(cal.boxes['queue'].width(), rect.width() + 40, delta=1)
        self.assertAlmostEqual(cal.boxes['queue'].left(), rect.left(), delta=1)
        before = cal.boxes['queue'].left()
        cal.keyPressEvent(type('E', (), {'key': lambda s: Qt.Key_Right, 'modifiers': lambda s: Qt.ShiftModifier})())
        self.assertAlmostEqual(cal.boxes['queue'].left(), before + 10, delta=0.01)

    def test_snap_fits_box_to_the_text(self):
        raw = game_frame()
        x0, y0, x1, y1 = REGIONS['population']['canon']
        rough = (x0 - 6, y0 - 4, x1 + 6, y1 + 4)
        fitted = snap_to_text(raw, rough, 'population')
        self.assertIsNotNone(fitted)
        self.assertEqual(fitted, (x0 - 2, y0 - 2, x1 + 2, y1 + 2))
        clock = REGIONS['clock']['default']       # sloppy box that also covers the label next to the clock
        cx0, cy0, cx1, cy1 = snap_to_text(raw, (clock[0], clock[1], clock[2] + 20, clock[3]), 'clock')
        self.assertLessEqual(cx1, 916)
        self.assertGreaterEqual(cx0, 846)
        self.assertIsNone(snap_to_text(raw, (1200, 800, 1260, 830), 'population'))
        self.assertIsNone(snap_to_text(raw, rough, 'queue'))

    def test_test_read_runs_on_frozen_frame(self):
        cal = self.make()
        cal.test_read()
        self.assertEqual(set(cal.readouts), set(cal.boxes))


if __name__ == '__main__':
    unittest.main()
