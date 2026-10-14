import sys
import tempfile
from pathlib import Path
from concurrent.futures import Future
import unittest
from unittest.mock import Mock,patch

@unittest.skipUnless(sys.platform=='win32','Controller integration needs Windows and Qt')
class TCLifecycleTests(unittest.TestCase):
    def setUp(self):
        from PyQt5.QtWidgets import QApplication,QMenu
        from tc_reminder.integration import TCController
        self.app=QApplication.instance() or QApplication([])
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
        self.menu=QMenu()
        with patch('tc_reminder.native.single_instance',return_value=True):
            self.c=TCController(self.app,self.menu,Path(tmp.name)/'prefs.json')
        self.c.timer.stop();self.addCleanup(self.c.close)
        self.c.voice=Mock();self.c.sync_view=Mock();self.c.panel.present=Mock()
        self.c.match_session='session';self.c.reminder.session='session';self.c.reminder.total=1
        self.c.detector.alerts_validated=True

    def tick(self,**changes):
        game=(1,'session',(0,0,2560,1440));now=12
        result=dict(context='gameplay',gameplay=True,advancing=True,confident=True,
                    selected_tcs=None,busy_upper_bound=1,housed=0,population=(20,25),
                    reason='recognized',clock_seconds=600)
        result.update(changes)
        self.c.last_frame=now;self.c.last_good=now;self.c.last_diagnostic=now
        self.c.future=Future();self.c.future.set_result((game,self.c.epoch,now,result))
        with patch('tc_reminder.native.foreground_game',return_value=game),\
             patch('tc_reminder.native.companion_focused',return_value=False),\
             patch('tc_reminder.integration.time.monotonic',return_value=now):self.c._tick()

    def test_pause_clears_blocked_evidence_and_silences_voice(self):
        self.c.blocked_since=10;self.c.blocked_last=11
        self.tick(context='pause',gameplay=False,advancing=False,confident=False,population=(20,20))
        self.assertEqual(self.c.housing_state,'')
        self.assertIsNone(self.c.blocked_since)
        self.assertFalse(self.c.voice.update.call_args.args[0])

    def test_new_match_resets_housing_events_and_voice_session(self):
        self.c.blocked_since=10;self.c.blocked_last=11
        self.c.build_events.update((20,25),'Build House',True)
        self.c.continuity.last_time=600;self.c.continuity.pending=1
        self.tick(clock_seconds=2,population=(3,5))
        self.assertTrue(self.c.latest_state['new_match'])
        self.assertEqual(self.c.housing_state,'')
        self.assertIsNone(self.c.blocked_since)
        self.assertEqual(self.c.build_events.serial,0)
        self.c.voice.reset.assert_called_once()

    def test_manual_total_is_used_when_partial_group_is_selected(self):
        self.c.manual_tcs=5;self.c.reminder.shortfall_since=0
        self.c.selection.observe(2,11.5,True)
        self.tick(selected_tcs=2,busy_upper_bound=2)
        self.assertEqual(self.c.reminder.total,5)
        self.assertTrue(self.c.idle_alert)

if __name__=='__main__':unittest.main()
