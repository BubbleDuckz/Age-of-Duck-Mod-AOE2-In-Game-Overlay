import json,unittest
from pathlib import Path
from PIL import Image
from tc_reminder.vision import Detector
class AgeResearchTests(unittest.TestCase):
 def test_supplied_feudal_queue(self):
  d=Detector();d.profile['regions']['queue']=[0,27,142,64]
  r=d.analyze_queue(Image.open('tc_reminder/samples/feudal-user-crop.png'))
  self.assertEqual(r['research'],1);self.assertEqual(r['busy_upper_bound'],1)
 def test_supplied_loom_queue(self):
  d=Detector();d.profile["regions"]["queue"]=[0,12,108,49]
  r=d.analyze_queue(Image.open("tc_reminder/samples/loom-user-crop.png"))
  self.assertEqual(r["research"],1);self.assertEqual(r["busy_upper_bound"],1)
 def test_town_watch_and_wheelbarrow(self):
  for name,y in [('town-watch',4),('wheelbarrow',1)]:
   im=Image.open('tc_reminder/samples/'+name+'-user-crop.png')
   d=Detector();d.profile['regions']['queue']=[0,y,im.width,y+37]
   r=d.analyze_queue(im)
   self.assertEqual(r['research'],1,name);self.assertEqual(r['busy_upper_bound'],1,name)
 def test_live_castle_progress(self):
  r=Detector().analyze_queue(Image.open('tc_reminder/samples/age-check-live.png'))
  self.assertEqual(r['research'],1);self.assertEqual(r['busy_upper_bound'],1)
 def test_green_castle_progress_across_resolutions(self):
  # Actual user pixels, composited onto a blank frame only to test resolution
  # normalization. This does not claim full gameplay recognition at each size.
  crop=Image.open('tc_reminder/samples/castle-green-normalized.png').convert('RGB')
  for width,height in [(1280,720),(1920,1080),(2560,1440),(3008,1692),(3840,2160),(3440,1440),(1280,1024)]:
   frame=Image.new('RGB',(round(width*1440/height),1440));frame.paste(crop,(0,0))
   frame=frame.resize((width,height),Image.Resampling.BICUBIC)
   d=Detector();r=d.analyze_queue(d.normalize_frame(frame))
   self.assertEqual(r['research'],1,(width,height,r['hits']))
   self.assertEqual(r['busy_upper_bound'],1,(width,height))
   self.assertEqual(r['waiting'],1,(width,height))
 def test_existing_queue_counts_unchanged(self):
  old=Detector(json.loads(Path('../../v1.17/source/tc_reminder/calibration.json').read_text()));new=Detector()
  # Compare only the original baseline fixtures; later captures include newly supported research.
  for p in Path('../../v1.17/source/tc_reminder/samples').glob('*.png'):
   if p.name=='age-check-live.png':continue
   im=Image.open(p).convert("RGB")
   if im.width<825 or im.height<95:continue
   a=old.analyze_queue(im);b=new.analyze_queue(im)
   self.assertEqual((a['busy'],a['research'],a['research_waiting']),(b['busy'],b['research'],b['research_waiting']),p.name)
if __name__=='__main__':unittest.main()

