import unittest
from pathlib import Path

from PIL import Image

from build_order_core import Progress, load_order
from hud_regions import HudRegions, ORDER, REGIONS
from tc_reminder.vision import Detector
from villager_reader import VillagerReader

ROOT = Path(__file__).parent
SAMPLES = ROOT / 'tc_reminder' / 'samples'
# Boxes drawn on a 3072x1728 game (window fractions), as saved by the set-up screen.
USER_BOXES = {
    'population': (0.17578125, 0.010416666666666666, 0.20930989583333334, 0.02789351851851852),
    'villagers': (0.16015625, 0.022222222222222223, 0.175390625, 0.034027777777777775),
    'clock': (0.33203125, 0.003472222222222222, 0.35703124999999997, 0.016666666666666666),
    'queue': (0.0, 0.04027777777777777, 0.1171875, 0.06597222222222222),
}


def default_boxes(margin):
    result = {}
    for key in ORDER:
        x0, y0, x1, y1 = REGIONS[key]['default']
        m = margin if key != 'queue' else 0
        result[key] = ((x0 - m) / 2560, max(0, y0 - m) / 1440, (x1 + m) / 2560, (y1 + m) / 1440)
    return result


class DigitTests(unittest.TestCase):
    def test_two_digit_counts_never_lose_a_digit_in_loose_boxes(self):
        reader = VillagerReader()
        for name, expected in (('foundation-five.png', 48), ('independent-four.png', None)):
            frame = Image.open(SAMPLES / name).convert('RGB')
            truth = reader.read(frame)
            if expected is not None:
                self.assertEqual(truth, expected)
            if truth is None:
                continue
            for scale in (1.0, 1.5, 2.0):
                raw = frame.resize((round(2560 * scale), round(1440 * scale)), Image.Resampling.BICUBIC) if scale != 1 else frame
                for margin in (0, 6):
                    regions = HudRegions()
                    regions.boxes = default_boxes(margin)
                    read = reader.read(regions.build_canvas(raw))
                    self.assertIn(read, (None, truth), (name, scale, margin))   # unreadable is fine, wrong is not


class ProgressTests(unittest.TestCase):
    def progress(self):
        return Progress(load_order(ROOT / 'BuildOrders' / 'Example-Archer-Opening.json'))

    def test_normal_increments_need_two_agreeing_reads(self):
        p = self.progress()
        p.observe(7, True); p.observe(7, True)
        self.assertEqual(p.high, 7)
        p.observe(8, True); self.assertEqual(p.high, 7)
        p.observe(8, True); self.assertEqual(p.high, 8)

    def test_big_jumps_are_probably_misreads_and_need_more_evidence(self):
        p = self.progress()
        p.observe(7, True); p.observe(7, True)
        for _ in range(3):
            p.observe(18, True)
        self.assertEqual(p.high, 7)          # three reads of 18 are not enough for +11
        p.observe(18, True)
        self.assertEqual(p.high, 18)
        q = self.progress()
        q.observe(7, True); q.observe(7, True)
        q.observe(9, True); q.observe(9, True); self.assertEqual(q.high, 9)   # two at once (two TCs) is normal
        q.observe(12, True); q.observe(12, True); self.assertEqual(q.high, 9)
        q.observe(12, True); self.assertEqual(q.high, 12)


class QueueTileTests(unittest.TestCase):
    def queue(self, name):
        crop = Image.open(ROOT / 'fixtures' / name).convert('RGB')
        raw = Image.new('RGB', (3072, 1728))
        raw.paste(crop, (0, 0))
        regions = HudRegions()
        regions.boxes = USER_BOXES
        detector = Detector()
        return detector.analyze_queue(regions.build_canvas(raw))

    def test_age_up_progress_and_counted_queue_tiles_are_activity_not_idle(self):
        result = self.queue('live-queue-progress-tiles.png')
        # Villager tile, a green research tile and an unrecognised tile: a lone TC is clearly busy.
        self.assertGreaterEqual(result['busy_upper_bound'], 3)
        self.assertGreaterEqual(result['research'], 1)

    def test_activity_is_bounded_by_the_tiles_on_screen(self):
        # Four tiles are visible (the gold one is only waiting): never more activity than tiles.
        self.assertLessEqual(self.queue('live-queue-progress-tiles.png')['busy_upper_bound'], 4)


if __name__ == '__main__':
    unittest.main()
