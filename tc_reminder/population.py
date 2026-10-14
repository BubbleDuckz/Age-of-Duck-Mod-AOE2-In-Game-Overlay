"""Population glyphs calibrated from the user's HUD screenshots."""
import json
import cv2
import numpy as np
from .paths import ROOT

def glyphs(image):
    a=np.asarray(image.convert('RGB'))
    m=(((a.min(2)>180)&(a.max(2)-a.min(2)<50))|((a[:,:,0]>240)&(a[:,:,1]>240))).astype('uint8')
    _,_,stats,_=cv2.connectedComponentsWithStats(m)
    boxes=sorted([list(s[:4]) for s in stats[1:] if s[4]>=3],key=lambda s:s[0]);merged=[]
    for x,y,w,h in boxes:
        if merged and x<merged[-1][0]+merged[-1][2] and (h<9 or merged[-1][3]<9):
            px,py,pw,ph=merged.pop();merged.append([px,min(y,py),max(px+pw,x+w)-px,max(py+ph,y+h)-min(py,y)])
        else:merged.append([x,y,w,h])
    return [cv2.resize(m[y:y+h,x:x+w],(12,18),interpolation=cv2.INTER_NEAREST) for x,y,w,h in merged if h>=9 and m[y:y+h,x:x+w].sum()>=10]

class PopulationReader:
    def __init__(self):
        self.templates=[(t['char'],np.array(t['mask'],dtype='uint8')) for t in json.loads((ROOT/'population-glyphs.json').read_text())]
    def read(self,image,region=(450,15,535,36)):
        if image.info.get('hud'):
            # Remapped from user-drawn boxes: resampling blurs glyphs, so segment adaptively.
            result=self.read_adaptive(image,region)
            if result is not None:return result
        result=self.read_components(image,region)
        if result is None:result=self.read_fixed(image,region)
        if result is None:result=self.read_constrained(image,region)
        return result

    def read_adaptive(self,image,region):
        """Adaptive-threshold segmentation that can split a slash fused to a digit."""
        crop=np.asarray(image.crop(region).convert('RGB')).astype(float)
        lum=crop.min(2)
        top=np.percentile(lum,99.5)
        if top<120:return None
        mask=(lum>.5*top).astype('uint8')
        _,_,stats,_=cv2.connectedComponentsWithStats(mask)
        boxes=sorted([list(t[:4]) for t in stats[1:] if t[4]>=3],key=lambda t:t[0]);merged=[]
        for x,y,w,h in boxes:
            if merged and x<merged[-1][0]+merged[-1][2] and (h<9 or merged[-1][3]<9):
                px,py,pw,ph=merged.pop();merged.append([px,min(y,py),max(px+pw,x+w)-px,max(py+ph,y+h)-min(py,y)])
            else:merged.append([x,y,w,h])
        blobs=[b for b in merged if b[3]>=9 and mask[b[1]:b[1]+b[3],b[0]:b[0]+b[2]].sum()>=10]
        if not 3<=len(blobs)<=6:return None
        digit=float(np.median([b[2] for b in blobs]))
        def piece(x0,x1,y,h):
            return cv2.resize(mask[y:y+h,x0:x1],(12,18),interpolation=cv2.INTER_NEAREST)
        # Each blob is one glyph, or (when clearly wider than a digit) two glyphs: try both orders.
        options=[]
        for x,y,w,h in blobs:
            if w>1.35*digit:
                cut=max(2,int(round(w-digit)))
                options.append([[(x,x+cut,y,h),(x+cut,x+w,y,h)],[(x,x+w-cut,y,h),(x+w-cut,x+w,y,h)]])
            else:options.append([[(x,x+w,y,h)]])
        best=None
        def score(piece_masks):
            chars,total=[],0.0
            for g in piece_masks:
                scores={}
                for char,t in self.templates:
                    value=np.count_nonzero(g&t)/max(1,np.count_nonzero(g|t))
                    scores[char]=max(scores.get(char,0),value)
                ranked=sorted(scores.items(),key=lambda v:-v[1])
                chars.append(ranked[0][0]);total+=ranked[0][1]
            return chars,total/len(piece_masks)
        import itertools
        for choice in itertools.product(*options):
            pieces=[p for group in choice for p in group]
            chars,mean=score([piece(*p) for p in pieces])
            text=''.join(chars)
            if text.count('/')!=1:continue
            used,cap=text.split('/')
            if not (used.isdigit() and cap.isdigit()):continue
            used,cap=int(used),int(cap)
            if cap<=0 or cap>999 or cap%5 or used>cap+5:continue
            if best is None or mean>best[0]:best=(mean,(used,cap))
        return best[1] if best and best[0]>=.6 else None

    def read_constrained(self,image,region):
        """Last resort for HUDs whose glyphs match the templates only loosely (other UI scales).

        Each glyph keeps its few best digit candidates and the combination is chosen by
        score, but only combinations that are valid populations are allowed: "used/cap"
        with a cap that is a multiple of five (Town Centres, Houses and Castles add 5 or 20).
        A reading is refused when a different valid population scores nearly as well.
        """
        shapes=glyphs(image.crop(region))
        if not 3<=len(shapes)<=7:return None
        options=[]
        for g in shapes:
            scores={}
            for char,t in self.templates:
                score=np.count_nonzero(g&t)/max(1,np.count_nonzero(g|t))
                scores[char]=max(scores.get(char,0),score)
            ranked=sorted(scores.items(),key=lambda p:-p[1])
            options.append([(c,v) for c,v in ranked[:3] if v>=.45])
        slashes=[i for i,o in enumerate(options) if o and o[0][0]=='/' and o[0][1]>=.6]
        if len(slashes)!=1:return None
        cut=slashes[0]
        left,right=options[:cut],options[cut+1:]
        if not 1<=len(left)<=3 or not 1<=len(right)<=3:return None
        candidates={}
        def combos(groups):
            results=[('',0.0)]
            for group in groups:
                digits=[(c,v) for c,v in group if c.isdigit()]
                if not digits:return []
                results=[(text+c,total+v) for text,total in results for c,v in digits]
            return results
        for used_text,used_score in combos(left):
            for cap_text,cap_score in combos(right):
                used,cap=int(used_text),int(cap_text)
                if cap<=0 or cap>999 or cap%5 or used>cap+5:continue
                mean=(used_score+cap_score+options[cut][0][1])/len(shapes)
                key=(used,cap)
                if mean>candidates.get(key,0):candidates[key]=mean
        if not candidates:return None
        ranked=sorted(candidates.items(),key=lambda p:-p[1])
        if ranked[0][1]<.6:return None
        if len(ranked)>1 and ranked[0][1]-ranked[1][1]<.03:return None
        return ranked[0][0]
    def read_components(self,image,region):
        chars=[]
        for g in glyphs(image.crop(region)):
            scores={}
            for char,t in self.templates:
                score=np.count_nonzero(g&t)/max(1,np.count_nonzero(g|t))
                scores[char]=max(scores.get(char,0),score)
            rank=sorted(scores.items(),key=lambda p:-p[1])
            if len(rank)<2:return None
            score=rank[0][1];margin=score-rank[1][1]
            if not ((score>=.78 and margin>=.08) or (score>=.72 and margin>=.20)):return None
            chars.append(rank[0][0])
        value=''.join(chars).split('/')
        if len(value)!=2 or not all(v.isdigit() for v in value):return None
        used,cap=map(int,value)
        return (used,cap) if 0<cap<=999 and used<=999 else None

    def read_fixed(self,image,region):
        # Calibrated HUD font has an 8.5px digit advance and a 5px slash.
        # Fixed cells preserve disconnected zeros and separate touching slash/digits.
        a=np.asarray(image.crop(region).convert('RGB'))
        m=(((a.min(2)>180)&(a.max(2)-a.min(2)<50))|((a[:,:,0]>240)&(a[:,:,1]>240))).astype('uint8')
        xs=np.where(np.any(m,axis=0))[0]
        if not len(xs):return None
        candidates=[]
        for left in range(1,4):
            for right in range(1,4):
                if abs((xs[-1]-xs[0]+1)-(8.5*(left+right)+4))>3:continue
                for shift in (-1,0,1):
                    start=xs[0]+shift
                    bounds=[round(start+i*8.5) for i in range(left+1)]
                    bounds+=[round(start+left*8.5+5+i*8.5-.01) for i in range(right+1)]
                    chars=[];scores=[]
                    for i,(x,end) in enumerate(zip(bounds,bounds[1:])):
                        patch=m[:,max(0,x):max(0,end)]
                        ys,xx=np.where(patch)
                        if not len(ys):break
                        g=cv2.resize(patch[ys.min():ys.max()+1,xx.min():xx.max()+1],(12,18),interpolation=cv2.INTER_NEAREST)
                        ranked={}
                        for char,t in self.templates:
                            if (i==left)!=(char=='/'):continue
                            score=np.count_nonzero(g&t)/max(1,np.count_nonzero(g|t))
                            ranked[char]=max(ranked.get(char,0),score)
                        best=sorted(ranked.items(),key=lambda x:-x[1])
                        if not best or best[0][1]<.76:break
                        if len(best)>1 and best[0][1]-best[1][1]<.08:break
                        chars.append(best[0][0]);scores.append(best[0][1])
                    if len(chars)==left+right+1:
                        used,cap=map(int,''.join(chars).split('/'))
                        if cap>0:candidates.append((sum(scores)/len(scores),(used,cap)))
        if not candidates:return None
        candidates.sort(reverse=True)
        different=[score for score,value in candidates if value!=candidates[0][1]]
        if different and candidates[0][0]-max(different)<.05:return None
        return candidates[0][1]

class HousingReminder:
    def __init__(self):self.previous=None;self.seen=0
    def update(self,population,safe):
        if not safe or population is None:
            self.previous=None;self.seen=0;return ''
        self.seen=self.seen+1 if population==self.previous else 1
        self.previous=population
        if self.seen<2:return ''
        used,cap=population
        if cap>=200:return ''
        if used>=cap:return 'Housed'
        return 'Build House' if cap-used<=5 else ''


class BuildHouseEvents:
    """One cue per warning entry or confirmed population increase; ignore unsafe gaps."""
    def __init__(self):
        self.previous=None
        self.warning=False
        self.serial=0
    def update(self,population,housing,confirmed):
        if not confirmed or population is None:return
        used,_=population
        warning=housing=='Build House'
        if warning and (not self.warning or self.previous is None or used>self.previous):
            self.serial+=1
        self.previous=used
        self.warning=warning
    @property
    def event(self):return ('build-house',self.serial)


class StableHousingReminder:
    """Bridge brief font flashes only after two confirmed readings."""
    def __init__(self):
        self.reader=HousingReminder();self.last_valid=None;self.last_message=''
    def update(self,population,safe,now):
        if not safe:
            self.__init__();return ''
        if population is None:
            if self.last_valid is not None and now-self.last_valid<=1.25:return self.last_message
            self.__init__();return ''
        message=self.reader.update(population,True)
        self.last_valid=now
        if self.reader.seen>=2:self.last_message=message
        else:self.last_message=''
        return message
    @property
    def seen(self):return self.reader.seen
