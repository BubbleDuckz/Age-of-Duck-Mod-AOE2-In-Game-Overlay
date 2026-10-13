import tempfile,unittest,json
from pathlib import Path
from unittest.mock import patch
from PyQt5.QtCore import QObject,pyqtSignal,Qt,QPoint
from PyQt5.QtGui import QMouseEvent
from PyQt5.QtWidgets import QApplication,QMenu
from tc_reminder.integration import TCController,TCPanel
app=QApplication.instance() or QApplication([])
class MainStub(QObject):
 scale_changed=pyqtSignal(float)
 scale_factor=1.
 def increase_scale(self):self.scale_factor*=1.1;self.scale_changed.emit(self.scale_factor)
 def decrease_scale(self):self.scale_factor/=1.1;self.scale_changed.emit(self.scale_factor)
class PanelTests(unittest.TestCase):
 def test_shared_scale_mute_and_persisted_position(self):
  menu=QMenu();main=MainStub()
  with tempfile.TemporaryDirectory() as tmp:
   path=Path(tmp)/'settings.json'
   with patch('tc_reminder.native.single_instance',return_value=True):c=TCController(app,menu,path,main)
   c.timer.stop();c.panel.plus.click();self.assertEqual(c.panel.width(),260);self.assertEqual(c.panel_scale,1.1)
   # Panel size is independent of the main overlay.
   self.assertEqual(main.scale_factor,1.);main.increase_scale();self.assertEqual(c.panel.width(),260)
   c.panel.minus.click();self.assertEqual(c.panel.width(),236);self.assertEqual(json.loads(path.read_text())['panel_scale'],1.0)
   c.panel.mute_button.click();self.assertTrue(c.mute.isChecked())
   c.save_position((150,120));c.changed();self.assertEqual(json.loads(path.read_text())['position'],[150,120])
   c.close()
 def test_build_house_is_amber_and_combined_warnings_are_red(self):
  p=TCPanel();g=(0,'test',(0,0,2560,1440))
  p.present(g,3,0,'Build House',False,True);p.phase=True;p.flash();amber=p.alert.styleSheet()
  p.present(g,3,1,'Build House · Idle TC',False,True);p.phase=True;p.flash()
  self.assertIn('Build House',p.alert.text());self.assertIn('Idle TC',p.alert.text());self.assertNotEqual(p.alert.styleSheet(),amber)
  p.close()
 def test_alert_counts_small_scale_and_drag(self):
  p=TCPanel();p.set_scale(.75);p.present((0,'test',(0,0,2560,1440)),1,0,'Housed',True,True)
  app.processEvents();self.assertEqual(p.values[0].text(),'1');self.assertEqual(p.values[1].text(),'0');self.assertTrue(p.mute_button.muted)
  self.assertTrue(p.flashing);before=p.alert.styleSheet();p.flash();self.assertNotEqual(p.alert.styleSheet(),before)
  p.grab().save('tc-panel-small-preview.png')
  origin=p.pos();press=QMouseEvent(QMouseEvent.MouseButtonPress,QPoint(10,10),origin+QPoint(10,10),Qt.LeftButton,Qt.LeftButton,Qt.NoModifier)
  p.drag_press(press)
  move=QMouseEvent(QMouseEvent.MouseMove,QPoint(10,10),origin+QPoint(60,40),Qt.NoButton,Qt.LeftButton,Qt.NoModifier)
  p.drag_move(move);p.drag_release(move);self.assertIsNotNone(p.offset)
  p.close()
