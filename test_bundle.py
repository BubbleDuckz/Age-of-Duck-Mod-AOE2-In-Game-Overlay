import shutil
import tempfile
import unittest
from pathlib import Path

from scripts.check_bundle import check_bundle


class BundleTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.project = Path(temp.name) / 'source'
        self.bundle = Path(temp.name) / 'bundle'
        self.project.mkdir()
        self.bundle.mkdir()
        (self.bundle / 'AgeOfDuck.exe').write_bytes(b'test executable')
        (self.project / 'AgeOfDuck.spec').write_text(
            "a = Analysis([], datas=[('catalog.json', '.'), ('portraits', 'portraits'), ('audio/*.wav', 'audio')])")
        (self.project / 'catalog.json').write_text('{}')
        (self.project / 'portraits/nested').mkdir(parents=True)
        (self.project / 'portraits/nested/unit.png').write_bytes(b'portrait')
        (self.project / 'audio').mkdir()
        (self.project / 'audio/cue.wav').write_bytes(b'voice')
        for path in ['catalog.json', 'portraits', 'audio']:
            source = self.project / path
            if source.is_dir():
                shutil.copytree(source, self.bundle / path)
            else:
                shutil.copy2(source, self.bundle / path)

    def test_root_and_internal_layouts(self):
        self.assertEqual(check_bundle(self.project, self.bundle), [])
        assets = self.bundle / '_internal'
        assets.mkdir()
        for path in ['catalog.json', 'portraits', 'audio']:
            shutil.move(str(self.bundle / path), assets / path)
        self.assertEqual(check_bundle(self.project, self.bundle), [])

    def test_missing_portrait_is_reported(self):
        (self.bundle / 'portraits/nested/unit.png').unlink()
        self.assertTrue(any('unit.png' in e for e in check_bundle(self.project, self.bundle)))

    def test_stale_data_is_reported(self):
        (self.bundle / 'catalog.json').write_text('{"stale": true}')
        self.assertTrue(any('differs from source' in e for e in check_bundle(self.project, self.bundle)))

    def test_missing_source_and_executable_are_reported(self):
        (self.project / 'audio/cue.wav').unlink()
        (self.bundle / 'AgeOfDuck.exe').unlink()
        errors = check_bundle(self.project, self.bundle)
        self.assertIn('Missing AgeOfDuck.exe', errors)
        self.assertTrue(any('matches no resources' in e for e in errors))


if __name__ == '__main__':
    unittest.main()
