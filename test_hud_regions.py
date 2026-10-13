import tempfile
import unittest
from pathlib import Path

from PIL import Image

from hud_regions import FlashTracker, HudRegions, ORDER, REGIONS, describe
from tc_reminder.vision import Detector
from villager_reader import VillagerReader

ROOT = Path(__file__).parent


def frame(name, scale=1.0, margin=0):
    """A 1440p-calibrated game frame (strip at the top, black below), optionally rescaled."""
    strip = Image.open(ROOT / 'fixtures' / name).convert('RGB')
    raw = Image.new('RGB', (2560, 1440))
    raw.paste(strip, (0, 0))
    if scale != 1.0:
        raw = raw.resize((round(2560 * scale), round(1440 * scale)), Image.Resampling.BICUBIC)
    return raw


def boxes_for(raw, margin=0):
    """Boxes drawn over the HUD items, as window fractions; `margin` px of slop in the 1440p frame."""
    w, h = 2560, 1440
    result = {}
    for key in ORDER:
        x0, y0, x1, y1 = REGIONS[key]['default']
        m = margin if key != 'queue' else 0
        result[key] = ((x0 - m) / w, max(0, y0 - m) / h, (x1 + m) / w, (y1 + m) / h)
    return result


class RemapTests(unittest.TestCase):
    def read(self, raw, margin=0):
        regions = HudRegions()
        regions.boxes = boxes_for(raw, margin)
        canvas = regions.build_canvas(raw)
        return canvas, Detector().population_reader.read(canvas), VillagerReader().read(canvas)

    def test_readings_survive_other_resolutions_and_loose_boxes(self):
        # Up-scaled captures are faithful; a 1440p frame shrunk to 1080p is blurrier than a real 1080p HUD.
        for scale in (1.0, 1.2, 1.5, 2.0):
            for margin in (0, 3, 6):
                _canvas, population, villagers = self.read(frame('hud-strip-normal.png', scale), margin)
                self.assertEqual(population, (20, 20), (scale, margin))
                self.assertEqual(villagers, 19, (scale, margin))

    def test_remapped_frame_counts_as_gameplay_without_skin_anchors(self):
        detector = Detector()
        detector.regions = HudRegions()
        detector.regions.boxes = boxes_for(None)
        result = detector.analyze(detector.normalize_frame(frame('hud-strip-normal.png', 1.2)), now=1.0)
        self.assertTrue(result['gameplay'])
        self.assertEqual(result['population'], (20, 20))

    def test_blank_boxes_are_not_gameplay(self):
        detector = Detector()
        detector.regions = HudRegions()
        detector.regions.boxes = boxes_for(None)
        result = detector.analyze(detector.normalize_frame(Image.new('RGB', (2560, 1440))), now=1.0)
        self.assertFalse(result['gameplay'])

    def test_housed_flash_is_a_jump_above_the_resting_colour(self):
        flashing = HudRegions()
        flashing.boxes = boxes_for(None)
        rest = flashing.build_canvas(frame('hud-strip-normal.png')).info['pop_flash_fraction']
        flash = flashing.build_canvas(frame('hud-strip-flash.png')).info['pop_flash_fraction']
        self.assertLess(rest, 0.15)
        self.assertGreater(flash, 0.3)
        tracker = FlashTracker()
        self.assertFalse(tracker.update(rest, 0.0))
        self.assertTrue(tracker.update(flash, 1.0))
        steady = FlashTracker()   # a skin that is always yellowish never alarms
        self.assertFalse(any(steady.update(0.6, t) for t in range(30)))

    def test_describe_and_persistence(self):
        raw = frame('hud-strip-normal.png', 1.2)
        text = describe(raw, boxes_for(raw), Detector(), VillagerReader())
        self.assertEqual(text['population'], '20/20')
        self.assertEqual(text['villagers'], '19')
        self.assertEqual(text['clock'], 'clock text found')
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'hud_regions.json'
            regions = HudRegions(path)
            self.assertFalse(regions.configured)
            regions.set_boxes(boxes_for(raw), (3072, 1728))
            again = HudRegions(path)
            self.assertTrue(again.configured)
            self.assertTrue(again.usable((1920, 1080)))
            self.assertFalse(again.usable((3440, 1440)))   # different aspect: boxes would land in the wrong place
            again.clear()
            self.assertFalse(HudRegions(path).configured)


if __name__ == '__main__':
    unittest.main()
