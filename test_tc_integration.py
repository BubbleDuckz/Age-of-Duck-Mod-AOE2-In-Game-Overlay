import unittest,time
from unittest.mock import patch
from concurrent.futures import Future
from PyQt5.QtWidgets import QApplication,QMenu
from tc_reminder.integration import TCController,TCPanel
from tc_reminder.vision import Detector
from tc_reminder import native
from tc_reminder.paths import ROOT
from PIL import Image
app=QApplication.instance() or QApplication([])
class IntegratedTests(unittest.TestCase):
 def test_false_overflow_on_real_terrain(self):
  r=Detector().analyze(Image.open(ROOT/'samples/live-false-overflow.png'))
  self.assertTrue(r['confident']);self.assertFalse(r['queue_overflow']);self.assertEqual(r['housed'],1)
 def test_hud_gap_preserves_count_and_recovers_idle(self):
  menu=QMenu()
  with patch('tc_reminder.native.single_instance',return_value=True):c=TCController(app,menu,'tc-test-settings.json');c.timer.stop()
  game=(123,'test',(0,0,2560,1440));c.reminder.session='test';c.reminder.total=1
  base=time.monotonic()
  with patch('tc_reminder.native.foreground_game',return_value=game),patch.object(c.panel,'present'),patch.object(c.voice,'update'):
   for offset,visible in [(0,False),(3,False),(4,True),(7,True)]:
    now=base+offset;c.last_frame=now
    r=dict(context='gameplay' if visible else 'unknown',gameplay=visible,advancing=visible,confident=visible,selected_tcs=None,busy_upper_bound=0,housed=0,reason='HUD unavailable',population=(30,35) if visible else None)
    c.future=Future();c.future.set_result((game,c.epoch,now,r))
    # Normal 2Hz capture avoids stale-frame suppression between test observations.
    c.last_good=now
    with patch('tc_reminder.integration.time.monotonic',return_value=now):c._tick()
    self.assertEqual(c.reminder.total,1)
   self.assertTrue(c.idle_alert)
  c.close()
 def test_match_identity_survives_missing_clock_and_updates_after_restart(self):
  menu=QMenu()
  with patch('tc_reminder.native.single_instance',return_value=True):c=TCController(app,menu,'tc-test-settings.json');c.timer.stop()
  game=(123,'test',(0,0,2560,1440));frames=[];c.frame_observed.connect(lambda g,r,t:frames.append(r.copy()))
  base=time.monotonic()
  with patch('tc_reminder.native.foreground_game',return_value=game),patch.object(c.panel,'present'),patch.object(c.voice,'update'):
   for i,seconds in enumerate([600,601,None,601,602,2,3,4]):
    now=base+i*.5;c.last_frame=now;c.last_good=now
    r=dict(context='gameplay',gameplay=True,advancing=True,confident=True,selected_tcs=None,busy_upper_bound=0,housed=0,reason='OK',population=(4,5),clock_seconds=seconds)
    c.future=Future();c.future.set_result((game,c.epoch,now,r))
    with patch('tc_reminder.integration.time.monotonic',return_value=now):c._tick()
   self.assertEqual([r['new_match'] for r in frames],[False]*6+[True,False])
   self.assertTrue(frames[5]['match_pending']);self.assertEqual(frames[-1]['match_id'],('test',1))
  c.close()
 def test_quick_restart_and_clock_noise(self):
  from tc_reminder.runtime import MatchContinuity
  c=MatchContinuity()
  self.assertFalse(c.observe(8));self.assertFalse(c.observe(1));self.assertFalse(c.observe(9))
  self.assertIsNone(c.pending)
  self.assertFalse(c.observe(0));self.assertTrue(c.observe(1));self.assertFalse(c.observe(2))
 def test_profile_capture(self):
  d=Detector();self.assertTrue(d.alerts_validated)
  r=d.analyze(Image.open(ROOT/'samples/foundation-five.png'))
  self.assertEqual((r['selected_tcs'],r['busy_upper_bound'],r['population']),(5,4,(48,65)))
 def test_panel_focus(self):
  p=TCPanel();before=native.u.GetForegroundWindow()
  p.present((0,'test',(0,0,2560,1440)),4,2,'Build House',False,True)
  app.processEvents();self.assertEqual(before,native.u.GetForegroundWindow());self.assertTrue(all(native.overlay_flags(p.hwnd).values()))
  p.grab().save('tc-panel-preview.png');p.hide();p.close()
 def test_controller_housing_and_focus_loss(self):
  menu=QMenu()
  with patch('tc_reminder.native.single_instance',return_value=True):c=TCController(app,menu,'tc-test-settings.json');c.timer.stop()
  game=(123,'test',(0,0,2560,1440))
  r=dict(context='gameplay',gameplay=True,advancing=True,confident=False,selected_tcs=4,busy_upper_bound=2,housed=0,reason='OK',population=(95,100))
  with patch('tc_reminder.native.foreground_game',return_value=game),patch.object(c.panel,'present') as present,patch.object(c.voice,'update'):
   for i in range(2):
    now=time.monotonic()+i*.5;c.last_frame=now;c.future=Future();c.future.set_result((game,c.epoch,now,r.copy()))
    with patch('tc_reminder.integration.time.monotonic',return_value=now):c._tick()
   self.assertEqual(c.reminder.total,4);self.assertTrue(c.voice.path.endswith('build-house.wav'));self.assertIn('Build House',present.call_args[0][3])
  with patch('tc_reminder.native.foreground_game',return_value=None),patch.object(c.voice,'stop') as stop:
   c._tick();self.assertFalse(c.voice_active);self.assertFalse(c.panel.isVisible());stop.assert_called()
  c.close()
if __name__=='__main__':unittest.main()
