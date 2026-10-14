import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock,patch
from update_io import startup_command,fetch_update,download_installer,launch_installer,consume_completed_update

class UpdateIOTests(unittest.TestCase):
    def test_frozen_startup_uses_real_executable(self):
        command=startup_command(True,r'C:\Program Files\AgeOfDuck\AgeOfDuck.exe',r'C:\Program Files\AgeOfDuck\_internal\AgeofDuck.py')
        self.assertEqual(command,'"C:\\Program Files\\AgeOfDuck\\AgeOfDuck.exe"')

    def test_source_startup_includes_interpreter_and_script(self):
        command=startup_command(False,r'C:\Python311\python.exe',r'C:\My Project\AgeofDuck.py')
        self.assertIn('python.exe',command)
        self.assertIn('"C:\\My Project\\AgeofDuck.py"',command)

    def test_connection_failure_is_not_no_update(self):
        with self.assertRaises(ConnectionError):
            fetch_update('unused','2.0.1',get=Mock(side_effect=ConnectionError('offline')))

    def test_new_release_without_installer_is_an_error(self):
        response=Mock();response.json.return_value={'tag_name':'v2.1.0','assets':[]}
        with self.assertRaises(ValueError):fetch_update('unused','2.0.1',get=Mock(return_value=response))

    def test_latest_version_is_successful_no_update(self):
        response=Mock();response.json.return_value={'tag_name':'v2.0.1','assets':[]}
        self.assertEqual(fetch_update('unused','2.0.1',get=Mock(return_value=response)),(None,None))

    def test_cancelled_launch_does_not_create_success_marker(self):
        with tempfile.TemporaryDirectory() as tmp:
            marker=Path(tmp)/'update.json'
            for code in [0,5,31,32]:
                with self.assertRaises(OSError):launch_installer('setup.exe','2.1.0',marker,Mock(return_value=code))
                self.assertFalse(marker.exists())

    def test_marker_only_reports_success_after_the_version_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            marker=Path(tmp)/'update.json'
            launch_installer('setup.exe','2.1.0',marker,Mock(return_value=33))
            self.assertFalse(consume_completed_update(marker,'2.0.1'))
            self.assertTrue(marker.exists())
            self.assertTrue(consume_completed_update(marker,'2.1.0'))
            self.assertFalse(marker.exists())

    def test_invalid_legacy_markers_are_not_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            marker=Path(tmp)/'update.json'
            for value in ['', '[]', '{"version":"bad"}']:
                marker.write_text(value)
                self.assertFalse(consume_completed_update(marker,'2.0.1'))

    def test_failed_download_removes_partial_file(self):
        with patch('update_io.tempfile.mkstemp') as create:
            import os
            with tempfile.TemporaryDirectory() as tmp:
                path=Path(tmp)/'partial.exe'
                descriptor=os.open(path,os.O_CREAT|os.O_WRONLY)
                create.return_value=(descriptor,str(path))
                with self.assertRaises(ConnectionError):
                    download_installer('unused',get=Mock(side_effect=ConnectionError('offline')))
                self.assertFalse(path.exists())

if __name__=='__main__':unittest.main()
