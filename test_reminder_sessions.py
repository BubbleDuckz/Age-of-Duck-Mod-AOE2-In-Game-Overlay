"""Session regressions, with Windows playback replaced only at the boundary."""
import sys
import types
import unittest
from unittest.mock import Mock, patch
from tc_reminder.core import Observation, Reminder

class ReminderSessionTests(unittest.TestCase):
    def test_manual_total_survives_new_session_and_partial_selection(self):
        r=Reminder()
        obs=Observation(session='new',foreground=True,gameplay=True,advancing=True,confident=True,
                        selected_tcs=2,selection_verified=True,busy=2)
        r.step(obs,0,validated=True,manual_total=5)
        text,cue,reason=r.step(obs,4,validated=True,manual_total=5)
        self.assertEqual(r.total,5)
        self.assertEqual(text,'Check TC queues')
        self.assertTrue(cue)

    def test_automatic_counting_is_retained(self):
        r=Reminder()
        obs=Observation(foreground=True,paused=True,selected_tcs=3,selection_verified=True)
        r.step(obs,0)
        self.assertEqual(r.total,3)

    def test_new_voice_session_can_repeat_the_same_instruction(self):
        # winsound is unavailable on Linux. Keep the real voice class and replace playback.
        sound=types.SimpleNamespace(PlaySound=Mock(),SND_FILENAME=1,SND_ASYNC=2,SND_NODEFAULT=4)
        with patch.dict(sys.modules,{'winsound':sound}):
            from tc_reminder.voice import RepeatingVoice
            calls=[]
            voice=RepeatingVoice('missing.wav',play=lambda *args:calls.append(args))
            voice.update(True,0,event=('opening','3'))
            voice.advance(2)
            voice.stop()
            voice.update(True,3,event=('opening','3'))
            self.assertEqual(len([a for a in calls if a[0]]),1)
            voice.reset()
            voice.update(True,4,event=('opening','3'))
            self.assertEqual(len([a for a in calls if a[0]]),2)

if __name__=='__main__':unittest.main()
