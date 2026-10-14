import html
import ctypes
import json
import os
import sys
import tempfile
import threading
import time
import webbrowser
from datetime import datetime, timezone

import psutil
import requests
from PyQt5.QtCore import QCoreApplication, QEasingCurve, QPointF, QRectF, QStandardPaths, Qt, QTimer, QVariantAnimation, pyqtSignal, QObject
from PyQt5.QtGui import QBrush, QColor, QFont, QIcon, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap, QTextDocument, QCursor
from PyQt5.QtNetwork import QLocalServer, QLocalSocket
from PyQt5.QtWidgets import (
    QAction,
    QApplication,
    QDialog,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)

if sys.platform == "win32":
    import winreg

from tooltip import CivMatchupPanel
from screen_placement import visible_position
from update_release import select_update


ACCENT = "#A7F3D0"
FG = "#EEF6FF"
MUTED = "#9FB3C8"
PANEL_A = (18, 29, 40, 192)
PANEL_B = (28, 43, 59, 180)
BORDER_RGBA = (255, 255, 255, 52)

CURRENT_VERSION = "2.0.0"
POLL_INTERVAL = 15
MAX_LIVE_AGE_MINUTES = 180
DEFAULT_FONT_SIZE = 9


GITHUB_API_LATEST_RELEASE = (
    "https://api.github.com/repos/BubbleDuckz/"
    "AgeofDuck-ELO-Overlay-for-Age-of-Empires-2-DE/releases/latest"
)

APP_DIR = os.path.dirname(os.path.abspath(__file__))
APP_DATA_DIR = os.path.join(
    QStandardPaths.writableLocation(QStandardPaths.AppDataLocation),
    "AgeOfDuck",
)
os.makedirs(APP_DATA_DIR, exist_ok=True)

PROFILE_FILE = os.path.join(APP_DATA_DIR, "profile_id.txt")
POSITION_FILE = os.path.join(APP_DATA_DIR, "overlay_position.txt")
UPDATE_FLAG_PATH = os.path.join(tempfile.gettempdir(), "AgeOfDuck_updated.flag")
STRATEGIES_FILE = os.path.join(APP_DATA_DIR, "typical_strategies.json")
CIV_DATA_FILE = os.path.join(APP_DATA_DIR, "civ_data.json")
UNITS_DB_FILE = os.path.join(APP_DATA_DIR, "units_db.json")
OVERLAY_SETTINGS_FILE = os.path.join(APP_DATA_DIR, "overlay_settings.json")


def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = APP_DIR
    return os.path.join(base_path, relative_path)


def seed_editable_data_files():
    """Seed shared data once so Age of Duck and Config Duck edit the same files."""
    for filename, destination in (
        ("civ_data.json", CIV_DATA_FILE),
        ("units_db.json", UNITS_DB_FILE),
        ("typical_strategies.json", STRATEGIES_FILE),
    ):
        if os.path.exists(destination):
            continue
        try:
            bundled = resource_path(filename)
            if os.path.exists(bundled):
                with open(bundled, "r", encoding="utf-8") as src:
                    data = src.read()
                with open(destination, "w", encoding="utf-8") as dst:
                    dst.write(data)
        except Exception:
            pass


def load_saved_scale(path=OVERLAY_SETTINGS_FILE):
    try:
        with open(path, "r", encoding="utf-8") as handle:
            value = float(json.load(handle).get("scale_factor", 1.0))
        return min(1.8, max(0.75, value))
    except Exception:
        return 1.0


def load_peak_expanded(path=OVERLAY_SETTINGS_FILE):
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return bool(json.load(handle).get("peak_expanded", True))
    except Exception:
        return True


def save_peak_expanded(expanded, path=OVERLAY_SETTINGS_FILE):
    _save_setting("peak_expanded", bool(expanded), path)


def save_scale(scale_factor, path=OVERLAY_SETTINGS_FILE):
    _save_setting("scale_factor", round(float(scale_factor), 3), path)


def _save_setting(key, value, path):
    try:
        data = {}
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
                if not isinstance(data, dict):
                    data = {}
        data[key] = value
        temp = path + ".tmp"
        with open(temp, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2)
        os.replace(temp, path)
    except Exception:
        pass


def get_app_startup_path():
    return "AgeOfDuck", f'"{os.path.join(APP_DIR, "AgeOfDuck.exe")}"'


def set_app_startup(enable=True):
    if sys.platform != "win32":
        return
    app_name, exe_path = get_app_startup_path()
    key = winreg.OpenKey(
        winreg.HKEY_CURRENT_USER,
        r"Software\Microsoft\Windows\CurrentVersion\Run",
        0,
        winreg.KEY_ALL_ACCESS,
    )
    if enable:
        winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, exe_path)
    else:
        try:
            winreg.DeleteValue(key, app_name)
        except FileNotFoundError:
            pass
    winreg.CloseKey(key)


def is_app_startup_enabled():
    if sys.platform != "win32":
        return False
    app_name, exe_path = get_app_startup_path()
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
        )
        value, _ = winreg.QueryValueEx(key, app_name)
        winreg.CloseKey(key)
        return exe_path in value
    except FileNotFoundError:
        return False


def is_another_instance_running(server_name="AgeOfDuckOverlaySingleton"):
    socket = QLocalSocket()
    socket.connectToServer(server_name)
    if socket.waitForConnected(1000):
        socket.close()
        return True

    server = QLocalServer()
    QLocalServer.removeServer(server_name)
    if not server.listen(server_name):
        return True
    return server


def check_for_update():
    try:
        response = requests.get(GITHUB_API_LATEST_RELEASE, timeout=8)
        response.raise_for_status()
        return select_update(response.json(), CURRENT_VERSION)
    except Exception as exc:
        print("Update check failed:", exc)
    return None, None


def download_and_run_installer(installer_url, tray_icon):
    if not installer_url:
        tray_icon.showMessage("Update Error", "Installer URL not found.", QSystemTrayIcon.Critical)
        return

    try:
        temp_installer = os.path.join(tempfile.gettempdir(), "AgeOfDuckInstaller.exe")
        tray_icon.showMessage("Updating", "Downloading installer...", QSystemTrayIcon.Information)
        with requests.get(installer_url, stream=True, timeout=60) as response:
            response.raise_for_status()
            with open(temp_installer, "wb") as f:
                for chunk in response.iter_content(8192):
                    if chunk:
                        f.write(chunk)

        log_path = os.path.join(tempfile.gettempdir(), "AgeOfDuck_Install.log")
        params = f'/LOG="{log_path}" /CLOSEAPPLICATIONS /RESTARTAPPLICATIONS'
        open(UPDATE_FLAG_PATH, "w").close()
        ctypes.windll.shell32.ShellExecuteW(None, "runas", temp_installer, params, None, 1)
        tray_icon.showMessage(
            "Updating",
            "Installer launched. The app will close and restart automatically.",
            QSystemTrayIcon.Information,
        )
    except Exception as exc:
        tray_icon.showMessage("Update Error", str(exc), QSystemTrayIcon.Critical)


def save_last_profile_id(profile_id):
    try:
        with open(PROFILE_FILE, "w", encoding="utf-8") as f:
            f.write(profile_id.strip())
    except Exception:
        pass


def load_last_profile_id():
    try:
        if os.path.exists(PROFILE_FILE):
            with open(PROFILE_FILE, "r", encoding="utf-8") as f:
                return f.read().strip()
    except Exception:
        pass
    return ""


from recs_provider import RecsWorker as Worker


class ProcessChecker(QObject):
    aoe2_running_changed = pyqtSignal(bool)

    def __init__(self):
        super().__init__()
        self.running = True
        self._last_state = None

    def stop(self):
        self.running = False

    def run(self):
        while self.running:
            aoe_running = False
            try:
                for proc in psutil.process_iter(["name"]):
                    if (proc.info.get("name") or "").lower() == "aoe2de_s.exe":
                        aoe_running = True
                        break
            except Exception:
                pass

            if aoe_running != self._last_state:
                self.aoe2_running_changed.emit(aoe_running)
                self._last_state = aoe_running
            time.sleep(2)


SETTINGS_STYLE = f"""
    QWidget#settingsRoot, QDialog#profileHelp {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #121D28, stop:1 #1C2B3B);
    }}
    QLabel {{ color: {FG}; background: transparent; font-family: 'Segoe UI'; }}
    QLabel#appTitle {{ font-size: 17pt; font-weight: 700; }}
    QLabel#muted {{ color: {MUTED}; }}
    QLabel#cardTitle {{ color: {ACCENT}; font-weight: 700; font-size: 10pt; }}
    QLabel#status {{ color: {MUTED}; }}
    QFrame#card {{
        background: rgba(255, 255, 255, 0.045);
        border: 1px solid rgba(255, 255, 255, 0.10);
        border-radius: 10px;
    }}
    QLineEdit {{
        background: rgba(6, 12, 19, 0.55);
        border: 1px solid rgba(255, 255, 255, 0.16);
        border-radius: 7px;
        padding: 6px 8px;
        color: {FG};
        selection-background-color: rgba(167, 243, 208, 0.40);
    }}
    QLineEdit:focus {{ border: 1px solid rgba(167, 243, 208, 0.75); }}
    QPushButton {{
        background: rgba(255, 255, 255, 0.07);
        border: 1px solid rgba(255, 255, 255, 0.15);
        border-radius: 7px;
        padding: 6px 12px;
        color: {FG};
    }}
    QPushButton:hover {{ background: rgba(255, 255, 255, 0.15); }}
    QPushButton:pressed {{ background: rgba(255, 255, 255, 0.22); }}
    QPushButton#primary {{
        background: rgba(167, 243, 208, 0.22);
        border: 1px solid rgba(167, 243, 208, 0.60);
        color: {ACCENT};
        font-weight: 700;
    }}
    QPushButton#primary:hover {{ background: rgba(167, 243, 208, 0.34); }}
    QSpinBox {{
        background: rgba(6, 12, 19, 0.55);
        border: 1px solid rgba(255, 255, 255, 0.16);
        border-radius: 7px;
        padding: 4px 8px;
        color: {FG};
        min-width: 64px;
    }}
    QSpinBox:focus {{ border: 1px solid rgba(167, 243, 208, 0.75); }}
    QCheckBox {{ color: {FG}; spacing: 8px; font-family: 'Segoe UI'; background: transparent; }}
    QCheckBox::indicator {{
        width: 16px; height: 16px; border-radius: 4px;
        border: 1px solid rgba(255, 255, 255, 0.30);
        background: rgba(6, 12, 19, 0.55);
    }}
    QCheckBox::indicator:hover {{ border-color: rgba(167, 243, 208, 0.7); }}
    QCheckBox::indicator:checked {{
        background: {ACCENT};
        border-color: {ACCENT};
        image: none;
    }}
"""


class SettingsWindow(QWidget):
    profile_set = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("settingsRoot")
        self.setWindowTitle("Age of Duck Settings")
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        self.setFixedWidth(420)
        self.setStyleSheet(SETTINGS_STYLE)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 14)
        layout.setSpacing(12)

        # Header: logo, name and version.
        header = QHBoxLayout()
        header.setSpacing(12)
        logo = QLabel()
        logo_pix = QPixmap(resource_path("duck.png"))
        if not logo_pix.isNull():
            logo.setPixmap(logo_pix.scaled(40, 40, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        logo.setFixedSize(40, 40)
        header.addWidget(logo)
        titles = QVBoxLayout()
        titles.setSpacing(0)
        app_title = QLabel("Age of Duck")
        app_title.setObjectName("appTitle")
        subtitle = QLabel(f"Settings  \u00b7  v{CURRENT_VERSION}")
        subtitle.setObjectName("muted")
        titles.addWidget(app_title)
        titles.addWidget(subtitle)
        header.addLayout(titles, 1)
        layout.addLayout(header)

        # Profile card.
        profile_card, profile_layout = self._card("AoE2 Profile ID")
        explain = QLabel("Your numeric ID lets the overlay recognise you in live matches.")
        explain.setObjectName("muted")
        explain.setWordWrap(True)
        profile_layout.addWidget(explain)

        field_row = QHBoxLayout()
        field_row.setSpacing(8)
        self.edit = QLineEdit()
        self.edit.setPlaceholderText("Numeric profile ID")
        self.edit.setText(load_last_profile_id())
        self.edit.returnPressed.connect(self.set_profile)
        field_row.addWidget(self.edit, 1)
        self.find_button = QPushButton("Find profile ID")
        self.find_button.setToolTip("Look up your profile on aoe2insights.com")
        self.find_button.setCursor(Qt.PointingHandCursor)
        self.find_button.clicked.connect(lambda: show_profile_id_help(self))
        field_row.addWidget(self.find_button)
        profile_layout.addLayout(field_row)

        save_row = QHBoxLayout()
        self.status_label = QLabel("")
        self.status_label.setObjectName("status")
        save_row.addWidget(self.status_label, 1)
        save_button = QPushButton("Save")
        save_button.setObjectName("primary")
        save_button.setCursor(Qt.PointingHandCursor)
        save_button.setMinimumWidth(96)
        save_button.clicked.connect(self.set_profile)
        save_row.addWidget(save_button)
        profile_layout.addLayout(save_row)
        layout.addWidget(profile_card)

        # Voice volume card; the in-game controls module supplies the slider.
        self.volume_card, self.volume_layout = self._card("Voice volume")
        volume_hint = QLabel("Volume of build-order cues and TC / housing reminders. Click the speaker to mute.")
        volume_hint.setObjectName("muted")
        volume_hint.setWordWrap(True)
        self.volume_layout.addWidget(volume_hint)
        layout.addWidget(self.volume_card)

        # HUD recognition card; filled once the recognition controller exists.
        self.hud_card, self.hud_layout = self._card("HUD recognition")
        layout.addWidget(self.hud_card)
        self._hud_controller = None

        # Build orders & audio card; the build-order module fills it.
        self.build_card, self.build_layout = self._card("Build orders")
        self.build_layout.setSpacing(8)
        layout.addWidget(self.build_card)

        footer = QLabel("Live data: aoe2recs.com  \u00b7  Tech tree: aoe2techtree.net")
        footer.setObjectName("muted")
        footer.setAlignment(Qt.AlignCenter)
        layout.addWidget(footer)

    def _card(self, title):
        card = QFrame()
        card.setObjectName("card")
        inner = QVBoxLayout(card)
        inner.setContentsMargins(14, 12, 14, 14)
        inner.setSpacing(8)
        heading = QLabel(title)
        heading.setObjectName("cardTitle")
        inner.addWidget(heading)
        return card, inner

    def add_hud_controls(self, controller, open_setup):
        """Buttons for drawing HUD areas and a manual Town Centre count."""
        self._hud_controller = controller
        intro = QLabel("Skins and interface sizes differ. Draw a box over each HUD item once and the overlay "
                       "reads those areas, whatever your resolution or HUD style.")
        intro.setObjectName("muted")
        intro.setWordWrap(True)
        self.hud_layout.addWidget(intro)
        self.hud_status = QLabel("")
        self.hud_status.setWordWrap(True)
        self.hud_status.setObjectName("status")
        self.hud_layout.addWidget(self.hud_status)
        buttons = QHBoxLayout()
        buttons.setSpacing(8)
        setup = QPushButton("Set up HUD areas…")
        setup.setObjectName("primary")
        setup.setCursor(Qt.PointingHandCursor)
        setup.setToolTip("Needs the game running in a match (windowed or borderless)")
        setup.clicked.connect(open_setup)
        self.hud_reset = QPushButton("Use built-in layout")
        self.hud_reset.setCursor(Qt.PointingHandCursor)
        self.hud_reset.clicked.connect(self._reset_hud)
        buttons.addWidget(setup, 1)
        buttons.addWidget(self.hud_reset)
        self.hud_layout.addLayout(buttons)
        tc_row = QHBoxLayout()
        tc_label = QLabel("Town Centres")
        tc_label.setToolTip("Auto reads your selection panel. Set a number if your HUD cannot be read.")
        self.tc_spin = QSpinBox()
        self.tc_spin.setRange(0, 20)
        self.tc_spin.setSpecialValueText("Auto")
        self.tc_spin.setValue(controller.manual_tcs)
        self.tc_spin.setToolTip(tc_label.toolTip())
        self.tc_spin.valueChanged.connect(controller.set_manual_tcs)
        tc_row.addWidget(tc_label)
        tc_row.addStretch()
        tc_row.addWidget(self.tc_spin)
        self.hud_layout.addLayout(tc_row)
        self.refresh_hud_status()

    def refresh_hud_status(self):
        if self._hud_controller is None:
            return
        regions = self._hud_controller.regions
        self.hud_status.setText(regions.status())
        self.hud_reset.setEnabled(regions.configured)

    def _reset_hud(self):
        self._hud_controller.regions.clear()
        self._hud_controller.reload_regions()
        self.refresh_hud_status()

    def section_layout(self):
        """Layout other modules use to add their controls to the settings window."""
        return self.build_layout

    def set_profile(self):
        profile_id = self.edit.text().strip()
        if not profile_id.isdigit():
            self.status_label.setText("Enter a numeric AoE2 profile ID.")
            self.status_label.setStyleSheet("color:#FCA5A5;")
            QMessageBox.warning(self, "Profile ID", "Enter a numeric AoE2 profile ID.")
            return
        self.status_label.setText("")
        save_last_profile_id(profile_id)
        self.profile_set.emit(profile_id)
        self.hide()

    def show_and_focus(self):
        self.edit.setText(load_last_profile_id())
        self.showNormal()
        self.adjustSize()
        screen = QApplication.screenAt(QCursor.pos()) or QApplication.primaryScreen()
        if screen:
            self.move(screen.availableGeometry().center() - self.rect().center())
        self.raise_()
        self.activateWindow()
        self.edit.setFocus(Qt.OtherFocusReason)
        self.edit.selectAll()
        if sys.platform == "win32":
            # Windows may apply a launcher's hidden startup state to the first show.
            user32 = ctypes.windll.user32
            user32.ShowWindow.argtypes = [ctypes.c_void_p, ctypes.c_int]
            user32.SetForegroundWindow.argtypes = [ctypes.c_void_p]
            user32.ShowWindow(int(self.winId()), 9)
            user32.SetForegroundWindow(int(self.winId()))


CIV_ABBREVIATIONS = {
    "Armenians": "Am", "Aztecs": "Az", "Bengalis": "Bn", "Berbers": "Bb", "Bohemians": "Bo",
    "Britons": "Br", "Bulgarians": "Bg", "Burgundians": "Bd", "Burmese": "Bm", "Byzantines": "By",
    "Celts": "Ce", "Chinese": "Ch", "Cumans": "Cu", "Dravidians": "Dr", "Ethiopians": "Et",
    "Franks": "Fr", "Georgians": "Ge", "Goths": "Go", "Gurjaras": "Gu", "Hindustanis": "Hi",
    "Huns": "Hu", "Incas": "In", "Italians": "It", "Japanese": "Ja", "Jurchens": "Ju",
    "Khitans": "Kt", "Khmer": "Km", "Koreans": "Ko", "Lithuanians": "Li", "Magyars": "Mg",
    "Malay": "Ml", "Malians": "Ma", "Mayans": "My", "Mongols": "Mo", "Persians": "Pe",
    "Poles": "Po", "Portuguese": "Pt", "Romans": "Ro", "Saracens": "Sa", "Shu": "Sh",
    "Sicilians": "Si", "Slavs": "Sl", "Spanish": "Sp", "Tatars": "Ta", "Teutons": "Te",
    "Turks": "Tu", "Vietnamese": "Vi", "Vikings": "Vk", "Wei": "We", "Wu": "Wu",
    "Danes": "Dn", "Saxons": "Sx", "Mapuche": "Mp", "Muisca": "Ms", "Tupi": "Tp", "Varangians": "Va",
}

# Layout metrics (unscaled px). The overlay width follows the Peak column animation.
OVERLAY_WIDTH_EXPANDED = 416
OVERLAY_WIDTH_MIN = 340
PEAK_WIDTH_COLLAPSED = 18
PEAK_ANIMATION_MS = 220


def civ_abbreviation(civ):
    civ = civ or ""
    return CIV_ABBREVIATIONS.get(civ) or civ[:2].capitalize()


class CivBadge(QWidget):
    """Civ emblem with its short name drawn over the artwork."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._pixmap = QPixmap()
        self._abbr = ""
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.set_badge_size(28)

    def set_badge_size(self, size):
        self.setFixedSize(size, size)
        self.update()

    def set_civ(self, civ):
        self._abbr = civ_abbreviation(civ)
        self._pixmap = QPixmap(resource_path(os.path.join("CivIcons", f"{civ}_AoE2.webp")))
        self.update()

    def clear(self):
        self._abbr = ""
        self._pixmap = QPixmap()
        self.update()

    def paintEvent(self, event):
        if not self._abbr:
            return
        painter = QPainter(self)
        painter.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform | QPainter.TextAntialiasing)
        rect = self.rect()
        if self._pixmap.isNull():
            painter.setBrush(QColor(255, 255, 255, 30))
            painter.setPen(QPen(QColor(255, 255, 255, 70), 1))
            painter.drawEllipse(rect.adjusted(1, 1, -1, -1))
        else:
            painter.drawPixmap(rect, self._pixmap)
        font = QFont("Segoe UI")
        font.setBold(True)
        font.setPixelSize(max(9, int(rect.height() * 0.42)))
        painter.setFont(font)
        metrics = painter.fontMetrics()
        x = (rect.width() - metrics.horizontalAdvance(self._abbr)) / 2
        y = (rect.height() + metrics.ascent() - metrics.descent()) / 2
        path = QPainterPath()
        path.addText(x, y, font, self._abbr)
        painter.setPen(QPen(QColor(0, 0, 0, 230), 2.4, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        painter.setBrush(Qt.NoBrush)
        painter.drawPath(path)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#FFFFFF"))
        painter.drawPath(path)


class PeakToggle(QPushButton):
    """Header button for the Peak column: label plus a bold chevron that turns as the column folds."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.progress = 1.0
        self.setFixedHeight(20)

    def set_progress(self, value):
        self.progress = value
        self.update()

    def label_width(self):
        return self.fontMetrics().horizontalAdvance("Peak") + 4 + 12 + 4

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHints(QPainter.Antialiasing | QPainter.TextAntialiasing)
        rect = self.rect().adjusted(0, 1, -1, -1)
        hover = self.underMouse()
        if hover:
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(255, 255, 255, 22))
            painter.drawRoundedRect(rect, 5, 5)
        tone = QColor(238, 246, 255) if hover else QColor(159, 179, 200)
        chevron_x = rect.right() - 8
        if self.progress > 0.55:
            alpha = int(255 * min(1.0, (self.progress - 0.55) / 0.45))
            painter.setPen(QColor(tone.red(), tone.green(), tone.blue(), alpha))
            painter.drawText(rect.adjusted(4, 0, -14, 0), Qt.AlignRight | Qt.AlignVCenter, "Peak")
        painter.save()
        painter.translate(chevron_x if self.progress > 0.55 else rect.center().x() + 0.5, rect.center().y() + 0.5)
        painter.rotate(180 * (1 - self.progress))  # open: points left (fold in); closed: points right (open out)
        painter.setPen(QPen(tone, 1.8, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        painter.setBrush(Qt.NoBrush)
        painter.drawPolyline(QPointF(1.9, -3.4), QPointF(-1.9, 0), QPointF(1.9, 3.4))
        painter.restore()


TEAM_COLORS = ["#5EEAD4", "#FCA5A5", "#FDE68A", "#C4B5FD", "#93C5FD", "#F9A8D4"]


class BotIcon(QWidget):
    """Little robot head marking computer (AI) players."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.set_icon_size(18)

    def set_icon_size(self, size):
        self.setFixedSize(size, size)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        s = min(self.width(), self.height()) / 18.0
        painter.scale(s, s)
        tone = QColor("#9FB3C8")
        painter.setPen(QPen(tone, 1.3, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        painter.setBrush(QColor(159, 179, 200, 45))
        painter.drawRoundedRect(QRectF(2.5, 5.5, 13, 9.5), 3, 3)            # head
        painter.drawLine(QPointF(9, 5.5), QPointF(9, 2.6))                    # antenna
        painter.setPen(Qt.NoPen)
        painter.setBrush(tone)
        painter.drawEllipse(QPointF(9, 2.2), 1.2, 1.2)
        painter.setBrush(QColor("#A7F3D0"))
        painter.drawEllipse(QPointF(6.4, 9.6), 1.5, 1.5)                      # eyes
        painter.drawEllipse(QPointF(11.6, 9.6), 1.5, 1.5)
        painter.setBrush(tone)
        painter.drawRoundedRect(QRectF(5.8, 12.2, 6.4, 1.3), 0.6, 0.6)        # mouth
        painter.drawRect(QRectF(0.8, 8.5, 1.1, 3.2))                          # ear plates
        painter.drawRect(QRectF(16.1, 8.5, 1.1, 3.2))


class TeamDivider(QWidget):
    """Slim 'VS' rule drawn between opposing teams."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.set_divider_height(12)

    def set_divider_height(self, height):
        self.setFixedHeight(height)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHints(QPainter.Antialiasing | QPainter.TextAntialiasing)
        rect = self.rect()
        mid = rect.height() / 2.0
        font = QFont("Segoe UI")
        font.setBold(True)
        font.setPixelSize(max(8, rect.height() - 4))
        font.setLetterSpacing(QFont.AbsoluteSpacing, 1.2)
        painter.setFont(font)
        text_w = painter.fontMetrics().horizontalAdvance("VS")
        gap = 8
        left_end = rect.width() / 2.0 - text_w / 2.0 - gap
        right_start = rect.width() / 2.0 + text_w / 2.0 + gap
        margin = 10
        for x0, x1, fade_from_edge in ((margin, left_end, True), (right_start, rect.width() - margin, False)):
            grad = QLinearGradient(x0, 0, x1, 0)
            edge, inner = (0, 90) if fade_from_edge else (90, 0)
            grad.setColorAt(0, QColor(255, 255, 255, edge))
            grad.setColorAt(1, QColor(255, 255, 255, inner))
            painter.setPen(QPen(QBrush(grad), 1))
            painter.drawLine(int(x0), int(mid), int(x1), int(mid))
        painter.setPen(QColor(159, 179, 200, 210))
        painter.drawText(rect, Qt.AlignCenter, "VS")


class PlayerRow(QFrame):
    clicked = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.player = None
        self.setObjectName("playerRow")
        self.setCursor(Qt.PointingHandCursor)
        self.setSizePolicy(self.sizePolicy().horizontalPolicy(), self.sizePolicy().Minimum)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(7, 4, 7, 4)
        layout.setSpacing(6)

        self.team_color = None
        self.civ_badge = CivBadge()
        self.bot_icon = BotIcon()
        self.bot_icon.hide()
        self.name_label = QLabel("")
        self.name_label.setObjectName("playerName")
        self.name_label.setMinimumWidth(0)
        self.name_label.setSizePolicy(self.name_label.sizePolicy().Ignored, self.name_label.sizePolicy().Preferred)
        self.rating_label = QLabel("")
        self.rating_label.setObjectName("playerRating")
        self.rating_label.setMinimumWidth(36)
        self.peak_label = QLabel("")
        self.peak_label.setObjectName("playerPeak")
        self.peak_label.setMinimumWidth(0)
        self.peak_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.peak_label.setTextFormat(Qt.RichText)

        layout.addWidget(self.civ_badge)
        layout.addWidget(self.bot_icon)
        layout.addWidget(self.name_label, 1)
        layout.addWidget(self.rating_label)
        layout.addWidget(self.peak_label)

    def set_team_color(self, color):
        """Thin coloured bar on the row's left edge: players with the same colour are teammates."""
        if color != self.team_color:
            self.team_color = color
            self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.team_color:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(self.team_color))
            painter.drawRoundedRect(QRectF(1.5, 5, 3, max(0, self.height() - 10)), 1.5, 1.5)

    def set_peak_progress(self, width, progress):
        """Column width in px and 0..1 expansion; the value fades as the column narrows."""
        self.peak_label.setFixedWidth(width)
        alpha = max(0.0, min(1.0, (progress - 0.35) / 0.65))
        self.peak_label.setStyleSheet(f"color: rgba(238, 246, 255, {alpha:.2f});")

    def set_player(self, player):
        self.player = player
        color = player.get("color") or FG
        civ = player.get("civ", "")
        is_ai = bool(player.get("is_ai"))
        name = "AI" if is_ai else (player.get("name") or "Unknown")
        self.bot_icon.setVisible(is_ai)
        self.name_label.setText(name)
        self.name_label.setToolTip("Computer player" if is_ai else name)
        self.name_label.setStyleSheet(f"color:{color}; font-weight:700;")
        self.civ_badge.set_civ(civ)
        self.rating_label.setText("" if player.get("rating") is None else str(player.get("rating")))
        peak=player.get('peak');mode=player.get('peak_mode')
        self.peak_label.setText('—' if peak is None else html.escape(str(peak))+(f'&nbsp;<b>({html.escape(mode).replace(chr(32), chr(160))})</b>' if mode else ''))
        self.peak_label.setToolTip('Highest peak across 1v1, Teams, EW 1v1 and EW Teams')
        self.setToolTip(f"{player.get('name', 'Unknown')} \u00b7 {civ}\nClick for units and counters")
        self.show()

    def clear(self):
        self.player = None
        self.civ_badge.clear()
        self.hide()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.player:
            self.clicked.emit(self.player)
        super().mousePressEvent(event)


class Overlay(QWidget):
    scale_changed = pyqtSignal(float)
    game_running_changed = pyqtSignal(bool)
    settings_requested = pyqtSignal()

    def __init__(self, tray_icon):
        super().__init__()
        self.tray_icon = tray_icon
        self.locked = False
        self.dragging = False
        self.last_mouse_pos = None
        self.scale_factor = load_saved_scale()
        self._aoe2_running = False
        self.is_waiting = True
        self.current_players = []
        self.player_civ = None
        self.test_mode_active = False
        self._peak_expanded = load_peak_expanded()
        self._peak_progress = 1.0 if self._peak_expanded else 0.0
        self._peak_full_width = 40

        self.setWindowTitle("Age of Duck")
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool | Qt.WindowDoesNotAcceptFocus)
        self.setAttribute(Qt.WA_TranslucentBackground)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(40)
        shadow.setYOffset(10)
        shadow.setColor(QColor(0, 0, 0, 135))
        self.setGraphicsEffect(shadow)

        self._build_ui()
        self.restore_last_position()
        self.placement_timer=QTimer(self)
        self.placement_timer.timeout.connect(self.ensure_visible_position)
        self.placement_timer.start(2000)
        self._waiting_dot_index = 0
        self.waiting_timer = QTimer(self)
        self.waiting_timer.setInterval(500)
        self.waiting_timer.timeout.connect(self._update_waiting_text)

        self.worker = Worker()
        self.worker.in_game_signal.connect(self.on_game_state_changed)
        self.worker.data_updated.connect(self.update_overlay)
        self.worker.provider_status.connect(self.footer.setToolTip)
        self.worker.not_in_game.connect(self.show_waiting)
        self.worker.profile_error.connect(self.profile_error)
        self.game_running_changed.connect(self.worker.set_game_running_state)
        self.worker_thread = threading.Thread(target=self.worker.poll_loop, daemon=True)
        self.worker_thread.start()

        self.process_checker = ProcessChecker()
        self.process_checker.aoe2_running_changed.connect(self.on_aoe2_running_changed)
        self.process_thread = threading.Thread(target=self.process_checker.run, daemon=True)
        self.process_thread.start()

    def nativeEvent(self,event_type,message):
        # Accept clicks without asking Windows to activate the gameplay overlay.
        from ctypes import wintypes
        msg=ctypes.cast(int(message),ctypes.POINTER(wintypes.MSG)).contents
        if msg.message==0x0021:return True,3  # WM_MOUSEACTIVATE / MA_NOACTIVATE
        return super().nativeEvent(event_type,message)

    def _build_ui(self):
        self.setStyleSheet(f"""
            QLabel {{
                color: {FG};
                background: transparent;
                font-family: 'Segoe UI';
            }}
            QLabel#muted {{
                color: {MUTED};
            }}
            QLabel#mode {{
                font-weight: 700;
                color: {FG};
            }}
            QLabel#map {{
                color: {ACCENT};
            }}
            QFrame#playerRow {{
                background: rgba(255, 255, 255, 0.045);
                border: 1px solid rgba(255, 255, 255, 0.10);
                border-radius: 8px;
            }}
            QFrame#playerRow:hover {{
                background: rgba(255, 255, 255, 0.12);
            }}
            QLabel#playerRating, QLabel#playerPeak {{
                color: {FG};
            }}
            QPushButton#peakToggle {{
                background: transparent;
                border: none;
                border-radius: 4px;
                color: {MUTED};
                padding: 0px;
                text-align: right;
            }}
            QPushButton#peakToggle:hover {{
                background: rgba(255, 255, 255, 0.10);
                color: {FG};
            }}
            QPushButton {{
                background: rgba(255, 255, 255, 0.065);
                border: 1px solid rgba(255, 255, 255, 0.14);
                border-radius: 7px;
                color: {FG};
                padding: 2px 6px;
            }}
            QPushButton:hover {{
                background: rgba(255, 255, 255, 0.14);
            }}
        """)

        self.outer = QVBoxLayout(self)
        self.outer.setContentsMargins(12, 8, 12, 8)
        self.outer.setSpacing(6)

        self.drag_bar = QFrame()
        self.drag_bar.setFixedSize(100, 4)
        self.drag_bar.setStyleSheet("background: rgba(255,255,255,0.45); border-radius: 2px;")
        drag_layout = QHBoxLayout()
        drag_layout.addStretch()
        drag_layout.addWidget(self.drag_bar)
        drag_layout.addStretch()
        self.outer.addLayout(drag_layout)
        self.drag_bar.mousePressEvent = self.drag_bar_mouse_press
        self.drag_bar.mouseMoveEvent = self.drag_bar_mouse_move
        self.drag_bar.mouseReleaseEvent = self.drag_bar_mouse_release

        top = QHBoxLayout()
        self.mode_label = QLabel("Waiting for Age of Empires II")
        self.mode_label.setObjectName("mode")
        self.map_label = QLabel("")
        self.map_label.setObjectName("map")
        self.mode_label.setSizePolicy(self.mode_label.sizePolicy().Ignored, self.mode_label.sizePolicy().Preferred)
        self.mode_label.setMinimumWidth(0)
        self.map_label.setSizePolicy(self.map_label.sizePolicy().Ignored, self.map_label.sizePolicy().Preferred)
        self.map_label.setMinimumWidth(0)
        self.map_label.hide()
        top.addWidget(self.mode_label, 1)

        self.minus_button = QPushButton("-")
        self.plus_button = QPushButton("+")
        self.lock_button = QPushButton("Lock")
        self.minus_button.clicked.connect(self.decrease_scale)
        self.plus_button.clicked.connect(self.increase_scale)
        self.lock_button.clicked.connect(self.toggle_lock)
        top.addWidget(self.minus_button)
        top.addWidget(self.plus_button)
        top.addWidget(self.lock_button)
        self.settings_button = QPushButton("Settings")
        self.settings_button.clicked.connect(self.settings_requested.emit)
        top.addWidget(self.settings_button)
        self.outer.addLayout(top)
        self.outer.addWidget(self.map_label)
        self.outer.setSpacing(4)

        headers = QHBoxLayout()
        headers.setContentsMargins(7, 0, 7, 0)
        headers.setSpacing(6)
        self.header_badge_spacer = QWidget()
        headers.addWidget(self.header_badge_spacer)
        player_header = QLabel("Player")
        player_header.setObjectName("muted")
        player_header.setMinimumWidth(0)
        headers.addWidget(player_header, 1)
        self.elo_header = QLabel("ELO")
        self.elo_header.setObjectName("muted")
        headers.addWidget(self.elo_header)
        self.peak_toggle = PeakToggle()
        self.peak_toggle.setObjectName("peakToggle")
        self.peak_toggle.setCursor(Qt.PointingHandCursor)
        self.peak_toggle.setFocusPolicy(Qt.NoFocus)
        self.peak_toggle.clicked.connect(self.toggle_peak)
        headers.addWidget(self.peak_toggle)
        self.column_headers = [player_header, self.elo_header, self.peak_toggle]
        self.peak_anim = QVariantAnimation(self)
        self.peak_anim.setDuration(PEAK_ANIMATION_MS)
        self.peak_anim.setEasingCurve(QEasingCurve.InOutCubic)
        self.peak_anim.valueChanged.connect(self._set_peak_progress)
        self.outer.addLayout(headers)

        self.rows_layout = QVBoxLayout()
        self.rows_layout.setSpacing(4)
        self.player_rows = []
        self.team_dividers = []
        for _ in range(8):
            divider = TeamDivider()
            divider.hide()
            self.team_dividers.append(divider)
            self.rows_layout.addWidget(divider)
            row = PlayerRow()
            row.clicked.connect(self.select_player)
            row.hide()
            self.player_rows.append(row)
            self.rows_layout.addWidget(row)
        self.outer.addLayout(self.rows_layout)

        self.matchup_panel = CivMatchupPanel(
            civ_data_path=CIV_DATA_FILE,
            units_db_path=UNITS_DB_FILE,
            strategies_path=STRATEGIES_FILE,
            assets_root=resource_path(""),
            parent=self,
        )
        self.outer.addWidget(self.matchup_panel)

        self.footer = QLabel("Age of Duck | Live data by aoe2recs.com")
        self.footer.setObjectName("muted")
        self.footer.setAlignment(Qt.AlignCenter)
        self.outer.addWidget(self.footer)

        self.apply_scale()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.rect().adjusted(1, 1, -1, -1)
        gradient = QLinearGradient(rect.left(), rect.top(), rect.right(), rect.bottom())
        gradient.setColorAt(0, QColor(*PANEL_A))
        gradient.setColorAt(1, QColor(*PANEL_B))
        painter.setBrush(QBrush(gradient))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(rect, 14, 14)
        painter.setPen(QPen(QColor(*BORDER_RGBA), 1))
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(rect, 14, 14)

    def moveEvent(self, event):
        super().moveEvent(event)
        try:
            with open(POSITION_FILE, "w", encoding="utf-8") as f:
                f.write(f"{self.x()},{self.y()}")
        except Exception:
            pass

    def closeEvent(self, event):
        self.worker.stop()
        self.process_checker.stop()
        event.accept()

    def ensure_visible_position(self):
        if self.dragging:return
        areas=[screen.availableGeometry() for screen in QApplication.screens()]
        point=visible_position(self.frameGeometry(),areas)
        if point!=self.pos():self.move(point)

    def restore_last_position(self):
        try:
            with open(POSITION_FILE, "r", encoding="utf-8") as f:
                x_raw, y_raw = f.read().strip().split(",", 1)
            self.move(int(x_raw), int(y_raw))
        except Exception:
            self.move(40, 80)
        self.ensure_visible_position()

    def drag_bar_mouse_press(self, event):
        if not self.locked and event.button() == Qt.LeftButton:
            self.dragging = True
            self.last_mouse_pos = event.globalPos()

    def drag_bar_mouse_move(self, event):
        if self.dragging and not self.locked:
            delta = event.globalPos() - self.last_mouse_pos
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self.last_mouse_pos = event.globalPos()

    def drag_bar_mouse_release(self, event):
        self.dragging = False

    def toggle_lock(self):
        self.locked = not self.locked
        self.lock_button.setText("Locked" if self.locked else "Lock")
        self.minus_button.setEnabled(not self.locked)
        self.plus_button.setEnabled(not self.locked)

    def increase_scale(self):
        self.scale_factor = min(1.8, round(self.scale_factor * 1.1, 3))
        self.apply_scale()
        save_scale(self.scale_factor)

    def decrease_scale(self):
        self.scale_factor = max(0.75, round(self.scale_factor / 1.1, 3))
        self.apply_scale()
        save_scale(self.scale_factor)

    def apply_scale(self):
        base = max(8, int(round(DEFAULT_FONT_SIZE * self.scale_factor)))
        self.mode_label.setFont(QFont("Segoe UI", base + 2, QFont.DemiBold))
        self.map_label.setFont(QFont("Segoe UI", base + 2))
        self.footer.setFont(QFont("Segoe UI", max(7, base - 1)))
        badge_size = max(22, int(round(28 * self.scale_factor)))
        self.header_badge_spacer.setFixedSize(badge_size, 1)
        self.peak_toggle.setFont(QFont("Segoe UI", base))
        self.elo_header.setFont(QFont("Segoe UI", base))
        self.column_headers[0].setFont(QFont("Segoe UI", base))
        for divider in self.team_dividers:
            divider.set_divider_height(max(12, int(round(12 * self.scale_factor))))
        for row in self.player_rows:
            row.civ_badge.set_badge_size(badge_size)
            row.bot_icon.set_icon_size(max(14, round(badge_size * 0.62)))
            for label in (row.name_label, row.rating_label, row.peak_label):
                label.setFont(QFont("Segoe UI", base))
        self.sync_player_columns()
        self.matchup_panel.set_scale(self.scale_factor, base)
        self.scale_changed.emit(self.scale_factor)
        self.adjustSize()

    def _set_map_text(self, text):
        # The map name is deliberately not shown; the label stays only for compatibility.
        self.map_label.setText(text or "")
        self.map_label.hide()

    def toggle_peak(self):
        self._peak_expanded = not self._peak_expanded
        save_peak_expanded(self._peak_expanded)
        self.peak_anim.stop()
        self.peak_anim.setStartValue(self._peak_progress)
        self.peak_anim.setEndValue(1.0 if self._peak_expanded else 0.0)
        self.peak_anim.start()

    def _set_peak_progress(self, progress):
        """Drive the Peak column and overlay width from 0 (collapsed) to 1 (expanded)."""
        progress = float(progress)
        self._peak_progress = progress
        full = max(self._peak_full_width, PEAK_WIDTH_COLLAPSED + 20)
        col = int(round(PEAK_WIDTH_COLLAPSED + (full - PEAK_WIDTH_COLLAPSED) * progress))
        self.peak_toggle.setFixedWidth(col)
        self.peak_toggle.set_progress(progress)
        self.peak_toggle.setToolTip("Hide peak ELO" if self._peak_expanded else "Show peak ELO")
        for row in self.player_rows:
            row.set_peak_progress(col, progress)
        saved = (full - PEAK_WIDTH_COLLAPSED) * (1.0 - progress)
        width = max(OVERLAY_WIDTH_MIN, OVERLAY_WIDTH_EXPANDED - saved)
        self.setFixedWidth(int(round(width * self.scale_factor)))

    def sync_player_columns(self):
        # Reserve only the space actually needed by data; names receive the remainder.
        visible = [row for row in self.player_rows if row.player]
        rows = visible or self.player_rows[:1]
        widths = {}
        for attr, header in (("rating_label", self.elo_header), ("peak_label", self.peak_toggle)):
            sizes = [header.label_width() if attr == "peak_label" else header.fontMetrics().horizontalAdvance("ELO") + 6]
            for row in rows:
                label = getattr(row, attr)
                doc = QTextDocument()
                doc.setDocumentMargin(0)
                doc.setDefaultFont(label.font())
                doc.setHtml(label.text() or "0000")
                sizes.append(int(doc.idealWidth()) + 3)
            widths[attr] = max(sizes)
        for row in self.player_rows:
            row.rating_label.setFixedWidth(widths["rating_label"])
        self.elo_header.setFixedWidth(widths["rating_label"])
        self._peak_full_width = widths["peak_label"]
        self._set_peak_progress(self._peak_progress)

    def on_game_state_changed(self, in_game):
        if not in_game:
            if self.test_mode_active:
                return
            self.matchup_panel.clear_selection()

    def on_aoe2_running_changed(self, running):
        if self.test_mode_active and not running:
            return
        self._aoe2_running = running
        self.game_running_changed.emit(running)
        if running:
            self.show()
            self.show_waiting()
        else:
            self.waiting_timer.stop()
            self.hide()

    def update_overlay(self, match, players, game_mode, map_name):
        self.is_waiting = False
        self.waiting_timer.stop()
        self.test_mode_active = False
        teams = {}
        for player in players:
            teams.setdefault(player.get("team"), []).append(player)
        # Free-for-all: everyone is on their own team, so team dividers would only add noise.
        ffa = bool((match or {}).get("ffa")) or (len(players) > 2 and len(teams) == len(players))
        title = game_mode or "Live Match"
        self.mode_label.setText(title + (" \u00b7 FFA" if ffa and "FFA" not in title else ""))
        self._set_map_text(map_name)
        flat = []
        for team_id in sorted(teams.keys(), key=lambda t: (t is None, t)):
            members = teams[team_id]
            flat.extend(members if ffa else sorted(members, key=lambda item: (item.get("name") or "").lower()))
        team_colors = {}
        for team_id in sorted(teams.keys(), key=lambda t: (t is None, t)):
            team_colors[team_id] = TEAM_COLORS[len(team_colors) % len(TEAM_COLORS)]
        self.current_players = flat
        self.player_civ = self._find_player_civ(flat)

        for index, row in enumerate(self.player_rows):
            if index < len(flat):
                row.set_player(flat[index])
            else:
                row.clear()
            # A divider sits above the first player of each new team; teammates share a coloured edge bar.
            self.team_dividers[index].setVisible(
                not ffa and 0 < index < len(flat) and flat[index].get("team") != flat[index - 1].get("team")
            )
            row.set_team_color(None if ffa or index >= len(flat) or len(teams) < 2 else team_colors[flat[index].get("team")])

        self.sync_player_columns()
        if self._aoe2_running:
            self.show()
        self.adjustSize()

    def select_player(self, player):
        civ = player.get("civ")
        if not civ:
            return
        self.matchup_panel.select_civ(civ, player.get("name"), player_civ=self.player_civ)
        self.adjustSize()

    def show_waiting(self):
        if self.test_mode_active:
            return
        self.is_waiting = True
        if not self.waiting_timer.isActive():
            self._waiting_dot_index = 0
            self._update_waiting_text()
            self.waiting_timer.start()
        self._set_map_text("")
        self.current_players = []
        self.player_civ = None
        for row in self.player_rows:
            row.clear()
        for divider in self.team_dividers:
            divider.hide()
        self.matchup_panel.clear_selection()
        self.sync_player_columns()
        if self._aoe2_running:
            self.show()
        self.adjustSize()

    def _update_waiting_text(self):
        if not self.is_waiting or self.test_mode_active:
            self.waiting_timer.stop()
            return
        dots = "." * (self._waiting_dot_index + 1)
        self.mode_label.setText(f"Waiting for live match{dots}")
        self._waiting_dot_index = (self._waiting_dot_index + 1) % 3

    def profile_error(self, message):
        self.tray_icon.showMessage("Profile Error", message, QSystemTrayIcon.Warning)

    def _find_player_civ(self, players):
        for player in players:
            if player.get("is_self"):
                return player.get("civ")

        profile_id = str(getattr(self.worker, "profile_id", "") or "")
        if profile_id:
            for player in players:
                if str(player.get("profile_id")) == profile_id:
                    return player.get("civ")

        return players[0].get("civ") if players else None


def show_profile_id_help(parent=None):
    dlg = QDialog(parent)
    dlg.setObjectName("profileHelp")
    dlg.setWindowTitle("Find your profile ID")
    dlg.setWindowFlags(dlg.windowFlags() | Qt.WindowStaysOnTopHint)
    dlg.setStyleSheet(SETTINGS_STYLE)
    dlg.setFixedWidth(400)
    layout = QVBoxLayout(dlg)
    layout.setContentsMargins(18, 16, 18, 16)
    layout.setSpacing(10)
    title = QLabel("Find your profile ID")
    title.setObjectName("appTitle")
    title.setStyleSheet("font-size:14pt;")
    layout.addWidget(title)
    steps = QLabel(
        "<ol style='margin-left:-18px'>"
        "<li>Open <b>aoe2insights.com</b> with the button below.</li>"
        "<li>Search for your in-game username.</li>"
        "<li>Open your profile.</li>"
        "<li>Copy the number from the address, for example "
        "<span style='color:%s'>aoe2insights.com/user/<b>199325</b></span>.</li>"
        "</ol>" % ACCENT
    )
    steps.setTextFormat(Qt.RichText)
    steps.setWordWrap(True)
    layout.addWidget(steps)
    buttons = QHBoxLayout()
    buttons.setSpacing(8)
    close_button = QPushButton("Close")
    close_button.clicked.connect(dlg.accept)
    open_button = QPushButton("Open aoe2insights.com")
    open_button.setObjectName("primary")
    open_button.setCursor(Qt.PointingHandCursor)
    open_button.clicked.connect(lambda: webbrowser.open("https://www.aoe2insights.com"))
    buttons.addStretch()
    buttons.addWidget(close_button)
    buttons.addWidget(open_button)
    layout.addLayout(buttons)
    dlg.exec_()


def main():
    QCoreApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    app = QApplication(sys.argv)
    singleton_check = is_another_instance_running()
    if singleton_check is True:
        sys.exit(0)

    global singleton_server
    singleton_server = singleton_check

    app.setApplicationName("Age of Duck")
    app.setQuitOnLastWindowClosed(False)
    seed_editable_data_files()

    tray_icon = QSystemTrayIcon(QIcon(resource_path("duck.png")), parent=app)
    tray_icon.setToolTip("Age of Duck")

    if os.path.exists(UPDATE_FLAG_PATH):
        tray_icon.showMessage("Update complete", "Age of Duck was updated successfully.", QSystemTrayIcon.Information)
        try:
            os.remove(UPDATE_FLAG_PATH)
        except Exception:
            pass

    settings = SettingsWindow()
    overlay = Overlay(tray_icon)

    def open_settings():
        # Let the tray menu release its focus grab before activating the editor.
        QTimer.singleShot(0, settings.show_and_focus)

    def handle_relaunch():
        while singleton_server.hasPendingConnections():
            connection = singleton_server.nextPendingConnection()
            connection.close()
            connection.deleteLater()
        open_settings()

    singleton_server.newConnection.connect(handle_relaunch)
    if singleton_server.hasPendingConnections():
        handle_relaunch()
    overlay.settings_requested.connect(open_settings)

    def apply_profile(profile_id):
        overlay.worker.set_profile(profile_id)

    def best_parent():
        return settings if settings.isVisible() else overlay

    def toggle_startup():
        set_app_startup(action_autostart.isChecked())

    def on_check_updates():
        latest, installer_url = check_for_update()
        if latest:
            answer = QMessageBox.question(
                best_parent(),
                "Update Available",
                f"Version {latest} is available. Install now?",
            )
            if answer == QMessageBox.Yes:
                download_and_run_installer(installer_url, tray_icon)
        else:
            QMessageBox.information(best_parent(), "No Update", "You have the latest version.")

    action_settings = QAction("Settings", app)
    action_find_id = QAction("Find my Profile ID", app)
    action_autostart = QAction("Start with Windows", app)
    action_autostart.setCheckable(True)
    action_autostart.setChecked(is_app_startup_enabled())
    action_check_updates = QAction("Check for Updates", app)
    action_discord = QAction("Join Discord", app)
    action_donate = QAction("Donate", app)
    action_version = QAction(f"Version: {CURRENT_VERSION}", app)
    action_version.setEnabled(False)
    action_quit = QAction("Quit", app)

    action_settings.triggered.connect(open_settings)
    action_find_id.triggered.connect(show_profile_id_help)
    action_autostart.toggled.connect(toggle_startup)
    action_check_updates.triggered.connect(on_check_updates)
    action_discord.triggered.connect(lambda: webbrowser.open("https://discord.gg/hWsa7KS9nw"))
    action_donate.triggered.connect(lambda: webbrowser.open("https://paypal.me/mywebdeveloper"))
    action_quit.triggered.connect(app.quit)

    menu = QMenu()
    menu.addAction(action_settings)
    menu.addAction(action_find_id)
    menu.addSeparator()
    menu.addSeparator()
    menu.addAction(action_autostart)
    menu.addAction(action_check_updates)
    menu.addAction(action_discord)
    menu.addAction(action_donate)
    menu.addSeparator()
    from tc_reminder.integration import TCController
    tc_controller = TCController(app, menu, os.path.join(APP_DATA_DIR, "tc_reminder_settings.json"), overlay)
    from build_orders import BuildOrders
    build_orders = BuildOrders(app, overlay, tc_controller, APP_DATA_DIR, resource_path(""))
    build_orders.settings_controls(settings.section_layout())
    build_orders.tray_controls(menu)
    from companion_controls import CompanionControls
    overlay.companion_controls = CompanionControls(overlay, build_orders, tc_controller)
    overlay.outer.insertWidget(overlay.outer.indexOf(overlay.footer), overlay.companion_controls)
    settings.volume_layout.addWidget(overlay.companion_controls.volume_row)

    def open_hud_setup():
        from tc_reminder import native
        from hud_calibration import HudCalibrator
        game = native.find_game_window()
        if game is None:
            QMessageBox.information(
                best_parent(), "Set up HUD areas",
                "Start Age of Empires II, load into a match and try again.\n\n"
                "The game must be visible: run it in Windowed or Borderless mode.")
            return
        existing = getattr(overlay, "hud_calibrator", None)
        if existing is not None and existing.isVisible():
            existing.raise_()
            return
        calibrator = HudCalibrator(game, tc_controller.regions, tc_controller.detector, tc_controller.villager_reader)
        calibrator.saved.connect(lambda: (tc_controller.reload_regions(), settings.refresh_hud_status()))
        overlay.hud_calibrator = calibrator
        calibrator.present()

    settings.add_hud_controls(tc_controller, open_hud_setup)
    menu.addAction("Set up HUD areas…", lambda: QTimer.singleShot(0, open_hud_setup))
    overlay.adjustSize()
    menu.addSeparator()
    menu.addAction(action_version)
    menu.addAction(action_quit)
    tray_icon.setContextMenu(menu)
    tray_icon.show()

    settings.profile_set.connect(apply_profile)
    tray_icon.activated.connect(
        lambda reason: open_settings() if reason == QSystemTrayIcon.DoubleClick else None
    )

    initial_profile = load_last_profile_id()
    if initial_profile:
        overlay.worker.set_profile(initial_profile)
    else:
        settings.show_and_focus()

    QTimer.singleShot(3000, lambda: None)
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()

