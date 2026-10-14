import unittest

from check_game_data import validate_data


class GameDataTests(unittest.TestCase):
    def setUp(self):
        self.source = {'civs': {'Britons': {}}}
        self.catalog = {'metadata': {'data_sha256': 'snapshot'},
                        'civs': {'Britons': {'unitsAvailable': {'Barracks': {'Militia': True}}}},
                        'units': {'Militia': {'unitDescription': 'Infantry.'}}}
        self.counters = {'metadata': {'source_data_sha256': 'snapshot'},
                         'units': {'Militia': {'line': 'Militia', 'weak_vs': ['Archers'], 'strong_vs': []}},
                         'lines': {'Militia': ['Militia']}, 'classes': {'Archers': [['Militia']]}}
        self.portraits = {'Militia': '001.png'}
        self.files = {'CivIcons/Britons_AoE2.webp', 'UnitIcons/001.png'}

    def errors(self):
        return validate_data(self.source, self.catalog, self.counters, self.portraits, 'snapshot', self.files)

    def test_consistent_snapshot(self):
        self.assertEqual(self.errors(), [])

    def test_stale_generated_files(self):
        self.catalog['metadata']['data_sha256'] = 'older'
        self.counters['metadata']['source_data_sha256'] = 'older'
        self.assertEqual(len(self.errors()), 2)

    def test_missing_portraits_and_civilisation_emblems(self):
        self.files.clear()
        self.assertEqual(len(self.errors()), 2)

    def test_broken_counter_relationships(self):
        self.counters['units']['Militia']['weak_vs'] = ['Unknown']
        self.counters['lines']['Militia'] = ['Unknown Unit']
        self.counters['classes']['Archers'] = [['Unknown Unit']]
        self.assertEqual(len(self.errors()), 4)

    def test_missing_civilisation_and_unit_data(self):
        self.source['civs']['Franks'] = {}
        self.counters['units'].clear()
        self.catalog['civs']['Britons']['unitsAvailable']['Barracks']['Unknown Unit'] = True
        self.assertEqual(len(self.errors()), 3)

    def test_empty_descriptions(self):
        self.catalog['units']['Militia']['unitDescription'] = ' '
        self.assertEqual(len(self.errors()), 1)

    def test_strength_classes_use_membership_not_weakness_classes(self):
        self.counters['units']['Militia']['member_of'] = ['Mounted Units']
        self.counters['units']['Militia']['strong_vs'] = ['Mounted Units']
        self.assertEqual(self.errors(), [])
        self.counters['units']['Militia']['strong_vs'] = ['Unknown']
        self.assertEqual(len(self.errors()), 1)


if __name__ == '__main__':
    unittest.main()
