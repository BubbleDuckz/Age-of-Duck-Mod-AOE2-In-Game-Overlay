"""Town Centre selection counter that works at any resolution and interface size.

The Town Centre command card always carries the same Town Bell icon, and the selection
panel shows one identical Town Centre tile per selected Town Centre. The art never
changes between skins and sizes; only its pixel size, position and the panel background
do. So instead of looking at fixed pixels, search the bottom-left of the screen across
a ladder of scales:

1. find the Town Bell (this also gives the interface scale and the panel position),
2. count the Town Centre tiles beside it, at that same scale.

The selection panel can be read only after the Town Centres are selected, which is all
the reminder needs: the count is remembered afterwards.
"""
import time
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from .paths import ROOT

# Crops of selected-three.png (2560x1440, interface scale 1.0): the bell button art
# (the hotkey letter in its corner is left out) and the inside of one Town Centre tile.
SAMPLE = 'selected-three.png'
BELL_CROP = (214, 1376, 238, 1396)
TILE_CROP = (341, 1287, 365, 1309)
# Where the tiles sit relative to the bell at scale 1.0 (bell top-left -> first tile top-left).
TILE_DX, TILE_DY = 127, -89
TILE_PITCH = 35
SCALES = [round(0.6 * 1.07 ** i, 4) for i in range(0, 22)]      # 0.6 .. ~2.5
BELL_AREA = (0.0, 0.70, 0.32, 1.0)    # fractions of the frame searched for the Town Bell
BELL_THRESHOLD = 0.80
TILE_THRESHOLD = 0.55
RESCAN_SECONDS = 2.5          # full scale scan while the interface size is still unknown
KNOWN_RESCAN_SECONDS = 8.0    # once the size is known, only re-scan occasionally
MAX_TILES = 16


def _gray(image):
    return cv2.cvtColor(np.asarray(image.convert('RGB')), cv2.COLOR_RGB2GRAY)


def _resized(template, scale):
    h, w = template.shape
    size = (max(3, round(w * scale)), max(3, round(h * scale)))
    return cv2.resize(template, size, interpolation=cv2.INTER_AREA if scale < 1 else cv2.INTER_CUBIC)


def _best(region, template):
    if template.shape[0] > region.shape[0] or template.shape[1] > region.shape[1]:
        return 0.0, (0, 0)
    result = cv2.matchTemplate(region, template, cv2.TM_CCOEFF_NORMED)
    _, score, _, location = cv2.minMaxLoc(result)
    return (float(score) if np.isfinite(score) else 0.0), location


class SelectionFinder:
    def __init__(self):
        sample = Image.open(ROOT / 'samples' / SAMPLE).convert('RGB')
        self.bell = _gray(sample.crop(BELL_CROP))
        self.tile = _gray(sample.crop(TILE_CROP))
        self.scale = None          # scale of the Town Bell while a Town Centre is selected
        self.known_scale = None    # last scale that worked: tried first, cheaply, every frame
        self.scanned_at = -1e9

    def reset(self):
        self.scale = self.known_scale = None
        self.scanned_at = -1e9

    @staticmethod
    def region(size):
        """Generous bottom-left search area (the panel is always in this corner)."""
        width, height = size
        return 0, int(height * 0.55), int(width * 0.60), height

    def find_bell(self, gray, now):
        """(score, scale, (x, y)) of the Town Bell; scans all scales only occasionally."""
        anchor = self.scale or self.known_scale
        if anchor is not None:
            best = (0.0, None, None)
            for scale in [anchor * f for f in (0.96, 0.98, 1.0, 1.02, 1.04)]:
                score, location = _best(gray, _resized(self.bell, scale))
                if score > best[0]:
                    best = (score, scale, location)
            if best[0] >= BELL_THRESHOLD:
                return best
            wait = KNOWN_RESCAN_SECONDS
        else:
            wait = RESCAN_SECONDS
        if now - self.scanned_at < wait:
            return 0.0, None, None
        self.scanned_at = now
        ladder = SCALES
        best = (0.0, None, None)
        for scale in ladder:
            score, location = _best(gray, _resized(self.bell, scale))
            if score > best[0]:
                best = (score, scale, location)
        if best[0] >= BELL_THRESHOLD:
            # Refine around the coarse optimum.
            for scale in [best[1] * f for f in (0.97, 0.98, 0.99, 1.01, 1.02, 1.03)]:
                score, location = _best(gray, _resized(self.bell, scale))
                if score > best[0]:
                    best = (score, scale, location)
        return best

    def read(self, image, now=None):
        """Number of selected Town Centres, or None when no Town Centre selection is visible."""
        now = time.monotonic() if now is None else now
        x0, y0, x1, y1 = self.region(image.size)
        gray = _gray(image.crop((x0, y0, x1, y1)))
        height, width = gray.shape
        full_w, full_h = image.size
        ax0, ay0 = int(full_w * BELL_AREA[0]) - x0, int(full_h * BELL_AREA[1]) - y0
        ax1 = min(width, int(full_w * BELL_AREA[2]) - x0)
        corner = gray[max(0, ay0):, max(0, ax0):ax1]
        score, scale, location = self.find_bell(corner, now)
        if scale is not None:
            location = (location[0] + max(0, ax0), location[1] + max(0, ay0))
        if scale is None or score < BELL_THRESHOLD:
            self.scale = None        # command card gone; known_scale still guides the next look
            return None
        self.scale = self.known_scale = scale
        bx, by = location
        # Tiles sit above and to the right of the bell.
        left = max(0, int(bx + 40 * scale))
        top = max(0, int(by + (TILE_DY - 45) * scale))
        bottom = min(gray.shape[0], int(by + (TILE_DY + 70) * scale))
        band = gray[top:bottom, left:]
        tile = _resized(self.tile, scale)
        if band.shape[0] < tile.shape[0] or band.shape[1] < tile.shape[1]:
            return 1
        result = cv2.matchTemplate(band, tile, cv2.TM_CCOEFF_NORMED)
        hits = []
        for _ in range(MAX_TILES + 4):
            _, value, _, (x, y) = cv2.minMaxLoc(result)
            if not np.isfinite(value) or value < TILE_THRESHOLD:
                break
            hits.append((x, y, value))
            pitch = TILE_PITCH * scale
            result[max(0, y - int(pitch * .5)):y + int(pitch * .5) + 1, max(0, x - int(pitch * .5)):x + int(pitch * .5) + 1] = -1
        count = len(hits)
        if count == 0:
            return 1        # a single Town Centre shows a large portrait instead of tiles
        return count if count <= MAX_TILES else None
