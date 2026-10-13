"""Screen-only cyan villager counter, calibrated from real HUD captures."""
import json
from pathlib import Path
import cv2
import numpy as np

def masks(image):
 a=np.asarray(image.convert('RGB')).astype(int)
 m=((a[:,:,1]>150)&(a[:,:,2]>150)&((a[:,:,0]<a[:,:,1]-10)|(a.min(2)>185))).astype('uint8')
 xs=np.where(m.any(0))[0];segments=[];out=[]
 for x in xs:
  if not segments or x>segments[-1][-1]+1:segments.append([])
  segments[-1].append(x)
 for seg in segments:
  g=m[:,seg[0]:seg[-1]+1];ys=np.where(g.any(1))[0]
  if len(ys)<8:continue
  out.append(cv2.resize(g[ys[0]:ys[-1]+1],(12,18),interpolation=cv2.INTER_NEAREST))
 return out

def soft_glyphs(image):
 # Retain anti-aliased edge intensity: hard thresholding distorted narrow digits.
 a=np.asarray(image.convert('RGB')).astype('float32')
 intensity=np.minimum(a[:,:,1],a[:,:,2])/255.0
 xs=np.where((intensity>.55).any(0))[0];segments=[];out=[]
 for x in xs:
  if not segments or x>segments[-1][-1]+1:segments.append([])
  segments[-1].append(x)
 for seg in segments:
  g=intensity[:,seg[0]:seg[-1]+1];ys=np.where((g>.55).any(1))[0]
  if len(ys)<8:continue
  out.append(cv2.resize(g[ys[0]:ys[-1]+1],(12,18),interpolation=cv2.INTER_AREA))
 return out

class VillagerReader:
 def __init__(self):
  self.data=json.loads((Path(__file__).parent/'villager-glyphs.json').read_text())
  self.templates=[(t['char'],np.array(t['pixels'],dtype='float32')) for t in self.data['soft_templates']]
 def read(self,image):
  if abs(image.height-self.data['size'][1])>4 or image.width<535:return None
  return self.read_crop(image.crop(self.data['region']))
 def read_crop(self,crop):
  chars=[]
  for g in soft_glyphs(crop):
   scores={}
   for c,t in self.templates:
    value=float(cv2.matchTemplate(g,t,cv2.TM_CCOEFF_NORMED)[0,0]);scores[c]=max(scores.get(c,-1),value)
   rank=sorted(scores.items(),key=lambda v:-v[1])
   if len(rank)<2:return None
   score=rank[0][1];margin=score-rank[1][1]
   # Anti-aliasing can reduce absolute correlation; require a much clearer
   # winning digit before accepting a lower-scoring glyph.
   if not ((score>=.80 and margin>=.12) or (score>=.70 and margin>=.22)):return None
   chars.append(rank[0][0])
  if not chars or len(chars)>3:return None
  value=int(''.join(chars))
  return value if 0<=value<=250 else None
