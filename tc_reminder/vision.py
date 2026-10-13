"""Screenshot-derived template recognition. Unknown evidence is never idle evidence."""
import json
from pathlib import Path
import cv2
import numpy as np
from PIL import Image, ImageDraw
from .clock_reader import ClockReader
from .population import PopulationReader
from .validation_gate import approved

from .paths import ROOT
from hud_regions import FlashTracker, text_mask, REGIONS as HUD_REGIONS


def gray(im):
    return cv2.cvtColor(np.asarray(im.convert('RGB')), cv2.COLOR_RGB2GRAY)


def similarity(a, b, mask=None):
    if a.shape != b.shape or a.size == 0:
        return 0.0
    result = cv2.matchTemplate(a, b, cv2.TM_CCOEFF_NORMED, mask=mask)
    value = float(result[0, 0])
    return value if np.isfinite(value) else 0.0


class Detector:
    def __init__(self, profile=None):
        self.alerts_validated = approved() if profile is None else False
        self.profile = profile or json.loads((ROOT / 'calibration.json').read_text())
        self.templates = [(t, gray(Image.open(ROOT / t['file']))) for t in self.profile['templates']]
        self.templates = [(t, (im>210).astype(np.uint8)*255 if t.get('binary') else im) for t,im in self.templates]
        self.previous_clock = None
        self.clock_changed = None
        self.clock_edges = 0
        self.clock_reader=ClockReader()
        self.population_reader=PopulationReader()
        # User-drawn HUD areas (hud_regions.HudRegions); None keeps the built-in layout.
        self.regions=None
        self.flash=FlashTracker()

    def reset_clock(self):
        self.previous_clock = None
        self.clock_changed = None
        self.clock_edges = 0

    def rect(self, name, size):
        r = list(self.profile['regions'][name])
        if name.startswith('selection') or name == 'bottom_anchor':
            delta = size[1] - self.profile['size'][1]
            r[1] += delta
            r[3] += delta
        if name=='bottom_anchor':
            delta=size[0]-self.profile['size'][0];r[0]+=delta;r[2]+=delta
        return r

    def matches(self, image, category, region, threshold):
        x0, y0, x1, y1 = region
        hay = gray(image.crop(region))
        hits = []
        for meta, template in self.templates:
            if meta['kind'] != category or template.shape[0] > hay.shape[0] or template.shape[1] > hay.shape[1]:
                continue
            search = (hay>210).astype(np.uint8)*255 if meta.get('binary') else hay
            result = cv2.matchTemplate(search, template, cv2.TM_CCOEFF_NORMED)
            # Bound candidate work even on pathological input.
            for _ in range(64):
                _, score, _, (x, y) = cv2.minMaxLoc(result)
                if score < (max(threshold,.94) if meta.get('reference_only') else threshold) or not np.isfinite(score):
                    break
                h, w = template.shape
                hits.append({'kind': category, 'box': [x+x0, y+y0, x+x0+w, y+y0+h], 'score': score,
                             'name':meta.get('label',Path(meta['file']).stem)})
                result[max(0,y-h//2):y+h//2+1, max(0,x-w//2):x+w//2+1] = -1
        kept = []
        for hit in sorted(hits, key=lambda v: -v['score']):
            x,y,r,b = hit['box']
            if not any(abs(x-h['box'][0]) < (r-x)*0.7 and abs(y-h['box'][1]) < (b-y)*0.7 for h in kept):
                kept.append(hit)
        return sorted(kept, key=lambda v:v['box'][0])

    def normalize_frame(self,image):
        if image.info.get('hud'):return image
        if self.regions is not None and self.regions.usable(image.size):return self.regions.build_canvas(image)
        target=tuple(self.profile['size'])
        if all(abs(a-b)<=4 for a,b in zip(image.size,target)):return image
        # UI size follows height; preserve aspect ratio and anchor each region.
        if image.width>=640 and image.height>=480:
            return image.resize((round(image.width*target[1]/image.height),target[1]),Image.Resampling.BICUBIC)
        return image

    def hud_text_present(self, image):
        for key in ('population', 'clock'):
            x0, y0, x1, y1 = HUD_REGIONS[key]['canon']
            region = image.crop((x0 - 4, y0 - 4, x1 + 4, y1 + 4))
            if int(text_mask(region, HUD_REGIONS[key]['mask']).sum()) < 20:
                return False
        return True

    def analyze(self, image, threshold=.86, now=None):
        image=self.normalize_frame(image)
        p = self.profile
        result = {'busy': 0, 'busy_upper_bound':0, 'non_tc':0, 'housed': 0, 'research':0, 'research_waiting':0, 'waiting':0, 'selected_tcs': None, 'gameplay': False,
                  'confident': False, 'advancing': False, 'hits': [], 'unknown': [], 'reason': '', 'context':'unknown'}
        if abs(image.height-p['size'][1])>4 or image.width<1000:
            result['reason'] = 'Resolution differs from calibration — recalibrate before alerts'
            return result
        blockers=self.matches(image,'blocker',[image.width//4,image.height//4,image.width*3//4,image.height*3//4],.90)
        if blockers:
            result['blocker_hits']=blockers
            result['blocked']=True
            result['context']='pause' if any('paused' in h['name'] for h in blockers) else 'menu'
            result['reason']='Recognized pause/menu overlay'
            self.reset_clock()
        anchors = []
        if image.info.get('hud'):
            # Remapped frame: the HUD skin is unknown, so gameplay means the population and
            # clock boxes both contain text. A static clock still silences alerts (not advancing).
            anchors = [self.hud_text_present(image)]
            result['pop_flash'] = self.flash.update(image.info.get('pop_flash_fraction', 0.0), now if now is not None else 0.0)
        else:
            for kind in ('top_anchor', 'bottom_anchor'):
                anchors.append(bool(self.matches(image, kind, self.rect(kind,image.size), .94)))
        result['gameplay'] = all(anchors) and not blockers
        if not all(anchors):
            if not blockers:result['reason'] = 'Gameplay HUD anchors missing or obscured'
            self.reset_clock()
            return result
        if not blockers:result['context']='gameplay'
        result['clock_seconds']=self.clock_reader.read(image)
        result['population']=self.population_reader.read(image)
        result.update(self.analyze_queue(image,threshold))
        selection = self.matches(image, 'tc', self.rect('selection',image.size), threshold)
        result['selection_hits'] = selection
        # Require a calibrated TC command button as well as the distinctive group portraits.
        identity = self.matches(image, 'tc_command', self.rect('selection_command',image.size), .94)
        if identity and 0 < len(selection) < p['selection_visible_limit']:
            result['selected_tcs'] = len(selection)
        single_region = self.rect('selection_single',image.size)
        title = self.matches(image,'tc_single_title',single_region,.86)
        portrait = self.matches(image,'tc_single_portrait',single_region,.94)
        if title and portrait and identity:
            result['selected_tcs'] = 1
            result['selection_hits'] = title + portrait
        clock = np.asarray(image.crop(self.rect('clock',image.size)).convert('L')) > 185
        if now is not None and not blockers:
            if self.previous_clock is not None and np.count_nonzero(clock != self.previous_clock) > 12:
                self.clock_changed = now
                self.clock_edges += 1
            self.previous_clock = clock
            result['advancing'] = self.clock_edges >= 2 and self.clock_changed is not None and now-self.clock_changed < 1.25
        result['confident'] = True  # Only matched TC activity contributes to the count.
        if blockers:
            result['confident']=False
            result['reason']='Recognized pause/menu overlay'
            return result
        if result['queue_overflow']:
            result['confident']=False
            result['reason']='Queue reaches calibrated region edge — possible overflow'
            return result
        result['reason'] = ('Clock stopped or not yet verified' if not result['advancing'] else
                            'Unmatched queue boxes ignored (TC allowlist)' if result['unknown'] or result['waiting'] else
                            'Screen evidence recognized; non-TC production excluded')
        return result

    def analyze_queue(self,image,threshold=.86):
        """Analyze actual queue pixels; usable on supplied top-left crops without claiming gameplay."""
        p=self.profile
        result={'busy':0,'research':0,'research_waiting':0,'waiting':0,'housed':0,
                'busy_upper_bound':0,'non_tc':0,'hits':[],'unknown':[],'unclassified':0,'queue_overflow':False,'possible_housed':False}
        # These small regions are explicitly marked on actual screenshots.
        queue = self.rect('queue', image.size)
        queue[2]=min(queue[2],image.width)
        for kind in ('villager', 'research', 'research_waiting', 'housed', 'non_tc'):
            result['hits'] += self.matches(image, kind, queue, max(.95,threshold) if kind=='non_tc' else threshold)
        # Consolidate variant templates into ONE entry per queue slot.
        slots = {}
        for hit in result['hits']:
            centre = (hit['box'][0]+hit['box'][2])/2
            slot = int((centre - queue[0])/p['queue_pitch'])
            if slot not in slots or slots[slot]['score'] < hit['score']:
                slots[slot] = hit
        rgb = np.asarray(image.convert('RGB'))
        for index, hit in slots.items():
            x = round(queue[0]+index*p['queue_pitch'])
            patch = rgb[queue[1]+2:queue[1]+35,x+2:x+35].astype(float)
            red = np.mean((patch[:,:,0]>90)&(patch[:,:,0]>1.6*patch[:,:,1])&(patch[:,:,0]>1.6*patch[:,:,2]))
            # Observed housed examples: 18–32% red; observed running examples: 0%.
            if hit['kind']=='housed' and red < .12:
                hit['kind']='villager'
            if hit['kind']=='villager' and red >= .12:
                hit['kind'] = 'housed'
            if hit['kind'] in ('research','research_waiting','villager'):
                art=rgb[queue[1]+3:queue[1]+20,x+4:x+31].astype(float)
                gold=np.mean((art[:,:,0]>100)&(art[:,:,1]>65)&(art[:,:,0]>1.4*art[:,:,2])&(art[:,:,1]>1.3*art[:,:,2]))
                # Observed waiting art is >97% gold; active examples are <37%.
                # Grayscale correlation alone confuses these tint variants.
                if hit['kind']=='villager':
                    if gold>.85:hit['kind']='waiting'
                else:hit['kind']='research_waiting' if gold>.85 else 'research'

        result['hits'] = list(slots.values())
        result['non_tc']=sum(h['kind']=='non_tc' for h in result['hits'])
        result['busy'] = sum(h['kind']=='villager' for h in result['hits'])
        result['research'] = sum(h['kind']=='research' for h in result['hits'])
        # Entries may share a TC. Their sum is an upper bound, not an exact TC count.
        # A shortfall even against this bound proves a possible missing busy TC.
        result['busy_upper_bound'] = result['busy'] + result['research']
        result['waiting'] = sum(h['kind']=='waiting' for h in result['hits'])
        result['research_waiting'] = sum(h['kind']=='research_waiting' for h in result['hits'])
        result['housed'] = sum(h['kind'] == 'housed' for h in result['hits'])
        # Tiles that no stored picture matches. They are shown in debug and also counted as
        # possible activity (see below), but only when they continue the row of tiles that
        # starts at the left edge: the queue fills from the left, so isolated "frames" further
        # right are terrain or noise.
        pitch = int(round(p['queue_pitch']))
        tile_count = int((queue[2]-queue[0])/p['queue_pitch'])
        def has_frame(x, y):
            colour = rgb[max(0,y-1):y+p['queue_height']+1, x:x+pitch].astype(float)
            if colour.shape[0] < 8 or colour.shape[1] < pitch:
                return False
            neutral = (colour.max(2)-colour.min(2)<28)&(colour.mean(2)>65)
            # Actual box frames are neutral grey/white. Blue range lines and tan terrain
            # are not frames. Require substantial top AND bottom border support.
            if np.count_nonzero(neutral[:4]) > pitch*.6 and np.count_nonzero(neutral[-4:]) > pitch*.6:
                return True
            # Progress shading hides the frame on some tiles; the white hotkey letter in the
            # bottom-right corner (Q, A, Z ...) is on every queue tile.
            corner = rgb[y+18:y+p['queue_height'], x+14:x+pitch].astype(float)
            return corner.size > 0 and np.count_nonzero(corner.min(2) > 215) >= 14
        framed = {}
        for index in range(tile_count):
            if index in slots:
                continue
            x0 = round(queue[0] + index*p['queue_pitch'])
            # Another skin or a rescaled box can sit a few pixels off the calibrated grid.
            for dy in (0, -1, 1, -2, 2, -3, 3):
                for dx in (0, -1, 1, -2, 2, -3, 3):
                    if has_frame(x0+dx, queue[1]+dy):
                        framed[index] = (x0+dx, queue[1]+dy)
                        break
                if index in framed:
                    break
        row_end = 0
        while row_end in slots or row_end in framed:
            row_end += 1
        for index, (x, y) in sorted(framed.items()):
            if index >= row_end:
                continue
            box = [x, y, x+pitch, y+p['queue_height']]
            result['unknown'].append(box)
            art = rgb[y+2:y+35, x+2:x+35].astype(float)
            red = np.mean((art[:,:,0]>90)&(art[:,:,0]>1.6*art[:,:,1])&(art[:,:,0]>1.6*art[:,:,2]))
            result['possible_housed'] |= bool(red>=.12)
            top = rgb[y+3:y+20, x+4:x+31].astype(float)
            gold = np.mean((top[:,:,0]>100)&(top[:,:,1]>65)&(top[:,:,0]>1.4*top[:,:,2])&(top[:,:,1]>1.3*top[:,:,2]))
            # A research tile turns green as its progress bar fills (Age up at 70% ...), which
            # no stored template covers. Green progress is research in progress.
            green = np.mean((art[:,:,1]>70)&(art[:,:,1]>1.25*art[:,:,0])&(art[:,:,1]>1.25*art[:,:,2]))
            if gold > .85:
                result['waiting'] += 1            # queued behind another item: not activity
            elif green >= .22 and red < .12:
                result['hits'].append({'kind':'research','box':box,'score':float(green),'name':'research-progress'})
            else:
                result['unclassified'] += 1
        # Recount now that green research tiles were found among the unclassified boxes.
        result['research'] = sum(h['kind']=='research' for h in result['hits'])
        # A queue tile nothing recognises might be Town Centre production in a state with no
        # stored picture (age-up progress, a queued unit with a count badge, another skin).
        # Treat it as possible activity: wrongly staying quiet beats a false idle alarm.
        result['busy_upper_bound'] = result['busy'] + result['research'] + result['unclassified']
        result['queue_overflow'] = any(index>=int((queue[2]-queue[0])/p['queue_pitch'])-1 and hit['kind']!='non_tc' for index,hit in slots.items())
        # Unmatched terrain/units cannot veto the user's explicit TC allowlist.
        # Only recognized TC activity at the boundary indicates possible truncation.
        return result

    def annotate(self, image, result):
        im = image.copy()
        d = ImageDraw.Draw(im)
        for name in self.profile['regions']:
            r = self.rect(name,image.size)
            d.rectangle(r, outline='#7398ba', width=2)
        for hit in result['hits'] + result.get('selection_hits',[]) + result.get('blocker_hits',[]):
            x,y,r,b = hit['box']
            colour = '#ffb454' if hit['kind']=='housed' else '#56e6b1'
            d.rectangle((x,y,r,b),outline=colour,width=2)
            d.text((x,max(0,y-13)),f"{hit['kind']} {hit['score']:.2f}",fill=colour)
        for r in result['unknown']:
            d.rectangle(r,outline='#ff6978',width=2)
        return im
