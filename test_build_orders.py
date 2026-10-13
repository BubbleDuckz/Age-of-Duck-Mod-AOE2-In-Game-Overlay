import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch,Mock
from PIL import Image
from PyQt5.QtCore import QObject,pyqtSignal
from PyQt5.QtWidgets import QApplication,QVBoxLayout,QWidget,QAction
from build_order_core import load_order,Progress
from villager_reader import VillagerReader
from build_orders import BuildOrders
app=QApplication.instance() or QApplication([])
ROOT=Path(__file__).parent.resolve()
class Main(QObject):
 scale_changed=pyqtSignal(float)
 scale_factor=.9
class TC(QObject):
 frame_observed=pyqtSignal(object,object,float)
 observer_enabled=False
 def __init__(self):
  super().__init__();self.voice=Mock();self.mute=QAction();self.mute.setCheckable(True)
class BuildOrderTests(unittest.TestCase):
 def order(self,rows):
  tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);p=Path(tmp.name)/'order.json';p.write_text(json.dumps(dict(version=1,name='Test',steps=rows)));return load_order(p)
 def test_decimal_sequence_and_new_villager(self):
  order=self.order([dict(step=s,unit='Custom',text=s) for s in ['19','19.2','19.1','19.10','20']]);e=Progress(order)
  e.observe(19,True);self.assertIsNone(e.begin());e.observe(19,True)
  for s in ['19','19.1','19.2','19.10']:self.assertEqual(e.begin().id,s);e.complete()
  self.assertIsNone(e.begin());e.observe(20,True);e.observe(20,True);self.assertEqual(e.begin().id,'20')
 def test_loss_pause_and_jump(self):
  e=Progress(self.order([dict(step=str(n),unit='Villager',task='Food') for n in range(3,8)]))
  e.observe(3,True);e.observe(3,True);self.assertEqual(e.begin().id,'3');e.complete()
  e.observe(4,False);e.observe(None,True);self.assertIsNone(e.begin())
  e.observe(5,True);e.observe(5,True)
  for s in ['4','5']:self.assertEqual(e.begin().id,s);e.complete()
  e.observe(4,True);e.observe(4,True);e.observe(5,True);e.observe(5,True);self.assertIsNone(e.begin())
  e.reset();e.observe(5,True);e.observe(5,True);self.assertEqual(e.begin().id,'5')
 def test_17_to_18_to_19_with_decimals(self):
  e=Progress(load_order(ROOT/'BuildOrders/Example-Archer-Opening.json'))
  for count,steps in [(17,['17']),(18,['18']),(19,['19','19.1','19.2'])]:
   e.observe(count,True);e.observe(count,True)
   for step in steps:self.assertEqual(e.begin().id,step);e.complete()
   self.assertIsNone(e.begin())
 def test_invalid_files(self):
  for rows in [[{'step':19.1,'unit':'Loom'}],[{'step':'19.1','unit':'Loom'}],[{'step':'1','unit':'Loom'},{'step':'1','unit':'Loom'}],[{'step':'251','unit':'Loom'}],[{'step':'1','unit':'Custom'}]]:
   with self.assertRaises(ValueError):self.order(rows)
 def test_sample_order(self):
  o=load_order(ROOT/'BuildOrders/Example-Archer-Opening.json');self.assertEqual(o.steps[-1].id,'23.1');self.assertNotIn('9',[s.id for s in o.steps])
 def test_actual_villager_counter(self):
  reader=VillagerReader()
  for f,n in [('new-match.png',3),('independent-four.png',36),('housed-three.png',15),('build-house-live-3.png',24),('pop-30-live-4.png',29),('provided.png',21),('build-order-villagers-live.png',10),('build-order-17-live.png',17),('build-order-stuck-live.png',19),('build-order-20-live.png',20)]:
   self.assertEqual(reader.read(Image.open(ROOT/'tc_reminder/samples'/f).convert('RGB')),n,f)
  self.assertIsNone(reader.read(Image.new('RGB',(2560,1440),'black')))
  self.assertIsNone(reader.read(Image.new('RGB',(1920,1080),'black')))
 def test_speech_priority_and_interruption(self):
  import wave
  with tempfile.TemporaryDirectory() as tmp:
   b=BuildOrders(app,Main(),TC(),tmp,ROOT);b.timer.stop();fake=Mock();fake.poll.return_value=0
   with patch('build_orders.subprocess.Popen',return_value=fake):b.load(b.folder/'Example-Archer-Opening.json')
   idx=next(i for i,s in enumerate(b.order.steps) if s.id=='19')
   with wave.open(str(b.cache/f'{idx}.wav'),'wb') as f:f.setparams((1,2,8000,0,'NONE','not compressed'));f.writeframes(b'\0\0'*8000)
   b.voice.play=Mock();b.set_enabled(True);game=(1,'session',(0,0,2560,1440));r=dict(gameplay=True,advancing=True,confident=True,villagers=19)
   with patch('build_orders.native.foreground_game',return_value=game),patch('build_orders.time.monotonic',return_value=10):
    b.observe(game,r,10);b.observe(game,r,10);b.tick();self.assertTrue(b.audio_busy);self.assertEqual(b.progress.current.id,'19');b.tc.voice.stop.assert_called()
   b.observe(game,dict(r,advancing=False),10.2);self.assertFalse(b.audio_busy);self.assertIsNone(b.deadline);self.assertEqual(b.progress.current.id,'19');self.assertFalse(b.spoken.isVisible())
   b.close()
 def test_decimal_hold_new_count_and_shared_audio_priority(self):
  import wave
  from PyQt5.QtWidgets import QMenu
  from tc_reminder.integration import TCController
  with tempfile.TemporaryDirectory() as tmp:
   menu=QMenu()
   with patch('tc_reminder.native.single_instance',return_value=True):tc=TCController(app,menu,Path(tmp)/'tc.json');tc.timer.stop()
   b=BuildOrders(app,Main(),tc,tmp,ROOT);b.timer.stop();fake=Mock();fake.poll.return_value=0
   with patch('build_orders.subprocess.Popen',return_value=fake):b.load(b.folder/'Example-Archer-Opening.json')
   for i,step in enumerate(b.order.steps):
    with wave.open(str(b.cache/f'{i}.wav'),'wb') as f:f.setparams((1,2,8000,0,'NONE','not compressed'));f.writeframes(b'\0\0'*8000)
   b.voice.play=Mock();tc.voice.play=Mock();b.set_enabled(True)
   game=(1,'session',(0,0,2560,1440))
   def frame(now,count):
    r=dict(gameplay=True,advancing=True,confident=count is not None,villagers=count)
    with patch('build_orders.native.foreground_game',return_value=game),patch('build_orders.time.monotonic',return_value=now):
     b.observe(game,r,now);tc.last_good=now;tc.last_frame=now;tc.idle_alert=True
     tc._tick();b.tick();tc._tick()
   frame(10,19);tc.voice.play.reset_mock();frame(10.5,19)
   self.assertEqual(b.progress.current.id,'19');self.assertTrue(b.audio_busy)
   # First decimal stays visible for ten seconds; unreadable count cannot stop it.
   frame(11.6,19);self.assertEqual(b.progress.current.id,'19.1');self.assertAlmostEqual(b.deadline,21.6)
   self.assertTrue(b.spoken.isVisible());self.assertEqual([w.text().split('  ')[0] for w in b.panel.previous],['17','18','19'])
   self.assertTrue(all(w.font().strikeOut() for w in b.panel.previous));self.assertTrue(b.panel.instruction.font().bold());self.assertTrue(all(not w.font().bold() for w in b.panel.upcoming))
   self.assertEqual([w.text().split('  ')[0] for w in b.panel.upcoming],['19.2','20','21'])
   from tc_reminder import native
   self.assertTrue(all(native.overlay_flags(b.spoken.hwnd).values()))
   before=native.u.GetForegroundWindow();b.spoken.present(game,b.progress.current.text);self.assertEqual(native.u.GetForegroundWindow(),before)
   b.spoken.grab().save(str(ROOT/'build-order-spoken-preview.png'))
   frame(12,None);self.assertTrue(b.audio_busy);self.assertAlmostEqual(b.deadline,21.6)
   frame(13,20);self.assertTrue(b.spoken.isVisible());frame(13.5,20);self.assertIn('20',[s.id for s in b.progress.pending])
   frame(16,20);self.assertFalse(b.spoken.isVisible())
   frame(21.5,20);self.assertEqual(b.progress.current.id,'19.1')
   frame(21.7,20);self.assertEqual(b.progress.current.id,'19.2');self.assertAlmostEqual(b.deadline,31.7)
   frame(31.6,20);self.assertEqual(b.progress.current.id,'19.2')
   frame(31.8,20);self.assertEqual(b.progress.current.id,'20')
   self.assertFalse(any(c.args[0] for c in tc.voice.play.call_args_list))
   self.assertEqual(len([c for c in b.voice.play.call_args_list if c.args[0]]),4)
   frame(33,20);self.assertIsNone(b.progress.current);self.assertTrue(b.spoken.isVisible())
   frame(36,20);self.assertFalse(b.spoken.isVisible())
   self.assertTrue(any(c.args[0] and str(c.args[0]).endswith('idle.wav') for c in tc.voice.play.call_args_list))
   tc.mute.setChecked(True);self.assertTrue(b.muted);self.assertFalse(b.spoken.isVisible());tc.mute.setChecked(False);self.assertFalse(b.muted)
   b.close();tc.close()
 def test_new_match_resets_guide_but_pause_and_villager_loss_do_not(self):
  with tempfile.TemporaryDirectory() as tmp:
   b=BuildOrders(app,Main(),TC(),tmp,ROOT);b.timer.stop();fake=Mock();fake.poll.return_value=0
   with patch('build_orders.subprocess.Popen',return_value=fake):b.load(b.folder/'Example-Archer-Opening.json')
   b.set_enabled(True);game=(1,'session',(0,0,2560,1440))
   r=dict(gameplay=True,advancing=True,villagers=19,match_id=('session',0))
   b.observe(game,r,1);b.observe(game,r,2);self.assertEqual(b.progress.begin().id,'19')
   selected=b.prefs['selected']
   b.observe(game,dict(r,advancing=False),3);b.observe(None,None,4)
   b.observe(game,dict(r,villagers=3),5);b.observe(game,dict(r,villagers=3),6)
   self.assertEqual(b.progress.current.id,'19');self.assertEqual(b.progress.high,19)
   # A candidate clock rewind pauses the old guide until confirmed.
   b.observe(game,dict(r,match_pending=True),7);self.assertFalse(b.safe)
   new=dict(r,match_id=('session',1),new_match=True,villagers=3)
   b.observe(game,new,8);self.assertIsNone(b.progress.current);self.assertIsNone(b.progress.last)
   self.assertEqual(b.prefs['selected'],selected)
   b.observe(game,dict(new,new_match=False),9);self.assertEqual(b.progress.begin().id,'3')
   self.assertEqual([s.id for s in b.progress.pending],[])
   # Re-enabling after the one-frame new_match event still sees the new identity.
   b.set_enabled(False);b.set_enabled(True)
   b.observe(game,dict(r,match_id=('session',2),villagers=3),10)
   b.observe(game,dict(r,match_id=('session',2),villagers=3),11)
   self.assertEqual(b.progress.begin().id,'3');self.assertIsNone(b.progress.last)
   b.close()
 def test_guide_hides_on_exit_menu_and_stopped_match(self):
  with tempfile.TemporaryDirectory() as tmp:
   b=BuildOrders(app,Main(),TC(),tmp,ROOT);b.timer.stop();b.set_enabled(True)
   game=(1,'session',(0,0,2560,1440))
   with patch('build_orders.native.foreground_game',return_value=game),patch('build_orders.time.monotonic',return_value=10):
    b.tick();self.assertFalse(b.panel.isVisible())
    live=dict(gameplay=True,advancing=True,context='gameplay',villagers=3)
    b.observe(game,live,10);b.tick();self.assertTrue(b.panel.isVisible())
    for result in [dict(gameplay=False,advancing=False,context='unknown'),dict(gameplay=False,advancing=False,context='menu'),dict(live,advancing=False)]:
     b.observe(game,result,10);b.tick();self.assertFalse(b.panel.isVisible());self.assertFalse(b.spoken.isVisible())
     b.observe(game,live,10);b.tick();self.assertTrue(b.panel.isVisible())
    b.observe(game,dict(live,gameplay=False,advancing=False,context='pause'),10);b.tick();self.assertTrue(b.panel.isVisible());self.assertFalse(b.audio_busy)
   with patch('build_orders.native.foreground_game',return_value=game),patch('build_orders.time.monotonic',return_value=12):
    b.tick();self.assertFalse(b.panel.isVisible())
   with patch('build_orders.native.foreground_game',return_value=None):b.tick();self.assertFalse(b.panel.isVisible())
   b.close()
 def test_optional_settings_and_visual_progress(self):
  with tempfile.TemporaryDirectory() as tmp:
   main=Main();tc=TC();b=BuildOrders(app,main,tc,tmp,ROOT);b.timer.stop()
   self.assertFalse(b.enabled);self.assertFalse(tc.observer_enabled)
   fake=Mock();fake.poll.return_value=0
   with patch('build_orders.subprocess.Popen',return_value=fake):b.load(b.folder/'Example-Archer-Opening.json')
   b.set_enabled(True);b.toggle_mute();self.assertTrue(tc.observer_enabled)
   game=(1,'session',(0,0,2560,1440));r=dict(gameplay=True,advancing=True,confident=True,villagers=19)
   with patch('build_orders.time.monotonic',return_value=10),patch('build_orders.native.foreground_game',return_value=game):
    b.observe(game,r,10);b.observe(game,r,10);b.tick();self.assertEqual(b.progress.current.id,'19');self.assertFalse(b.audio_busy)
    b.panel.grab().save(str(ROOT/'build-order-preview.png'))
   b.observe(game,dict(r,advancing=False),10.1);self.assertIsNone(b.deadline);self.assertEqual(b.progress.current.id,'19')
   settings=QWidget();settings.setWindowTitle('Build-order settings');layout=QVBoxLayout(settings);b.settings_controls(layout);settings.resize(410,160);settings.show();app.processEvents();settings.grab().save(str(ROOT/'build-order-settings-preview.png'));settings.hide()
   b.set_enabled(False);self.assertFalse(tc.observer_enabled);b.close()
if __name__=='__main__':unittest.main()
