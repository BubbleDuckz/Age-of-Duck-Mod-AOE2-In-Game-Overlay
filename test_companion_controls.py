import tempfile,unittest,wave,json,time
from pathlib import Path
from unittest.mock import Mock,patch
import numpy as np
from PyQt5.QtWidgets import QApplication,QMenu
from AgeofDuck import Overlay
from build_orders import BuildOrders
from companion_controls import CompanionControls
from tc_reminder.integration import TCController
from tc_reminder.voice import RepeatingVoice,volume_file
app=QApplication.instance() or QApplication([])
ROOT=Path(__file__).parent
class ControlsTests(unittest.TestCase):
 def tearDown(self):RepeatingVoice.volume_percent=100
 def test_volume_preserves_duration_and_scales_amplitude(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp)/'voice.wav';samples=np.array([-30000,-10000,0,10000,30000],dtype='<i2')
   with wave.open(str(p),'wb') as f:f.setparams((1,2,8000,0,'NONE','not compressed'));f.writeframes(samples.tobytes())
   for percent in [0,50,100]:
    with wave.open(volume_file(p,percent),'rb') as f:
     self.assertEqual(f.getnframes(),5);self.assertEqual(f.getframerate(),8000)
     np.testing.assert_array_equal(np.frombuffer(f.readframes(5),dtype='<i2'),samples.astype(float)*percent/100)
 def test_in_game_controls_persist_visibility_and_volume(self):
  with tempfile.TemporaryDirectory() as tmp,patch('AgeofDuck.threading.Thread.start'),patch('tc_reminder.native.companion_focused',return_value=False),patch('AgeofDuck.load_saved_scale',return_value=.9),patch('companion_controls.native.foreground_game',return_value=(1,'test',(0,0,2560,1440))):
   main=Overlay(Mock());menu=QMenu()
   with patch('tc_reminder.native.single_instance',return_value=True):tc=TCController(app,menu,Path(tmp)/'tc.json');tc.timer.stop()
   build=BuildOrders(app,main,tc,tmp,ROOT);build.timer.stop();build.set_enabled(True)
   c=CompanionControls(main,build,tc);main.outer.insertWidget(main.outer.indexOf(main.footer),c)
   self.assertFalse(c.guide.isEnabled());self.assertFalse(c.idle.isEnabled())
   c.guide.click();c.idle.click();self.assertTrue(build.view_visible);self.assertTrue(tc.view_visible)
   build.in_match=True;build.session='test';build.last_frame=time.monotonic()
   tc.match_session='test';tc.last_good=time.monotonic();tc.latest_state={'context':'gameplay'};c.refresh()
   self.assertTrue(c.guide.isEnabled());self.assertTrue(c.idle.isEnabled())
   # Simulate losing game focus between an enabled button press and release.
   with patch('companion_controls.native.foreground_game',return_value=None):c.guide.click()
   self.assertFalse(build.view_visible);self.assertTrue(tc.view_visible)
   self.assertFalse(json.loads(build.pref_file.read_text())['view_visible']);c.refresh()
   self.assertTrue(c.guide.isEnabled());self.assertFalse(build.view_visible);self.assertTrue(build.enabled);self.assertFalse(build.muted)
   # A click must show the panel and update its label before any timer/capture.
   with patch('companion_controls.native.foreground_game',return_value=None):
    c.guide.click();self.assertTrue(build.view_visible);self.assertTrue(build.panel.isVisible())
    self.assertEqual(c.guide.text(),'Build Order');self.assertTrue(c.guide.light_on)
   c.idle.click();self.assertFalse(tc.view_visible);self.assertFalse(c.idle.light_on);self.assertTrue(tc.enabled.isChecked());self.assertFalse(tc.mute.isChecked())
   with patch('companion_controls.native.foreground_game',return_value=None):
    c.idle.click();self.assertTrue(tc.view_visible);self.assertTrue(tc.panel.isVisible())
    self.assertEqual(c.idle.text(),'Idle / Housed');self.assertTrue(c.idle.light_on)
   # The whole controls section folds away behind its header chevron and the choice persists.
   self.assertTrue(c.expanded);self.assertFalse(c.body.isHidden())
   c.chevron.click()
   for _ in range(40):app.processEvents();time.sleep(0.01)
   self.assertFalse(c.expanded);self.assertTrue(c.body.isHidden());self.assertFalse(json.loads(tc.settings_path.read_text())['controls_expanded'])
   c.chevron.click()
   for _ in range(40):app.processEvents();time.sleep(0.01)
   self.assertTrue(c.expanded);self.assertFalse(c.body.isHidden())
   self.assertIsNone(c.volume_row.parent());c.slider.setValue(90);self.assertEqual(RepeatingVoice.volume_percent,90);self.assertEqual(c.level.text(),'90%')
   for _ in range(40):app.processEvents();time.sleep(0.01)
   self.assertEqual(json.loads(tc.settings_path.read_text())['voice_volume'],90)
   c.speaker.click();self.assertTrue(tc.mute.isChecked());self.assertTrue(c.speaker.muted);c.speaker.click();self.assertFalse(tc.mute.isChecked())
   self.assertTrue(json.loads(build.pref_file.read_text())['view_visible'])
   main.mode_label.setText('RM 1v1');main.map_label.setText('Arabia');main.show();main.adjustSize();app.processEvents()
   main.grab().save(str(ROOT/'companion-controls-preview.png'))
   for button in c.findChildren(__import__('PyQt5.QtWidgets',fromlist=['QPushButton']).QPushButton):self.assertGreaterEqual(button.width(),button.minimumSizeHint().width())
   with patch('companion_controls.native.foreground_game',return_value=None):
    c.refresh();self.assertFalse(c.guide.isEnabled());self.assertFalse(c.idle.isEnabled())
    self.assertTrue(c.select.isEnabled());self.assertTrue(c.slider.isEnabled())
    main.grab().save(str(ROOT/'companion-controls-disabled-preview.png'))
   c.refresh();self.assertTrue(c.guide.isEnabled());self.assertTrue(c.idle.isEnabled())
   build.set_view_visible(False);tc.set_view_visible(True)
   with patch('tc_reminder.native.companion_focused',return_value=True):
    build.last_frame-=10;tc.last_good-=10;c.refresh()
    self.assertTrue(c.guide.isEnabled());self.assertTrue(c.idle.isEnabled());self.assertFalse(build.view_visible);self.assertTrue(tc.view_visible)
    c.guide.click();self.assertTrue(build.view_visible);self.assertTrue(tc.view_visible)
    build.tick();tc._tick();self.assertTrue(build.panel.isVisible());self.assertTrue(tc.panel.isVisible())
    c.guide.click();build.tick();tc._tick();self.assertFalse(build.panel.isVisible());self.assertTrue(tc.panel.isVisible())
    # Returning to the game must retain the independent TC view even before
    # a new capture completes. Reassert native visibility on every UI tick.
    with patch('tc_reminder.native.companion_focused',return_value=False),patch.object(tc.executor,'submit',return_value=None):
     tc.panel.hide();tc._tick();build.tick()
     self.assertTrue(tc.panel.isVisible());self.assertFalse(build.panel.isVisible())
    c.idle.click();tc._tick();self.assertFalse(tc.panel.isVisible());self.assertFalse(build.view_visible)
    tc.panel.set_scale(1.1);self.assertFalse(tc.panel.isVisible())
   # Returning after companion focus keeps shown panels while captures warm up.
   build.set_view_visible(True);tc.set_view_visible(True)
   build.last_frame-=2;tc.last_good-=2
   with patch.object(tc.executor,'submit',return_value=None):
    build.tick();tc._tick()
   self.assertTrue(build.panel.isVisible());self.assertTrue(tc.panel.isVisible())
   build.observe((1,'test',(0,0,2560,1440)),{'gameplay':True,'advancing':False,'context':'gameplay'},time.monotonic())
   build.tick();self.assertTrue(build.panel.isVisible());self.assertFalse(build.safe)
   build.last_frame-=2;c.refresh();self.assertTrue(c.guide.isEnabled());self.assertTrue(c.idle.isEnabled())
   build.select_dialog();app.processEvents();self.assertIsNone(app.activeModalWidget())
   called=[];main.settings_requested.connect(lambda:called.append(True));main.settings_button.click();self.assertTrue(called)
   import ctypes
   from ctypes import wintypes
   msg=wintypes.MSG();msg.message=0x21;self.assertEqual(main.nativeEvent(None,ctypes.addressof(msg)),(True,3))
   build.close();tc.close();main.close()
if __name__=='__main__':unittest.main()

