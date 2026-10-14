import unittest,os
from unittest.mock import patch
from tc_reminder import native
class FocusTests(unittest.TestCase):
 def tearDown(self):native._last_game_hwnd=None;native._last_game_context=None;native._null_companion_focus=False;native._last_game_seen=0
 def test_game_and_companion_windows_share_game_context(self):
  game=(10,'123',(0,0,2560,1440))
  with patch.object(native,'game_window',side_effect=lambda h,**kwargs:game if h==10 else None),patch.object(native.u,'GetForegroundWindow',return_value=10) as foreground,patch.object(native,'window_pid',return_value=os.getpid()) as pid:
   self.assertEqual(native.foreground_game(),game)
   for hwnd in [20,21,22]:
    foreground.return_value=hwnd;self.assertEqual(native.foreground_game(),game)
   pid.return_value=os.getpid()+1;self.assertIsNone(native.foreground_game())
   pid.return_value=os.getpid();self.assertEqual(native.foreground_game(),game)
 def test_closed_game_is_not_retained(self):
  native._last_game_hwnd=10
  with patch.object(native,'game_window',return_value=None),patch.object(native.u,'GetForegroundWindow',return_value=20),patch.object(native,'window_pid',return_value=os.getpid()):
   self.assertIsNone(native.foreground_game());self.assertIsNone(native._last_game_hwnd)
 def test_companion_focus_keeps_minimized_game_ui_context(self):
  game=(10,'123',(0,0,3008,1692))
  native._last_game_hwnd=10;native._last_game_context=game
  def lookup(hwnd,allow_minimized=False):
   return (10,'123',(0,0,160,28)) if hwnd==10 and allow_minimized else None
  with patch.object(native,'game_window',side_effect=lookup),patch.object(native.u,'GetForegroundWindow',return_value=20),patch.object(native,'window_pid',return_value=os.getpid()):
   self.assertEqual(native.foreground_game(),game)
   with patch.object(native.ImageGrab,'grab') as capture:
    self.assertIsNone(native.capture(game));capture.assert_not_called()
   with patch.object(native,'window_pid',return_value=os.getpid()+1):self.assertIsNone(native.foreground_game())
 def test_nonactivating_overlay_click_with_null_foreground(self):
  game=(10,'123',(0,0,2560,1440));native._last_game_hwnd=10;native._last_game_context=game
  with patch.object(native.u,'GetForegroundWindow',return_value=None) as fg,patch.object(native.u,'GetCursorPos',return_value=True),patch.object(native.u,'WindowFromPoint',return_value=20) as pointer,patch.object(native,'window_pid',return_value=os.getpid()) as pid,patch.object(native,'game_window',side_effect=lambda h,**kw:game if h==10 else None):
   self.assertEqual(native.foreground_game(),game);self.assertTrue(native.companion_focused())
   pointer.return_value=0
   self.assertEqual(native.foreground_game(),game)
   with patch.object(native.ImageGrab,'grab') as capture:
    self.assertIsNone(native.capture(game));capture.assert_not_called()
   fg.return_value=30;pid.return_value=os.getpid()+1
   self.assertIsNone(native.foreground_game());self.assertFalse(native.companion_focused())
 def test_brief_null_focus_on_game_return_preserves_only_ui(self):
  game=(10,'123',(0,0,2560,1440));native._last_game_hwnd=10;native._last_game_context=game;native._last_game_seen=100
  with patch.object(native.time,'monotonic',return_value=100.1) as clock,patch.object(native.u,'GetForegroundWindow',return_value=None),patch.object(native.u,'GetCursorPos',return_value=False),patch.object(native,'game_window',side_effect=lambda h,**kw:game if h==10 else None):
   self.assertEqual(native.foreground_game(),game)
   with patch.object(native.ImageGrab,'grab') as capture:
    self.assertIsNone(native.capture(game));capture.assert_not_called()
   clock.return_value=100.5;self.assertIsNone(native.foreground_game())
 def test_focus_change_during_capture_rejects_frame(self):
  game=(10,'123',(0,0,2560,1440))
  with patch.object(native,'foreground_game',side_effect=[game,None]),patch.object(native.ImageGrab,'grab',return_value=object()):self.assertIsNone(native.capture(game))
if __name__=='__main__':unittest.main()
