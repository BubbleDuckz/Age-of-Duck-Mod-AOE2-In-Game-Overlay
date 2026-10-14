import json
from pathlib import Path
import unittest
from counter_rules import compatible_target

class CounterTargetTests(unittest.TestCase):
    def test_generic_units_are_not_unique_bonus_targets(self):
        data = json.loads((Path(__file__).parent / 'unit_counters_v2.json').read_text(encoding='utf-8'))
        for name in ['Monk', 'Hand Cannoneer', 'Bombard Cannon', 'Trebuchet', 'Siege Tower', 'Petard',
                     'Cannon Galleon', 'Elite Cannon Galleon']:
            with self.subTest(name=name):
                self.assertFalse(data['units'][name]['unique'])
                self.assertNotIn('Unique Units', data['units'][name]['member_of'])
        self.assertTrue(data['units']['Elite Samurai']['unique'])
        for name in ['Savar','Camel Scout']:
            self.assertNotIn('Unique Units',data['units'][name]['member_of'])

    def test_land_unique_bonus_does_not_offer_a_ship_counter(self):
        self.assertFalse(compatible_target({'member_of': ['Warships', 'Unique Units']},
                                           {'member_of': ['Infantry', 'Unique Units'],'attack_range':0}))
        self.assertTrue(compatible_target({'member_of': ['Warships']}, {'member_of': ['Warships'],'attack_range':0}))
        self.assertTrue(compatible_target({'member_of': ['Warships']}, {'member_of': ['Ranged Soldiers'],'attack_range':4}))
        self.assertTrue(compatible_target({'member_of': ['Infantry']}, {'member_of': ['Infantry']}))

if __name__ == '__main__':
    unittest.main()
