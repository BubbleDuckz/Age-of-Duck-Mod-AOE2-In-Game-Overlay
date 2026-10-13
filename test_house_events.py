import unittest
from tc_reminder.population import BuildHouseEvents
from tc_reminder.voice import RepeatingVoice
class HouseEventTests(unittest.TestCase):
 def test_population_events(self):
  e=BuildHouseEvents()
  for pop,state,confirmed,serial in [((95,100),'Build House',True,1),((95,100),'Build House',True,1),(None,'',False,1),((95,100),'Build House',True,1),((96,100),'Build House',True,2),((95,100),'Build House',True,2),((96,100),'Build House',True,3),((96,110),'',True,3),((105,110),'Build House',True,4),((200,200),'',True,4)]:
   e.update(pop,state,confirmed);self.assertEqual(e.serial,serial)
 def test_one_shot_survives_ticks_and_suppression(self):
  calls=[];v=RepeatingVoice('missing.wav',play=lambda *a:calls.append(a))
  v.update(True,0,event=('house',1));v.update(True,3,event=('house',1));self.assertEqual(len(calls),1)
  v.update(False,4);v.update(True,5,event=('house',1));self.assertEqual(len(calls),2)
  v.update(True,6,event=('house',2));self.assertEqual(len(calls),3)
 def test_other_voice_still_repeats(self):
  calls=[];v=RepeatingVoice('missing.wav',play=lambda *a:calls.append(a))
  v.update(True,0);v.update(True,.5);v.update(True,1.1);self.assertEqual(len(calls),2)

class FlashTests(unittest.TestCase):
 def test_flash_gap_and_safety(self):
  from tc_reminder.population import StableHousingReminder
  h=StableHousingReminder()
  self.assertEqual(h.update((20,20),True,0),'')
  self.assertEqual(h.update(None,True,.25),'')
  self.assertEqual(h.update((20,20),True,.5),'Housed')
  self.assertEqual(h.update(None,True,1),'Housed')
  self.assertEqual(h.update(None,True,2),'')
  h.update((20,20),True,3);h.update((20,20),True,3.5)
  self.assertEqual(h.update(None,False,3.6),'')
class DeliveryTests(unittest.TestCase):
 def test_interrupted_cue_retries_until_completed(self):
  calls=[];v=RepeatingVoice('missing.wav',play=lambda *a:calls.append(a))
  v.update(True,0,event=('house',1));v.update(False,.2)
  v.update(True,.5,event=('house',1))
  self.assertEqual(len([c for c in calls if c[0]]),2)
  v.update(True,1.6,event=('house',1));v.update(False,1.7);v.update(True,2,event=('house',1))
  self.assertEqual(len([c for c in calls if c[0]]),2)
 def test_requested_population_sequence(self):
  from tc_reminder.population import StableHousingReminder
  h=StableHousingReminder();e=BuildHouseEvents();calls=[]
  v=RepeatingVoice('missing.wav',play=lambda *a:calls.append(a));now=0
  for pop in [(19,25),(20,25),(21,25),(22,25),(195,200)]:
   for _ in range(8):
    msg=h.update(pop,True,now);e.update(pop,msg,h.seen>=2)
    v.update(msg=='Build House',now,event=e.event if msg=='Build House' else None);now+=.5
  self.assertEqual(len([c for c in calls if c[0]]),3)

class PopulationSegmentationTests(unittest.TestCase):
 def test_live_thirty_both_flash_phases(self):
  from tc_reminder.population import PopulationReader
  from tc_reminder.paths import ROOT
  from PIL import Image
  r=PopulationReader()
  for i in range(6):self.assertEqual(r.read(Image.open(ROOT/'samples'/f'pop-30-live-{i}.png')),(30,30))
 def test_previous_population_samples(self):
  from tc_reminder.population import PopulationReader
  from tc_reminder.paths import ROOT
  from PIL import Image
  r=PopulationReader()
  for name,want in [('foundation-five',(48,65)),('housed-three',(15,15)),('independent-housed',(15,15)),('independent-four',(36,65)),('research-one-tc',(13,25)),('live-false-overflow',(20,20))]:
   self.assertEqual(r.read(Image.open(ROOT/'samples'/f'{name}.png')),want,name)
  self.assertEqual(r.read(Image.open(ROOT/'samples/population-74-200.png'),(55,15,120,36)),(74,200))
 def test_blank_is_not_a_count(self):
  from tc_reminder.population import PopulationReader
  from PIL import Image
  self.assertIsNone(PopulationReader().read(Image.new('RGB',(2560,1440))))
class CombinedCueTests(unittest.TestCase):
 def test_idle_resumes_between_house_events(self):
  from tc_reminder.voice import choose_cue
  calls=[];v=RepeatingVoice('missing.wav',play=lambda *a:calls.append(a))
  def tick(now,event):
   clip,token,active=choose_cue(v,'Build House',True,event,now)
   if v.path!=clip:v.stop();v.path=clip
   v.update(active,now,event=token)
   return clip
  self.assertEqual(tick(0,('house',1)),'build-house.wav')
  self.assertEqual(tick(.5,('house',1)),'build-house.wav')
  self.assertEqual(tick(1.2,('house',1)),'idle.wav')
  tick(2.4,('house',1))
  self.assertEqual(tick(3,('house',2)),'build-house.wav')
  self.assertEqual(tick(4.2,('house',2)),'idle.wav')
  self.assertEqual([c[0] for c in calls if c[0]],['build-house.wav','idle.wav','idle.wav','build-house.wav','idle.wav'])
 def test_no_idle_without_shortfall_and_housed_priority(self):
  from tc_reminder.voice import choose_cue
  v=RepeatingVoice('missing.wav',play=lambda *a:None);v.last_event=('house',1)
  self.assertEqual(choose_cue(v,'Build House',False,('house',1),2),('idle.wav',None,False))
  self.assertEqual(choose_cue(v,'Housed',True,None,2),('housed.wav',None,True))
