import threading
import unittest
from unittest.mock import Mock
from update_io import start_background

class BackgroundUpdateTests(unittest.TestCase):
    def test_blocked_network_work_does_not_block_caller(self):
        release=threading.Event();entered=threading.Event();success=Mock();failure=Mock();threads=[]
        def work():
            threads.append(threading.get_ident());entered.set()
            if not release.wait(2):raise TimeoutError('test did not release worker')
            return 'downloaded'
        thread=start_background(work,success,failure)
        self.addCleanup(release.set)
        self.assertTrue(entered.wait(1))
        self.assertNotEqual(threads[0],threading.get_ident())
        success.assert_not_called()
        release.set();thread.join(2)
        self.assertFalse(thread.is_alive())
        success.assert_called_once_with('downloaded');failure.assert_not_called()

    def test_errors_are_delivered_to_failure_callback(self):
        success=Mock();failure=Mock()
        thread=start_background(Mock(side_effect=ConnectionError('offline')),success,failure)
        thread.join(2)
        success.assert_not_called();failure.assert_called_once_with('offline')

    def test_shutdown_drops_late_results(self):
        success=Mock();failure=Mock()
        thread=start_background(lambda:'done',success,failure,lambda:True)
        thread.join(2)
        success.assert_not_called();failure.assert_not_called()

if __name__=='__main__':unittest.main()
