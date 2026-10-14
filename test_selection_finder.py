import unittest
from pathlib import Path

from PIL import Image

from tc_reminder.selection import SelectionFinder

SAMPLES = Path(__file__).parent / 'tc_reminder' / 'samples'
# Ground truth from the screenshots: selected Town Centres (None = no Town Centre selected).
EXPECTED = {
    'selected-three.png': 3, 'independent-four.png': 4, 'foundation-five.png': 5, 'live-paused-three.png': 3,
    'research-one-tc.png': 1, 'independent-single.png': 1, 'age-check-live.png': 1,
    'pop-30-live-0.png': None, 'menu.png': None, 'build-order-20-live.png': None, 'housed-three.png': None,
}


def at(name, scale):
    image = Image.open(SAMPLES / name).convert('RGB')
    if scale != 1.0:
        image = image.resize((round(image.width * scale), round(image.height * scale)), Image.Resampling.BICUBIC)
    return image


class SelectionFinderTests(unittest.TestCase):
    def test_count_is_the_same_at_other_resolutions_and_interface_sizes(self):
        for scale in (1.0, 1.2, 1.5, 2.0, 0.75):
            for name, expected in EXPECTED.items():
                self.assertEqual(SelectionFinder().read(at(name, scale), now=0), expected, (name, scale))

    def test_finds_the_bell_scale_and_keeps_it_for_cheap_later_frames(self):
        finder = SelectionFinder()
        self.assertEqual(finder.read(at('selected-three.png', 1.5), now=0), 3)
        self.assertAlmostEqual(finder.scale, 1.5, delta=0.05)
        # Selection cleared: nothing reported, but the remembered size still guides the next look.
        self.assertIsNone(finder.read(at('pop-30-live-0.png', 1.5), now=0.5))
        self.assertAlmostEqual(finder.known_scale, 1.5, delta=0.05)
        self.assertEqual(finder.read(at('independent-four.png', 1.5), now=1.0), 4)

    def test_widescreen_frames_use_the_same_corner(self):
        # Ultrawide: extra width on the right only; the bottom-left panel keeps its place.
        base = at('selected-three.png', 1.0)
        wide = Image.new('RGB', (3440, 1440))
        wide.paste(base, (0, 0))
        self.assertEqual(SelectionFinder().read(wide, now=0), 3)


if __name__ == '__main__':
    unittest.main()
