import unittest
from PIL import Image
from tc_reminder.vision import Detector
from villager_reader import VillagerReader
class ResolutionTests(unittest.TestCase):
 def test_actual_new_resolution_frames(self):
  d=Detector()
  for name,pop,vils in [('resolution-current',(4,10),3),('resolution-live-2',(7,15),6),('resolution-tc',(9,15),8)]:
   im=Image.open('tc_reminder/samples/'+name+'.png');r=d.analyze(im)
   self.assertIn(r['context'],('gameplay','pause'));self.assertEqual(r['population'],pop)
   self.assertEqual(r['busy_upper_bound'],1);self.assertEqual(VillagerReader().read(d.normalize_frame(im)),vils)
 def test_actual_single_tc_after_scaling(self):
  r=Detector().analyze(Image.open('tc_reminder/samples/resolution-independent.png'))
  self.assertEqual(r['selected_tcs'],1);self.assertEqual(r['context'],'pause');self.assertEqual(r['population'],(9,15));self.assertEqual(r['busy_upper_bound'],1)
 def test_wide_and_narrow_hud_edge_anchoring(self):
  d=Detector();im=d.normalize_frame(Image.open('tc_reminder/samples/resolution-live-2.png'))
  for width in [1920,3440]:
   canvas=Image.new('RGB',(width,1440));canvas.paste(im.crop((0,0,1000,1440)),(0,0));canvas.paste(im.crop((1984,0,2560,1440)),(width-576,0))
   r=d.analyze(canvas);self.assertTrue(r['gameplay']);self.assertEqual(r['population'],(7,15));self.assertEqual(r['busy_upper_bound'],1)
 def test_blank_scaled_frames_are_not_gameplay(self):
  for size in [(1920,1080),(3840,2160),(3440,1440),(1280,1024)]:self.assertFalse(Detector().analyze(Image.new('RGB',size))['gameplay'])
if __name__=='__main__':unittest.main()
