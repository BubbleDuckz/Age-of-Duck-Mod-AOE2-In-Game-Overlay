# unit_ocr.py
import os, json, time, difflib
from dataclasses import dataclass
from collections import deque

import numpy as np
import cv2
from mss import mss
from PyQt5 import QtCore, QtGui, QtWidgets

# ---------------- Tunables ----------------
CAPTURE_TICK_MS         = 50     # capture cadence
OCR_MIN_INTERVAL        = 250    # min ms between OCR requests
HISTORY_LEN             = 6      # smoothing for label
REQUIRED_STABLE         = 2      # same label N times to commit
FUZZY_CUTOFF            = 0.50
ALLOWLIST               = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz -'"

# Motion gating + heartbeat
DIFF_PIXEL_THRESH       = 8
DIFF_FRACTION_THRESH    = 0.0015
FORCE_OCR_INTERVAL_MS   = 1500

MAX_COUNTERS_SHOWN      = 10

# ------------- Helpers / Models -------------
@dataclass
class ROI:
    left: int; top: int; width: int; height: int

class SelectionOverlay(QtWidgets.QWidget):
    rectSelected = QtCore.pyqtSignal(QtCore.QRect)
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint | QtCore.Qt.FramelessWindowHint | QtCore.Qt.Tool)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
        self._origin = None; self._current = None
        self.setGeometry(QtWidgets.QApplication.primaryScreen().geometry())

    def paintEvent(self, _):
        p = QtGui.QPainter(self); p.fillRect(self.rect(), QtGui.QColor(0,0,0,150))
        if self._origin and self._current:
            r = QtCore.QRect(self._origin, self._current).normalized()
            p.setCompositionMode(QtGui.QPainter.CompositionMode_Clear); p.fillRect(r, QtCore.Qt.transparent)
            p.setCompositionMode(QtGui.QPainter.CompositionMode_SourceOver)
            p.setPen(QtGui.QPen(QtGui.QColor(255,255,255,230), 2)); p.drawRect(r)

    def mousePressEvent(self, e):
        if e.button() == QtCore.Qt.LeftButton:
            self._origin = e.globalPos(); self._current = e.globalPos(); self.update()
    def mouseMoveEvent(self, e):
        if self._origin: self._current = e.globalPos(); self.update()
    def mouseReleaseEvent(self, e):
        if self._origin and e.button() == QtCore.Qt.LeftButton:
            self.rectSelected.emit(QtCore.QRect(self._origin, self._current).normalized()); self.close()

# ------------- Worker living in QThread -------------
# --- RapidOCR worker (no torch) ---
class OcrWorker(QtCore.QObject):
    finished = QtCore.pyqtSignal(str)
    _init_done = False

    def __init__(self, whitelist):
        super().__init__()
        self.whitelist = whitelist or []
        self.ocr = None
        self.name_lookup = {}  # injected by controller

    @QtCore.pyqtSlot()
    def init_in_thread(self):
        if self._init_done:
            return
        # Import and init RapidOCR from within the worker thread
        from rapidocr_onnxruntime import RapidOCR
        # Default models bundled inside the wheel; no extra downloads.
        self.ocr = RapidOCR()
        self._init_done = True

    @QtCore.pyqtSlot(np.ndarray)
    def process(self, bw_img: np.ndarray):
        if not self._init_done:
            self.init_in_thread()
        if self.ocr is None:
            self.finished.emit("")
            return

        # RapidOCR likes RGB uint8 images; we’ll give it the binarized image as 3-channel
        if len(bw_img.shape) == 2:
            rgb = cv2.cvtColor(bw_img, cv2.COLOR_GRAY2RGB)
        else:
            rgb = cv2.cvtColor(bw_img, cv2.COLOR_BGR2RGB)

        try:
            # result format: (boxes, texts, scores). We just want texts.
            _, texts, _ = self.ocr(rgb)
        except Exception:
            texts = []

        text = (texts[0].strip() if texts else "")
        text = "".join(ch for ch in text if ch.isalnum() or ch in " -'").strip()
        if not text:
            self.finished.emit("")
            return

        # snap to whitelist / DB names
        if self.whitelist:
            if text in self.whitelist:
                snapped = text
            else:
                low = text.lower()
                if low in self.name_lookup:
                    snapped = self.name_lookup[low]
                else:
                    import difflib
                    cand = difflib.get_close_matches(text, self.whitelist, n=1, cutoff=0.50)
                    snapped = cand[0] if cand else text
        else:
            snapped = text

        self.finished.emit(snapped)


# ------------- Public controller for embedding -------------
class UnitOcrDetector(QtCore.QObject):
    unitChanged   = QtCore.pyqtSignal(str)     # canonical unit name
    countersReady = QtCore.pyqtSignal(list)    # optional counters for UI

    def __init__(self, units_db_path: str, settings_path: str, parent=None, use_gpu=True):
        super().__init__(parent)
        self.units_db_path = units_db_path
        self.settings_path = settings_path
        self.use_gpu = use_gpu

        self._mss = None
        self._roi: ROI | None = None
        self._history = deque(maxlen=HISTORY_LEN)
        self._last_text = ""
        self._last_gray = None
        self._ocr_busy = False
        self._last_ocr_ms = 0
        self._last_force_ms = 0
        self._timer = QtCore.QTimer(self)
        self._timer.timeout.connect(self._tick)

        # Load DB
        self.UNITS_DB, self.WHITELIST, self.NAME_LOOKUP = self._load_units_db(self.units_db_path)

        # Worker thread
        self._thread = QtCore.QThread(self)
        self._worker = OcrWorker(self.WHITELIST)
        self._worker.name_lookup = self.NAME_LOOKUP
        self._worker.moveToThread(self._thread)
        self._worker.finished.connect(self._on_ocr_result)
        self._thread.start()
        QtCore.QMetaObject.invokeMethod(self._worker, "init_in_thread", QtCore.Qt.QueuedConnection)

        self._load_settings()

    # ---------- Public API ----------
    def start(self):
        if self._mss is None:
            self._mss = mss()
        if not self._timer.isActive():
            self._timer.start(CAPTURE_TICK_MS)

    def stop(self):
        if self._timer.isActive():
            self._timer.stop()

    def cleanup(self):
        try:
            if self._mss:
                self._mss.close()
        except Exception:
            pass
        self.stop()
        self._thread.quit()
        self._thread.wait(500)

    def pick_region(self, parent=None):
        sel = SelectionOverlay(parent)
        sel.rectSelected.connect(self._on_region_picked)
        sel.showFullScreen()

    # ---------- Internals ----------
    def _on_region_picked(self, rect: QtCore.QRect):
        screen = QtWidgets.QApplication.primaryScreen().geometry()
        x = max(0, min(rect.x(), screen.width()-10))
        y = max(0, min(rect.y(), screen.height()-10))
        w = max(20, min(rect.width(),  screen.width()-x))
        h = max(20, min(rect.height(), screen.height()-y))
        self._roi = ROI(x,y,w,h)
        self._last_gray = None
        self._save_settings()

    def _load_units_db(self, path: str):
        if not os.path.isfile(path):
            return {}, [], {}
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        names = list(data.keys())
        lookup = {k.lower(): k for k in names}
        return data, names, lookup

    def _load_settings(self):
        try:
            if os.path.exists(self.settings_path):
                s = json.load(open(self.settings_path, "r", encoding="utf-8"))
                roi = s.get("roi_text")
                if roi and all(k in roi for k in ("left","top","width","height")):
                    self._roi = ROI(**roi)
        except Exception:
            pass

    def _save_settings(self):
        try:
            s = {}
            if self._roi:
                s["roi_text"] = {"left": self._roi.left, "top": self._roi.top,
                                 "width": self._roi.width, "height": self._roi.height}
            json.dump(s, open(self.settings_path, "w", encoding="utf-8"), indent=2)
        except Exception:
            pass

    def _preprocess(self, frame_bgr: np.ndarray) -> np.ndarray:
        gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
        if gray.shape[1] < 450:
            gray = cv2.resize(gray, None, fx=1.4, fy=1.4, interpolation=cv2.INTER_CUBIC)
        gray = cv2.GaussianBlur(gray, (3,3), 0)
        _, bw = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        return bw

    def _tick(self):
        if not self._roi or not self._mss:
            return

        mon = {"left": self._roi.left, "top": self._roi.top, "width": self._roi.width, "height": self._roi.height}
        try:
            frame = np.array(self._mss.grab(mon))[:, :, :3]
        except Exception:
            return

        gray_now = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        changed = True
        if (self._last_gray is not None) and (self._last_gray.shape == gray_now.shape):
            diff = cv2.absdiff(gray_now, self._last_gray)
            changed_pixels = np.count_nonzero(diff > DIFF_PIXEL_THRESH)
            total_pixels = diff.size
            fraction = changed_pixels / max(1, total_pixels)
            changed = fraction >= DIFF_FRACTION_THRESH
        self._last_gray = gray_now

        now_ms = int(time.time() * 1000)
        heartbeat_due = (now_ms - self._last_force_ms) >= FORCE_OCR_INTERVAL_MS
        recent_ocr    = (now_ms - self._last_ocr_ms)   <  OCR_MIN_INTERVAL

        if (not changed) and recent_ocr and (not heartbeat_due):
            return
        if self._ocr_busy:
            return
        if (now_ms - self._last_ocr_ms) < OCR_MIN_INTERVAL and not heartbeat_due:
            return

        bw = self._preprocess(frame)
        self._ocr_busy = True
        self._last_ocr_ms = now_ms
        if heartbeat_due:
            self._last_force_ms = now_ms

        QtCore.QMetaObject.invokeMethod(
            self._worker, "process",
            QtCore.Qt.QueuedConnection,
            QtCore.Q_ARG(np.ndarray, bw)
        )

    @QtCore.pyqtSlot(str)
    def _on_ocr_result(self, text: str):
        self._ocr_busy = False
        if not text:
            return

        self._history.append(text)
        counts = {}
        for t in self._history:
            counts[t] = counts.get(t, 0) + 1
        winner = max(counts, key=counts.get)

        if counts[winner] >= REQUIRED_STABLE and winner != self._last_text:
            self._last_text = winner
            self.unitChanged.emit(winner)
            self._emit_counters(winner)

    def _emit_counters(self, unit_name: str):
        data = self.UNITS_DB.get(unit_name)
        if not data:
            low = unit_name.lower()
            data = self.UNITS_DB.get(self.NAME_LOOKUP.get(low, ""), None)
        if not data:
            self.countersReady.emit([])
            return
        counter_list = []
        for entry in (data.get("countered_by") or []):
            u = entry.get("unit") if isinstance(entry, dict) else str(entry)
            if u:
                counter_list.append(u)
        if counter_list:
            self.countersReady.emit(counter_list[:MAX_COUNTERS_SHOWN])
        else:
            self.countersReady.emit([])
