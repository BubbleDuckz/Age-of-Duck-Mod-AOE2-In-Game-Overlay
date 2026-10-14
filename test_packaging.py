"""Verify the Windows build entrypoint and runtime resource coverage without Qt."""
import ast
import fnmatch
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).parent


def bundled_resources():
    tree = ast.parse((ROOT / 'AgeOfDuck.spec').read_text(encoding='utf-8'))
    analysis = next(node.value for node in tree.body
                    if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call)
                    and isinstance(node.value.func, ast.Name) and node.value.func.id == 'Analysis')
    return ast.literal_eval(next(keyword.value for keyword in analysis.keywords if keyword.arg == 'datas'))


class PackagingTests(unittest.TestCase):
    def test_build_uses_checked_in_spec_without_deleting_it(self):
        script = (ROOT / 'make EXE.bat').read_text(encoding='utf-8').lower()
        self.assertIn('"ageofduck.spec"', script)
        self.assertNotIn('del /q ageofduck.spec', script)
        self.assertNotIn('--add-data', script)
        self.assertIn('if errorlevel 1', script)

    def test_counter_and_build_order_resources_are_bundled(self):
        sources = {source for source, destination in bundled_resources()}
        for resource in ('techtree_data.json', 'unit_counters_v2.json', 'UnitIcons',
                         'BuildOrders', 'build_order_voice.ps1', 'villager-glyphs.json'):
            with self.subTest(resource=resource):
                self.assertIn(resource, sources)

    def test_clock_and_detector_calibration_dependencies_are_bundled(self):
        resources = bundled_resources()

        def included(path):
            return any((path == source or path.startswith(source.rstrip('/') + '/')
                        or fnmatch.fnmatchcase(path, source))
                       and str(Path(destination) / Path(path).name) == path
                       for source, destination in resources)

        clock = json.loads((ROOT / 'tc_reminder/clock-calibration.json').read_text())
        detector = json.loads((ROOT / 'tc_reminder/calibration.json').read_text())
        paths = ['tc_reminder/samples/' + sample['file'] for sample in clock['samples']]
        paths += ['tc_reminder/' + template['file'] for template in detector['templates']]
        for path in paths:
            with self.subTest(path=path):
                self.assertTrue(included(path), 'Missing runtime calibration resource: ' + path)


if __name__ == '__main__':
    unittest.main()
