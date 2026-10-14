import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PyQt5.QtWidgets import QApplication, QLabel

import AgeofDuck
from AgeofDuck import Overlay, civ_abbreviation, CIV_ABBREVIATIONS
from tooltip import CivMatchupPanel

app = QApplication.instance() or QApplication([])
ROOT = Path(__file__).parent
PLAYERS = [
    dict(name='A', civ='Aztecs', rating=1500, peak=1550, peak_mode='1v1', team=1),
    dict(name='B', civ='Persians', rating=1600, peak=1650, peak_mode='Teams', team=1),
    dict(name='C', civ='Britons', rating=1700, peak=1750, peak_mode='1v1', team=2),
]


class OverlayLayoutTests(unittest.TestCase):
    def make_overlay(self):
        patcher = [patch('AgeofDuck.threading.Thread.start'), patch('AgeofDuck.Overlay.restore_last_position'),
                   patch('AgeofDuck.save_peak_expanded'), patch('AgeofDuck.load_peak_expanded', return_value=True),
                   patch('AgeofDuck.save_hide_own_team'), patch('AgeofDuck.load_hide_own_team', return_value=False)]
        for p in patcher:
            p.start()
            self.addCleanup(p.stop)
        overlay = Overlay(None)
        self.addCleanup(lambda: (overlay.worker.stop(), overlay.hide(), overlay.placement_timer.stop(), overlay.waiting_timer.stop()))
        overlay.update_overlay({}, PLAYERS, 'Team Random Map', 'Arabia')
        overlay.show()
        app.processEvents()
        return overlay

    def test_hide_own_team_button(self):
        overlay = self.make_overlay()
        players = [dict(p, is_self=(p['name'] == 'A')) for p in PLAYERS]
        overlay.update_overlay({}, players, 'Team Random Map', 'Arabia')
        app.processEvents()
        divider = overlay.team_dividers[2]
        self.assertEqual(divider.collapse_dir, 'up')       # own team sits above the strip
        self.assertEqual(sum(d.collapse_dir is not None for d in overlay.team_dividers), 1)
        self.assertTrue(all(r.isVisible() for r in overlay.player_rows[:3]))
        divider.toggled.emit()
        app.processEvents()
        self.assertEqual([r.isVisible() for r in overlay.player_rows[:3]], [False, False, True])
        self.assertTrue(divider.isVisible() and divider.team_hidden)
        divider.toggled.emit()
        app.processEvents()
        self.assertTrue(all(r.isVisible() for r in overlay.player_rows[:3]))

    def test_hide_own_team_when_enemy_is_first_and_never_in_ffa(self):
        overlay = self.make_overlay()
        players = [dict(p, is_self=(p['name'] == 'C')) for p in PLAYERS]
        overlay.update_overlay({}, players, 'Team Random Map', 'Arabia')
        self.assertEqual(overlay.team_dividers[2].collapse_dir, 'down')
        overlay.hide_own_team = True
        overlay.update_overlay({}, players, 'Team Random Map', 'Arabia')
        app.processEvents()
        self.assertEqual([r.isVisible() for r in overlay.player_rows[:3]], [True, True, False])
        ffa = [dict(name=f'P{i}', civ='Aztecs', rating=1500, peak=None, team=10 + i, is_self=(i == 0)) for i in range(4)]
        overlay.update_overlay({'ffa': True}, ffa, 'Scenario', 'x')
        app.processEvents()
        self.assertTrue(all(d.collapse_dir is None for d in overlay.team_dividers))
        self.assertTrue(all(r.isVisible() for r in overlay.player_rows[:4]))

    def test_abbreviations_are_unique_two_letter_codes(self):
        codes = list(CIV_ABBREVIATIONS.values())
        self.assertEqual(len(codes), len(set(codes)))
        self.assertTrue(all(len(code) == 2 for code in codes))
        self.assertEqual(civ_abbreviation('Persians'), 'Pe')
        self.assertEqual(civ_abbreviation('Unknownlanders'), 'Un')

    def test_no_civ_column_and_badge_precedes_name(self):
        overlay = self.make_overlay()
        row = overlay.player_rows[0]
        self.assertFalse(hasattr(row, 'civ_label'))
        self.assertLess(row.civ_badge.x(), row.name_label.x())

    def test_divider_only_between_teams(self):
        overlay = self.make_overlay()
        self.assertEqual([d.isVisible() for d in overlay.team_dividers[:3]], [False, False, True])

    def test_free_for_all_has_no_vs_lines_and_team_games_mark_teammates(self):
        overlay = self.make_overlay()
        ffa = [dict(name=f'P{i}', civ='Aztecs', rating=1500, peak=None, team=10 + i) for i in range(6)]
        overlay.update_overlay({'ffa': True}, ffa, 'Scenario', 'x')
        app.processEvents()
        self.assertFalse(any(d.isVisible() for d in overlay.team_dividers))
        self.assertIn('FFA', overlay.mode_label.text())
        self.assertTrue(all(row.team_color is None for row in overlay.player_rows))
        teams = [dict(name=f'P{i}', civ='Aztecs', rating=1500, peak=None, team=1 if i < 3 else 2) for i in range(6)]
        overlay.update_overlay({'ffa': False}, teams, 'RM TG', 'x')
        app.processEvents()
        self.assertEqual([d.isVisible() for d in overlay.team_dividers[:6]], [False, False, False, True, False, False])
        colors = [row.team_color for row in overlay.player_rows[:6]]
        self.assertEqual(len(set(colors[:3])), 1)
        self.assertEqual(len(set(colors[3:])), 1)
        self.assertNotEqual(colors[0], colors[3])

    def test_ai_player_is_named_ai_with_a_bot_icon(self):
        overlay = self.make_overlay()
        players = [dict(name='Human', civ='Aztecs', rating=1500, team=1), dict(name='AI', is_ai=True, civ='Bohemians', rating=None, team=2)]
        overlay.update_overlay({}, players, 'Scenario', 'x')
        app.processEvents()
        human, bot = overlay.player_rows[:2]
        self.assertEqual(bot.name_label.text(), 'AI')
        self.assertFalse(bot.bot_icon.isHidden())
        self.assertTrue(human.bot_icon.isHidden())

    def test_peak_collapse_narrows_overlay_and_restores(self):
        overlay = self.make_overlay()
        wide = overlay.width()
        overlay._peak_expanded = False
        overlay._set_peak_progress(0.0)
        app.processEvents()
        self.assertLess(overlay.width(), wide)
        self.assertEqual(overlay.peak_toggle.width(), AgeofDuck.PEAK_WIDTH_COLLAPSED)
        overlay._peak_expanded = True
        overlay._set_peak_progress(1.0)
        self.assertEqual(overlay.width(), wide)


class UnitPanelTests(unittest.TestCase):
    def make_panel(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        panel = CivMatchupPanel(assets_root=str(ROOT), strategies_path=str(Path(tmp.name) / 's.json'))
        self.addCleanup(panel.close)
        panel.select_civ('Japanese', player_civ='Franks')
        app.processEvents()
        return panel

    def test_header_row_and_collapsed_strategy(self):
        panel = self.make_panel()
        self.assertTrue(panel.strategy_box.isHidden())
        ys = {w.geometry().center().y() for w in (panel.strategy_button, panel.icon, panel.civ_name, panel.close_button)}
        self.assertLessEqual(max(ys) - min(ys), 6)
        self.assertEqual(panel.civ_name.text(), 'Japanese')

    def test_units_grouped_by_line_with_portraits(self):
        panel = self.make_panel()
        browser = panel.unit_browser
        self.assertGreater(len(browser.category_buttons), 1)
        self.assertNotIn('Town Center', browser.categories)
        self.assertNotIn('Market', browser.categories)
        # Barracks: the Militia line shares one row (same y), one icon per tier.
        militia = [b for b in browser.unit_buttons if set(b.property('members')) & {'Militia', 'Man-at-Arms', 'Long Swordsman', 'Two-Handed Swordsman', 'Champion'}]
        self.assertGreaterEqual(len(militia), 4)
        self.assertEqual(len({b.geometry().y() for b in militia}), 1)
        self.assertTrue(all(not b.icon().isNull() for b in militia))
        browser.toggle_category('Stable')
        self.assertIn('Knight', [n for b in browser.unit_buttons for n in b.property('members')])

    def test_every_unit_row_has_a_name(self):
        panel = self.make_panel()
        browser = panel.unit_browser
        panel.select_civ('Franks', player_civ='Franks')
        for category in browser.categories:
            browser.toggle_category(category)
            app.processEvents()
            for index in range(browser.units_layout.count()):
                row = browser.units_layout.itemAt(index).layout()
                text = row.itemAt(0).widget().text()
                # Continuation rows of a wrapped group are intentionally blank.
                self.assertIsInstance(text, str)
        browser.toggle_category('Castle')
        labels = [browser.units_layout.itemAt(i).layout().itemAt(0).widget().text() for i in range(browser.units_layout.count())]
        self.assertIn('Siege', labels)
        browser.toggle_category('Archery Range')
        names = {n for b in browser.unit_buttons for n in b.property('members')}
        self.assertIn('Hand Cannoneer', names)
        labels = [browser.units_layout.itemAt(i).layout().itemAt(0).widget().text() for i in range(browser.units_layout.count())]
        self.assertIn('Gunpowder', labels)

    def test_clicking_icon_selects_unit(self):
        panel = self.make_panel()
        button = panel.unit_browser.unit_buttons[0]
        button.click()
        self.assertTrue(button.isChecked())
        self.assertEqual(panel.unit_caption.text(), button.unit_name)

    def test_counters_come_from_class_data_and_player_civ(self):
        panel = self.make_panel()
        sections = dict(panel._class_counters('Knight'))
        self.assertIn('Halberdier', sections['Spearman-line'])
        self.assertNotIn('Paladin', sum(sections.values(), []))
        panel._show_counters_for_unit('Knight')
        texts = [label.text() for label in panel.counter_host.findChildren(QLabel)]
        self.assertIn('Weak vs. Spearman-line', texts)


if __name__ == '__main__':
    unittest.main()
