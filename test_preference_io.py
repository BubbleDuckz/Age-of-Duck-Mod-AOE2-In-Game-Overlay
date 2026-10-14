import json
from pathlib import Path
import tempfile
import unittest
from preference_io import read_object,valid_size,voice_volume

class PreferenceTests(unittest.TestCase):
    def test_non_objects_and_invalid_json_fall_back(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'prefs.json'
            self.assertEqual(read_object(p),{})
            for raw in ['[]','null','42','"text"','{']:
                p.write_text(raw)
                self.assertEqual(read_object(p),{})
            p.write_text(json.dumps({'mute':True}))
            self.assertEqual(read_object(p),{'mute':True})

    def test_dimensions_need_two_positive_integers(self):
        self.assertTrue(valid_size([2560,1440]))
        for value in [None,[],[2560],[2560,0],[0,1440],['2560',1440],[True,1440],[1.5,2],[1,2,3]]:
            with self.subTest(value=value):self.assertFalse(valid_size(value))

    def test_volume_recovers_and_clamps(self):
        for value in [None,{},'bad',float('inf')]:self.assertEqual(voice_volume(value),100)
        self.assertEqual(voice_volume('50'),50)
        self.assertEqual(voice_volume(200),100)
        self.assertEqual(voice_volume(-3),0)

if __name__=='__main__':unittest.main()
