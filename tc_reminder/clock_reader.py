"""Small screenshot-trained clock reader for detecting a visible match-time rewind.

Unreadable/untrained digits return None. They never become guessed zeroes.
"""
import json
from pathlib import Path
from functools import lru_cache
import numpy as np
from PIL import Image

from .paths import ROOT


def white_mask(image):
    a=np.asarray(image.convert('RGB'))
    return (a.min(2)>185)&(a.max(2)-a.min(2)<35)


class ClockReader:
    def __init__(self):
        self.profile=json.loads((ROOT/'clock-calibration.json').read_text())
        self.glyphs=load_glyphs((ROOT/'clock-calibration.json').stat().st_mtime_ns)

    def read(self,image):
        if image.height!=1440 or image.width<912:return None
        # Only process the observed clock strip, not the full screenshot.
        strip=image.crop((850,5,912,24))
        mask=white_mask(strip)
        digits=[]
        for x in self.profile['x']:
            g=mask[:,x-850:x-850+9]
            scores={}
            for char,template in self.glyphs:
                score=np.count_nonzero(g&template)/max(1,np.count_nonzero(g|template))
                scores[char]=max(scores.get(char,0),score)
            ranked=sorted(scores.items(),key=lambda pair:-pair[1])
            if ranked[0][1]<.85 or ranked[0][1]-ranked[1][1]<.15:return None
            digits.append(ranked[0][0])
        hours,minutes,seconds=int(''.join(digits[:2])),int(''.join(digits[2:4])),int(''.join(digits[4:]))
        if minutes>=60 or seconds>=60:return None
        return hours*3600+minutes*60+seconds


@lru_cache(maxsize=2)
def load_glyphs(version):
    profile=json.loads((ROOT/'clock-calibration.json').read_text())
    glyphs=[]
    for sample in profile['samples']:
        mask=white_mask(Image.open(ROOT/'samples'/sample['file']))
        for x,char in zip(profile['x'],sample['digits']):
            glyphs.append((char,mask[5:24,x:x+9]))
    return glyphs
