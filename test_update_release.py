import unittest

from update_release import select_update


class UpdateReleaseTests(unittest.TestCase):
    def release(self, name, url='https://example.invalid/setup.exe', **extra):
        return dict(tag_name='v2.1.0', assets=[dict(name=name, browser_download_url=url)], **extra)

    def test_versioned_setup_generated_by_both_installers(self):
        self.assertEqual(select_update(self.release('AgeOfDuck-Setup-v2.1.0.exe'), '2.0.0'),
                         ('2.1.0', 'https://example.invalid/setup.exe'))

    def test_legacy_installer_names(self):
        for name in ('AgeOfDuckInstaller-v2.1.0.exe', 'AgeOfDuck-Setup.exe', 'AGEOFDUCK-SETUP-V2.1.0.EXE'):
            with self.subTest(name=name):
                self.assertEqual(select_update(self.release(name), '2.0.0')[0], '2.1.0')

    def test_equal_and_older_versions(self):
        for version in ('2.1.0', '2.2.0'):
            with self.subTest(version=version):
                self.assertEqual(select_update(self.release('AgeOfDuck-Setup-v2.1.0.exe'), version), (None, None))

    def test_versions_are_compared_numerically(self):
        release = self.release('AgeOfDuck-Setup-v2.10.0.exe')
        release['tag_name'] = 'v2.10.0'
        self.assertEqual(select_update(release, '2.9.0')[0], '2.10.0')

    def test_non_executable_assets_and_missing_urls_are_skipped(self):
        release = self.release('AgeOfDuckInstaller.zip')
        release['assets'] += [dict(name='AgeOfDuckInstaller.exe'),
                              dict(name='AgeOfDuck-Setup-v2.1.0.exe', browser_download_url='https://example.invalid/setup.exe')]
        self.assertEqual(select_update(release, '2.0.0')[0], '2.1.0')

    def test_no_installer(self):
        for name in ('SHA256SUMS.txt', 'BuildAgeOfDuckInstaller.spec', 'unrelated.exe'):
            with self.subTest(name=name):
                self.assertEqual(select_update(self.release(name), '2.0.0'), (None, None))

    def test_unpublished_and_prerelease_versions(self):
        for flag in ('draft', 'prerelease'):
            with self.subTest(flag=flag):
                self.assertEqual(select_update(self.release('AgeOfDuckInstaller.exe', **{flag: True}), '2.0.0'), (None, None))

    def test_missing_release_fields(self):
        for release in ({}, {'tag_name': 'v2.1.0'}, {'tag_name': 'v2.1.0', 'assets': [{}]}):
            with self.subTest(release=release):
                self.assertEqual(select_update(release, '2.0.0'), (None, None))


if __name__ == '__main__':
    unittest.main()
