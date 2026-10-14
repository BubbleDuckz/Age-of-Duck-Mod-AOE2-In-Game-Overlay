import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from PyQt5.QtWidgets import QApplication,QLabel
from tooltip import CivMatchupPanel
from AgeofDuck import Overlay
app=QApplication.instance() or QApplication([])
ROOT=Path(__file__).parent
class CatalogTests(unittest.TestCase):
 def test_all_source_civs_and_units(self):
  source=json.loads((ROOT/'techtree_source/data.json').read_text(encoding='utf-8'));catalog=json.loads((ROOT/'techtree_data.json').read_text(encoding='utf-8'))
  self.assertEqual(set(source['civs']),set(catalog['civs']))
  for name,civ in catalog['civs'].items():
   tree=json.loads((ROOT/'techtree_source/trees'/f'{name}.json').read_text(encoding='utf-8'))
   expected={(n['node_id'],n['building_id']) for n in tree['units_techs'] if n['use_type']=='Unit' and n['node_id'] in source['civs'][name]['Unit'] and n['node_status']!='NotAvailable'}
   self.assertEqual(len(expected),sum(len(v) for v in civ['unitDetails'].values()))
   for group in civ['unitsAvailable'].values():
    for unit in group:self.assertTrue(catalog['units'][unit]['unitDescription']);self.assertNotIn('\n',unit)
  self.assertNotIn('Paladin',catalog['civs']['Britons']['unitsAvailable']['Stable'])
  self.assertIn('Champion',catalog['civs']['Britons']['unitsAvailable']['Barracks'])
 def test_source_description_display(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=CivMatchupPanel(assets_root=str(ROOT),strategies_path=str(Path(tmp)/'strategies.json'))
   p.select_civ('Britons',player_civ='Franks');p._show_counters_for_unit('Crossbowman')
   texts=[q.text() for q in p.counter_host.findChildren(QLabel)]
   self.assertIn('All-purpose Foot Archer. Strong vs. units at long range. Weak vs. Skirmishers, Mangonel-line and units at close range.',texts)
   p.close()
 def test_row_space_and_right_alignment(self):
  with patch('AgeofDuck.threading.Thread.start'),patch('AgeofDuck.Overlay.restore_last_position'):
   w=Overlay(None);w.scale_factor=.82;w.apply_scale()
   players=[dict(name='deswermobil',civ='Burmese',rating=2220,peak=2261,peak_mode='1v1',team=1),dict(name='Hera',civ='Sicilians',rating=2924,peak=3108,peak_mode='1v1',team=2)]
   w.update_overlay({},players,'RM 1v1','Fortress');w.show();app.processEvents()
   for row in w.player_rows[:2]:
    self.assertGreaterEqual(row.name_label.width(),row.name_label.fontMetrics().horizontalAdvance(row.name_label.text()))
    self.assertLessEqual(row.width()-(row.peak_label.x()+row.peak_label.width()),9)
   w.grab().save(str(ROOT/'techtree-layout-preview.png'))
   w.matchup_panel.select_civ('Britons',player_civ='Franks');w.matchup_panel._show_counters_for_unit('Crossbowman');app.processEvents();w.grab().save(str(ROOT/'techtree-description-preview.png'))
   w.worker.stop();w.hide();w.placement_timer.stop();w.waiting_timer.stop()
if __name__=='__main__':unittest.main()
