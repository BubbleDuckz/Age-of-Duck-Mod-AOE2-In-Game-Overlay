import unittest
from pathlib import Path
from unittest.mock import patch
from PIL import Image
from PyQt5.QtCore import QObject
from PyQt5.QtWidgets import QApplication, QMenu
from tc_reminder.population import PopulationReader
from tc_reminder.integration import TCController

app = QApplication.instance() or QApplication([])
ROOT = Path(__file__).parent


class HousedFallbackTests(unittest.TestCase):
    def test_scaled_hud_population_is_read_with_valid_population_constraints(self):
        # Captured from a 3072x1728 game: the loose glyph matches used to be rejected (None).
        canvas = Image.new('RGB', (2560, 140))
        canvas.paste(Image.open(ROOT / 'fixtures' / 'population-20-20-scaled-hud.png').convert('RGB'), (450, 15))
        self.assertEqual(PopulationReader().read(canvas), (20, 20))

    def test_blank_region_is_not_a_population(self):
        self.assertIsNone(PopulationReader().read(Image.new('RGB', (2560, 140))))

    def test_blocked_queue_icons_raise_housed_after_one_second_and_bridge_flicker(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp, patch('tc_reminder.native.single_instance', return_value=True):
            c = TCController(app, QMenu(), Path(tmp) / 't.json')
            c.timer.stop()
            self.assertEqual(c.queue_blocked(True, 10.0), '')       # just seen: wait for persistence
            self.assertEqual(c.queue_blocked(True, 11.1), 'Housed')
            self.assertEqual(c.queue_blocked(False, 12.0), 'Housed')  # clock flicker is bridged
            self.assertEqual(c.queue_blocked(False, 13.2), '')        # gone for over 2 s
            self.assertEqual(c.queue_blocked(False, 20.0), '')
            c.close()


if __name__ == '__main__':
    unittest.main()
