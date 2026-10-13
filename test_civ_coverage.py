import json
import tempfile
import unittest
from pathlib import Path

from PyQt5.QtWidgets import QApplication

from AgeofDuck import CIV_ABBREVIATIONS
from recs_provider import canonical_civ
from tooltip import CivMatchupPanel

app = QApplication.instance() or QApplication([])
ROOT = Path(__file__).parent
CATALOG = json.loads((ROOT / 'techtree_data.json').read_text(encoding='utf-8'))
COUNTERS = json.loads((ROOT / 'unit_counters_v2.json').read_text(encoding='utf-8'))
ICONS = json.loads((ROOT / 'UnitIcons' / 'manifest.json').read_text(encoding='utf-8'))
ECONOMY = {'Villager', 'Trade Cart', 'Trade Cog', 'Fishing Ship', 'Transport Ship'}


class CivCoverageTests(unittest.TestCase):
    def test_every_catalog_civ_is_fully_supported(self):
        codes = {}
        for civ, data in CATALOG['civs'].items():
            self.assertTrue((ROOT / 'CivIcons' / f'{civ}_AoE2.webp').is_file(), f'{civ}: emblem missing')
            self.assertIn(civ, CIV_ABBREVIATIONS, f'{civ}: badge abbreviation missing')
            codes.setdefault(CIV_ABBREVIATIONS[civ], []).append(civ)
            self.assertTrue(data['civTeamBonus'] and data['civStrategy'], civ)
            units = {u for group in data['unitsAvailable'].values() for u, ok in group.items() if ok}
            self.assertTrue(units, civ)
            for unit in units:
                self.assertTrue(CATALOG['units'][unit]['unitDescription'], (civ, unit))
                self.assertIn(unit, COUNTERS['units'], (civ, unit))
                if unit not in ECONOMY:
                    self.assertIn(unit, ICONS, (civ, unit, 'portrait missing'))
        self.assertEqual({c: v for c, v in codes.items() if len(v) > 1}, {}, 'duplicate badge abbreviations')

    def test_provider_civ_names_are_matched_to_the_catalog(self):
        for given, expected in (('Saxons', 'Saxons'), ('saxon', 'Saxons'), ('Varangian', 'Varangians'), ('TUPI', 'Tupi'),
                                ('Danes', 'Danes'), ('Maya', 'Mayans'), ('Muiscas', 'Muisca'), ('Mapuches', 'Mapuche')):
            self.assertEqual(canonical_civ(given), expected, given)
        self.assertEqual(canonical_civ('Some Future Civ'), 'Some Future Civ')
        self.assertEqual(canonical_civ(''), '')

    def test_new_civ_panel_shows_units_and_counters(self):
        with tempfile.TemporaryDirectory() as tmp:
            panel = CivMatchupPanel(assets_root=str(ROOT), strategies_path=str(Path(tmp) / 's.json'))
            for civ in ('Danes', 'Saxons', 'Shu', 'Wu', 'Wei', 'Varangians'):
                panel.select_civ(civ, player_civ='Saxons')
                self.assertEqual(panel.current_civ, civ)
                self.assertTrue(panel.unit_browser.category_buttons, civ)
                self.assertTrue(panel.unit_browser.unit_buttons, civ)
            panel.close()

    def test_unique_units_strong_vs_the_selected_unit_are_offered_as_counters(self):
        with tempfile.TemporaryDirectory() as tmp:
            panel = CivMatchupPanel(assets_root=str(ROOT), strategies_path=str(Path(tmp) / 's.json'))
            def uniques(me, selected):
                panel.select_civ('Saxons', player_civ=me)
                seen = {u for _name, units in panel._class_counters(selected) for u in units}
                return {u for _title, units in panel._unique_counters(selected, seen) for u in units}
            self.assertIn('E. Varangian Guard', uniques('Saxons', 'Knight'))        # "Strong vs. Cavalry"
            self.assertIn('E. Varangian Guard', uniques('Saxons', 'Hussar'))
            self.assertIn('Elite Genoese Crossbowman', uniques('Italians', 'Paladin'))
            self.assertIn('Elite Camel Archer', uniques('Berbers', 'Cavalry Archer'))   # "Strong vs. Mounted Archers"
            self.assertNotIn('E. Varangian Guard', uniques('Franks', 'Knight'))     # not buildable by Franks
            self.assertNotIn('E. Varangian Guard', uniques('Saxons', 'Archer'))     # not strong vs archers
            panel.close()

    def test_every_unique_unit_description_that_names_a_unit_class_is_understood(self):
        classy = ('cavalry', 'infantry', 'archery units', 'foot archers', 'ranged soldiers', 'siege weapons',
                  'mounted', 'monks', 'camel riders', 'skirmisher', 'spearman', 'gunpowder', 'close range')
        import re
        for name, entry in COUNTERS['units'].items():
            if not entry['unique']:
                continue
            text = ' '.join(re.findall(r'(?i)strong vs\.?\s*[^.]*', CATALOG['units'][name]['unitDescription'])).lower()
            if any(word in text for word in classy):
                self.assertTrue(entry['strong_vs'], (name, text))

    def test_unknown_civ_explains_itself(self):
        with tempfile.TemporaryDirectory() as tmp:
            panel = CivMatchupPanel(assets_root=str(ROOT), strategies_path=str(Path(tmp) / 's.json'))
            panel.select_civ('Zorblings')
            self.assertIn('No unit data for Zorblings', panel.hint.text())
            panel.clear_selection()
            self.assertNotIn('Zorblings', panel.hint.text())
            panel.close()


if __name__ == '__main__':
    unittest.main()
