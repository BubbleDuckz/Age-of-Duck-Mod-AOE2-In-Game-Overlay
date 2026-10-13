"""User-drawn HUD areas.

Automatic recognition assumes one HUD skin at one interface size. Instead, the player
draws a box over each HUD item once. Every box is cut out of the game frame, rescaled so
its contents have the size the readers were calibrated on, and pasted at the position
the readers expect. The existing recognisers then run unchanged on that "remapped"
frame, whatever the resolution, aspect ratio or UI scale of the player's game.

Boxes are stored as fractions of the game window, so they survive moving the game between
monitors of the same aspect ratio.
"""
import json
from collections import deque
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

CANVAS = (2560, 1440)
ASPECT_TOLERANCE = 0.02
QUEUE_TILE = 37  # height in px of one production-queue icon in the calibrated frame

# canon: where the readers expect the text, in the calibrated 2560x1440 frame (x0, y0, x1, y1).
# default: a sensible starting box for the standard HUD at 1440p.
REGIONS = {
    'population': dict(
        title='Population', canon=(455, 22, 492, 34), default=(450, 15, 535, 36), mask='bright',
        hint='Drag over the population numbers (used / cap, e.g. 20/20).'),
    'villagers': dict(
        title='Villagers', canon=(429, 33, 443, 45), default=(410, 32, 449, 49), mask='cyan', pad=1,
        hint='Drag over the villager count number.'),
    'clock': dict(
        title='Game clock', canon=(851, 9, 911, 21), default=(850, 5, 914, 24), mask='clock',
        hint='Drag over the match clock (e.g. 00:12:28).'),
    'queue': dict(
        title='TC queue', canon=None, default=(0, 58, 300, 95), mask=None,
        hint='Start at the left edge of the first queue icon; make the box one icon tall.'),
}
ORDER = ['population', 'villagers', 'clock', 'queue']


def text_mask(image, kind):
    a = np.asarray(image.convert('RGB')).astype(int)
    if kind == 'bright':
        return ((a.min(2) > 180) & (a.max(2) - a.min(2) < 50)) | ((a[:, :, 0] > 240) & (a[:, :, 1] > 240))
    if kind == 'cyan':
        # Digits only: white text next to the villager counter must not stretch the box.
        return (a[:, :, 1] > 150) & (a[:, :, 2] > 150) & (a[:, :, 0] < a[:, :, 1] - 10)
    return (a.min(2) > 185) & (a.max(2) - a.min(2) < 35)


def mask_bbox(mask):
    ys, xs = np.where(mask)
    if not len(xs):
        return None
    return int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1


def number_run(mask):
    """Bounding box of the number in a loose box, ignoring icons and stray pixels beside it.

    Components are glyph-sized blobs; start from the right-most tall one (the number is the
    last thing in the box) and walk left while neighbours have a matching height and a small gap.
    """
    count, _labels, stats, _ = cv2.connectedComponentsWithStats(mask.astype('uint8'), connectivity=8)
    blobs = [tuple(int(v) for v in row[:4]) for row in stats[1:count] if row[4] >= 4 and row[3] >= 5]
    if not blobs:
        return mask_bbox(mask)
    tallest = max(b[3] for b in blobs)
    seeds = [b for b in blobs if b[3] >= 0.6 * tallest]
    seed = max(seeds, key=lambda b: b[0] + b[2])
    height = seed[3]
    group, left = [seed], seed[0]
    others = sorted((b for b in blobs if b is not seed and b[0] + b[2] <= seed[0] + seed[2]),
                    key=lambda b: -(b[0] + b[2]))
    for blob in others:
        x, y, w, h = blob
        gap = left - (x + w)
        overlap = min(y + h, seed[1] + seed[3]) - max(y, seed[1])
        if gap > 0.9 * height:
            break
        if 0.55 * height <= h <= 1.5 * height and overlap >= 0.5 * min(h, height):
            group.append(blob)
            left = min(left, x)
        elif h < 0.55 * height and gap <= 0.3 * height:
            continue   # broken-off fragment of a glyph
    x0 = min(b[0] for b in group)
    y0 = min(b[1] for b in group)
    x1 = max(b[0] + b[2] for b in group)
    y1 = max(b[1] + b[3] for b in group)
    return x0, y0, x1, y1


def flash_fraction(image):
    """Share of yellow / red pixels: the population box flashes these colours when housed."""
    a = np.asarray(image.convert('RGB')).astype(int)
    yellow = (a[:, :, 0] > 130) & (a[:, :, 1] > 130) & (a[:, :, 2] < 90) & (abs(a[:, :, 0] - a[:, :, 1]) < 70)
    red = (a[:, :, 0] > 150) & (a[:, :, 1] < 80) & (a[:, :, 2] < 80)
    return float(np.mean(yellow | red))


class FlashTracker:
    """A flash is a jump above the box's own recent resting colour, so yellowish skins never false-alarm."""
    WINDOW = 25.0
    JUMP = 0.25

    def __init__(self):
        self.history = deque()

    def update(self, fraction, now):
        self.history.append((now, fraction))
        while self.history and now - self.history[0][0] > self.WINDOW:
            self.history.popleft()
        baseline = min(value for _, value in self.history)
        return fraction - baseline >= self.JUMP

    def reset(self):
        self.history.clear()


class HudRegions:
    def __init__(self, path=None):
        self.path = Path(path) if path else None
        self.boxes = {}
        self.size = None
        self.load()

    # -- persistence ------------------------------------------------------------
    def load(self):
        self.boxes, self.size = {}, None
        if not self.path:
            return
        try:
            data = json.loads(self.path.read_text(encoding='utf-8'))
            boxes = {k: tuple(float(v) for v in data['boxes'][k]) for k in ORDER}
            if all(len(b) == 4 and 0 <= b[0] < b[2] <= 1 and 0 <= b[1] < b[3] <= 1 for b in boxes.values()):
                self.boxes, self.size = boxes, tuple(data.get('size') or ()) or None
        except (OSError, ValueError, KeyError, TypeError):
            self.boxes, self.size = {}, None

    def save(self):
        if not self.path:
            return
        payload = {'version': 1, 'size': list(self.size or ()), 'boxes': {k: list(v) for k, v in self.boxes.items()}}
        temp = self.path.with_suffix('.tmp')
        temp.write_text(json.dumps(payload, indent=2), encoding='utf-8')
        temp.replace(self.path)

    def set_boxes(self, boxes, size):
        self.boxes = {k: tuple(boxes[k]) for k in ORDER}
        self.size = tuple(size)
        self.save()

    def clear(self):
        self.boxes, self.size = {}, None
        if self.path and self.path.exists():
            self.path.unlink()

    # -- use ----------------------------------------------------------------------
    @property
    def configured(self):
        return bool(self.boxes)

    def usable(self, size):
        """Boxes apply while the game window has the aspect ratio they were drawn on."""
        if not self.boxes:
            return False
        if not self.size:
            return True
        return abs((size[0] / size[1]) / (self.size[0] / self.size[1]) - 1) <= ASPECT_TOLERANCE

    def status(self, size=None):
        if not self.boxes:
            return 'Using the built-in layout (standard HUD, default interface size).'
        label = f'{self.size[0]}×{self.size[1]}' if self.size else 'your screen'
        if size and not self.usable(size):
            return f'Areas were drawn for {label}; this window has a different shape, so set them up again.'
        return f'Using your own HUD areas (drawn at {label}).'

    def pixel_box(self, key, size):
        fx0, fy0, fx1, fy1 = self.boxes[key]
        return (round(fx0 * size[0]), round(fy0 * size[1]), max(round(fx1 * size[0]), round(fx0 * size[0]) + 2),
                max(round(fy1 * size[1]), round(fy0 * size[1]) + 2))

    def build_canvas(self, raw):
        """Remap the boxes onto a black calibrated-size frame the existing readers understand."""
        canvas = Image.new('RGB', CANVAS)
        info = {'hud': True}
        for key in ORDER:
            spec = REGIONS[key]
            crop = raw.crop(self.pixel_box(key, raw.size))
            if key == 'population':
                info['pop_flash_fraction'] = flash_fraction(crop)
            if key == 'queue':
                scale = QUEUE_TILE / max(1, crop.height)
                resized = crop.resize((max(1, round(crop.width * scale)), QUEUE_TILE), Image.Resampling.BICUBIC)
                canvas.paste(resized.crop((0, 0, min(resized.width, CANVAS[0]), QUEUE_TILE)), (0, 58))
                continue
            self._paste_text(canvas, crop, spec)
        canvas.info.update(info)
        return canvas

    @staticmethod
    def _paste_text(canvas, crop, spec):
        mask = text_mask(crop, spec['mask'])
        if mask_bbox(mask) is None:
            return
        # A loose box can include an icon beside the number: keep only the number itself.
        box = number_run(mask)
        cx0, cy0, cx1, cy1 = spec['canon']
        scale = (cy1 - cy0) / max(1, box[3] - box[1])
        pad = spec.get('pad', max(3, round((box[3] - box[1]) * 0.6)))
        sx0, sy0 = max(0, box[0] - pad), max(0, box[1] - pad)
        sx1, sy1 = min(crop.width, box[2] + pad), min(crop.height, box[3] + pad)
        part = crop.crop((sx0, sy0, sx1, sy1))
        part = part.resize((max(1, round(part.width * scale)), max(1, round(part.height * scale))), Image.Resampling.BICUBIC)
        canvas.paste(part, (cx0 - round((box[0] - sx0) * scale), cy0 - round((box[1] - sy0) * scale)))


def describe(raw, boxes, detector, villager_reader):
    """Human-readable result of reading each box, for the set-up screen."""
    regions = HudRegions()
    regions.boxes = {k: tuple(boxes[k]) for k in ORDER}
    canvas = regions.build_canvas(raw)
    out = {}
    pop = detector.population_reader.read(canvas)
    flash = canvas.info.get('pop_flash_fraction', 0)
    out['population'] = f'{pop[0]}/{pop[1]}' if pop else ('text found, not readable' if _has_text(canvas, 'population') else 'nothing found')
    if flash > 0.25:
        out['population'] += '  (flashing)'
    villagers = villager_reader.read(canvas)
    out['villagers'] = str(villagers) if villagers is not None else ('text found, not readable' if _has_text(canvas, 'villagers') else 'nothing found')
    out['clock'] = 'clock text found' if _has_text(canvas, 'clock') else 'nothing found'
    try:
        queue = detector.analyze_queue(canvas)
        out['queue'] = f"{queue['busy']} villager, {queue['research']} research icons" if (queue['hits'] or queue['unknown']) else 'no icons found'
    except Exception:
        out['queue'] = 'no icons found'
    return out


def _has_text(canvas, key):
    x0, y0, x1, y1 = REGIONS[key]['canon']
    region = canvas.crop((x0 - 4, y0 - 4, x1 + 4, y1 + 4))
    return int(text_mask(region, REGIONS[key]['mask']).sum()) >= 20
