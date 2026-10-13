import unittest
from unittest.mock import patch
from PyQt5.QtWidgets import QApplication
from AgeofDuck import SettingsWindow
app=QApplication.instance() or QApplication([])
class SettingsTests(unittest.TestCase):
 def test_restore_and_save(self):
  with patch('AgeofDuck.load_last_profile_id',return_value='14982384'),patch('AgeofDuck.save_last_profile_id') as save:
   w=SettingsWindow();values=[];w.profile_set.connect(values.append)
   w.move(50000,50000);w.showMinimized();w.show_and_focus();app.processEvents()
   self.assertTrue(w.isVisible());self.assertFalse(w.isMinimized())
   self.assertTrue(any(s.availableGeometry().intersects(w.frameGeometry()) for s in app.screens()))
   self.assertEqual(w.edit.selectedText(),'14982384')
   self.assertEqual(w.find_button.text(),'Find profile ID');w.edit.setText('199325');w.set_profile();save.assert_called_once_with('199325');self.assertEqual(values,['199325']);self.assertFalse(w.isVisible());w.close()
if __name__=='__main__':unittest.main()
