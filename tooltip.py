import json
import os
import re

from PyQt5.QtCore import QEasingCurve, QSize, Qt, QTimer, QVariantAnimation, pyqtSignal
from PyQt5.QtGui import QFont, QIcon, QPixmap
from PyQt5.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStyle,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


FG = "#EEF6FF"
MUTED = "#9FB3C8"
ACCENT = "#A7F3D0"
WARNING = "#FCA5A5"
COUNTER_ACCENT = "#FDA4AF"
DEFAULT_HINT = "Click a player or civilization to inspect units, counters, and typical strategies."

COUNTER_UNIT_LINES = {
    "Militia line": ["Militia", "Man-at-Arms", "Long Swordsman", "Two-Handed Swordsman", "Champion"],
    "Spearman line": ["Spearman", "Pikeman", "Halberdier"],
    "Archer line": ["Archer", "Crossbowman", "Arbalester"],
    "Skirmisher line": ["Skirmisher", "Elite Skirmisher", "Imperial Skirmisher"],
    "Cavalry Archer line": ["Cavalry Archer", "Heavy Cavalry Archer"],
    "Scout Cavalry line": ["Scout Cavalry", "Light Cavalry", "Hussar", "Winged Hussar"],
    "Knight line": ["Knight", "Cavalier", "Paladin", "Savar"],
    "Camel line": ["Camel Scout", "Camel Rider", "Heavy Camel Rider", "Imperial Camel Rider"],
    "Steppe Lancer line": ["Steppe Lancer", "Elite Steppe Lancer"],
    "Battle Elephant line": ["Battle Elephant", "Elite Battle Elephant"],
    "Ram line": ["Battering Ram", "Capped Ram", "Siege Ram"],
    "Mangonel line": ["Mangonel", "Onager", "Siege Onager"],
    "Scorpion line": ["Scorpion", "Heavy Scorpion"],
    "Galley line": ["Galley", "War Galley", "Galleon"],
    "Fire Ship line": ["Fire Galley", "Fire Ship", "Fast Fire Ship"],
    "Demolition Ship line": ["Demolition Raft", "Demolition Ship", "Heavy Demo Ship", "Heavy Demolition Ship"],
}

UNIT_AGES = {
    "Militia": ("Dark Age", "dark"), "Man-at-Arms": ("Feudal", "feudal"),
    "Long Swordsman": ("Castle", "castle"), "Two-Handed Swordsman": ("Imperial", "imperial"),
    "Champion": ("Imperial", "imperial"), "Spearman": ("Dark Age, Feudal", "feudal"),
    "Pikeman": ("Castle", "castle"), "Halberdier": ("Imperial", "imperial"),
    "Archer": ("Feudal", "feudal"), "Crossbowman": ("Castle", "castle"),
    "Arbalester": ("Imperial", "imperial"), "Skirmisher": ("Feudal", "feudal"),
    "Elite Skirmisher": ("Castle", "castle"), "Imperial Skirmisher": ("Imperial", "imperial"),
    "Cavalry Archer": ("Castle", "castle"), "Heavy Cavalry Archer": ("Imperial", "imperial"),
    "Scout Cavalry": ("Feudal", "feudal"), "Light Cavalry": ("Castle", "castle"),
    "Hussar": ("Imperial", "imperial"), "Winged Hussar": ("Imperial", "imperial"),
    "Knight": ("Castle", "castle"), "Cavalier": ("Imperial", "imperial"),
    "Paladin": ("Imperial", "imperial"), "Savar": ("Imperial", "imperial"),
    "Camel Scout": ("Feudal", "feudal"), "Camel Rider": ("Castle", "castle"),
    "Heavy Camel Rider": ("Imperial", "imperial"), "Imperial Camel Rider": ("Imperial", "imperial"),
    "Steppe Lancer": ("Castle", "castle"), "Elite Steppe Lancer": ("Imperial", "imperial"),
    "Battle Elephant": ("Castle", "castle"), "Elite Battle Elephant": ("Imperial", "imperial"),
    "Battering Ram": ("Castle", "castle"), "Capped Ram": ("Imperial", "imperial"),
    "Siege Ram": ("Imperial", "imperial"), "Mangonel": ("Castle", "castle"),
    "Onager": ("Imperial", "imperial"), "Siege Onager": ("Imperial", "imperial"),
    "Scorpion": ("Castle", "castle"), "Heavy Scorpion": ("Imperial", "imperial"),
    "Galley": ("Feudal", "feudal"), "War Galley": ("Castle", "castle"),
    "Galleon": ("Imperial", "imperial"), "Fire Galley": ("Feudal", "feudal"),
    "Fire Ship": ("Castle", "castle"), "Fast Fire Ship": ("Imperial", "imperial"),
    "Demolition Raft": ("Feudal", "feudal"), "Demolition Ship": ("Castle", "castle"),
    "Heavy Demo Ship": ("Imperial", "imperial"), "Heavy Demolition Ship": ("Imperial", "imperial"),
}

# Economy buildings: their units (Villager, Trade Cart) are not combat units.
HIDDEN_UNIT_CATEGORIES = {"Town Center", "Market"}

AGE_ICON_FILES = {
    "dark": "DarkageDE.png", "feudal": "FeudalageDE.png",
    "castle": "CastleAgeIconDE.png", "imperial": "ImperialageDE.png",
}


def set_chevron(button, expanded):
    icon = QStyle.SP_ArrowDown if expanded else QStyle.SP_ArrowRight
    button.setIcon(button.style().standardIcon(icon))
    button.setIconSize(QSize(12, 12))


def load_json(path, fallback):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return fallback


def write_json_if_missing(path, data):
    if os.path.exists(path):
        return
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception:
        pass


class UnitCard(QFrame):
    def __init__(self, unit_name, subtitle="", parent=None):
        super().__init__(parent)
        self.setObjectName("unitCard")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(4)

        title = QLabel(unit_name)
        title.setObjectName("counterUnitName")
        title.setWordWrap(True)
        layout.addWidget(title)

        if subtitle:
            body = QLabel(subtitle)
            body.setObjectName("unitCounters")
            body.setWordWrap(True)
            layout.addWidget(body)


class CounterLineCard(QFrame):
    expandedChanged = pyqtSignal()

    def __init__(self, line_name, units, ageicons_dir, parent=None):
        super().__init__(parent)
        self.setObjectName("unitCard")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(7, 5, 7, 5)
        layout.setSpacing(4)

        self.toggle = QPushButton(line_name.replace(' line', ' Line'))
        self.toggle.setObjectName("lineToggle")
        self.toggle.setCursor(Qt.PointingHandCursor)
        self.toggle.clicked.connect(self.toggle_expanded)
        set_chevron(self.toggle, False)
        layout.addWidget(self.toggle)

        self.content = QWidget()
        content_layout = QVBoxLayout(self.content)
        content_layout.setContentsMargins(8, 2, 2, 2)
        content_layout.setSpacing(4)
        for unit in units:
            _age_text, age_key = UNIT_AGES.get(unit, ("", ""))
            age_keys = ["dark", "feudal"] if unit == "Spearman" else ([age_key] if age_key else [])
            row = QHBoxLayout()
            row.setSpacing(7)
            icons = QWidget()
            icons_layout = QHBoxLayout(icons)
            icons_layout.setContentsMargins(0, 0, 0, 0)
            icons_layout.setSpacing(3)
            for key in age_keys:
                icon = QLabel()
                icon.setFixedSize(22, 22)
                pix = QPixmap(os.path.join(ageicons_dir, AGE_ICON_FILES[key]))
                if not pix.isNull():
                    icon.setPixmap(pix.scaled(22, 22, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                icons_layout.addWidget(icon)
            icons_layout.addStretch()
            icons.setFixedWidth(48)
            name = QLabel(unit)
            name.setObjectName("counterUnitName")
            row.addWidget(icons)
            row.addWidget(name, 1)
            content_layout.addLayout(row)
        self.content.hide()
        layout.addWidget(self.content)

    def toggle_expanded(self):
        expanded = self.content.isHidden()
        self.content.setVisible(expanded)
        set_chevron(self.toggle, expanded)
        self.expandedChanged.emit()


class CollapsibleUnitSection(QWidget):
    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.expanded = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self.toggle = QPushButton()
        self.toggle.setObjectName("categoryToggle")
        self.toggle.setCursor(Qt.PointingHandCursor)
        self.toggle.clicked.connect(self.toggle_expanded)
        layout.addWidget(self.toggle)

        self.content = QWidget()
        self.content.setVisible(False)
        self.content_layout = QGridLayout(self.content)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setHorizontalSpacing(6)
        self.content_layout.setVerticalSpacing(6)
        layout.addWidget(self.content)

        self.title = title
        self._update_text()

    def toggle_expanded(self):
        self.expanded = not self.expanded
        self.content.setVisible(self.expanded)
        self._update_text()
        top = self.window()
        if top:
            top.adjustSize()

    def _update_text(self):
        self.toggle.setText(self.title)
        set_chevron(self.toggle, self.expanded)


class ElidedButton(QPushButton):
    """Push button that shortens its label with an ellipsis instead of widening."""

    def __init__(self, text="", parent=None, margin=16):
        super().__init__(parent)
        self._margin = margin
        self._full_text = text
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        self.setMinimumWidth(0)
        self._elide()

    def _elide(self):
        metrics = self.fontMetrics()
        room = max(10, self.width() - self._margin)
        super().setText(metrics.elidedText(self._full_text, Qt.ElideRight, room))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._elide()

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() == event.FontChange:
            self._elide()


class CounterChip(QFrame):
    """Compact read-only unit tag with an optional age icon."""

    def __init__(self, unit_name, ageicons_dir, portrait=None, parent=None):
        super().__init__(parent)
        self.setObjectName("counterChip")
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        self.setMinimumWidth(0)
        self.setToolTip(unit_name)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 3, 5, 3)
        layout.setSpacing(4)
        _age_text, age_key = UNIT_AGES.get(unit_name, ("", ""))
        if portrait is not None and not portrait.isNull():
            icon = QLabel()
            icon.setFixedSize(22, 22)
            icon.setPixmap(portrait.scaled(22, 22, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            layout.addWidget(icon)
        elif age_key:
            icon = QLabel()
            icon.setFixedSize(16, 16)
            pix = QPixmap(os.path.join(ageicons_dir, AGE_ICON_FILES[age_key]))
            if not pix.isNull():
                icon.setPixmap(pix.scaled(16, 16, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            layout.addWidget(icon)
        # The best upgrade is shown; the tooltip keeps the full name ("Elite ...").
        shown = re.sub(r"^(Elite |E\. |Heavy |H\. )", "", unit_name)
        self._full_text = shown
        self.label = QLabel(shown)
        self.label.setObjectName("counterUnitName")
        self.label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.label.setMinimumWidth(0)
        layout.addWidget(self.label, 1)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        room = max(10, self.label.width())
        self.label.setText(self.label.fontMetrics().elidedText(self._full_text, Qt.ElideRight, room))


LINE_LABELS = {
    "Militia": "Militia", "Spearman": "Spear", "Eagle Scout": "Eagle", "Archer": "Archer",
    "Skirmisher": "Skirm.", "Cavalry Archer": "Cav. Archer", "Scout Cavalry": "Scout",
    "Knight": "Knight", "Camel Rider": "Camel", "Steppe Lancer": "Lancer",
    "Battle Elephant": "Elephant", "Battering Ram": "Ram", "Mangonel": "Mangonel",
    "Scorpion": "Scorpion", "Galley": "Galley", "Fire Galley": "Fire ship",
    "Demolition Raft": "Demo", "Hulk": "Hulk",
}


class UnitIconButton(QPushButton):
    """Square unit-portrait button; reports hover so the panel can show the unit's name."""

    hoveredChanged = pyqtSignal(str)

    def __init__(self, unit_name, tooltip, pixmap, size, parent=None):
        super().__init__(parent)
        self.unit_name = unit_name
        self.setObjectName("unitIcon")
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip(tooltip)
        self.setFixedSize(size, size)
        if pixmap is not None and not pixmap.isNull():
            self.setIcon(QIcon(pixmap))
            self.setIconSize(QSize(size - 8, size - 8))
        else:
            self.setText(unit_name[:2])

    def enterEvent(self, event):
        super().enterEvent(event)
        self.hoveredChanged.emit(self.unit_name)

    def leaveEvent(self, event):
        super().leaveEvent(event)
        self.hoveredChanged.emit("")


class UnitCategoryBrowser(QWidget):
    """Category tabs on top; the selected category shows unit portraits.

    Units of one upgrade line share a labelled row (Militia -> Champion) and
    units that share a portrait (X / Elite X) collapse into one icon. Lines with
    a single icon are packed together in a wrapping grid underneath.
    """

    unitSelected = pyqtSignal(str)
    unitHovered = pyqtSignal(str)
    categoryOpened = pyqtSignal()
    contentChanged = pyqtSignal()

    TAB_COLUMNS = 5
    PER_ROW = 6
    LABEL_WIDTH = 66

    def __init__(self, parent=None):
        super().__init__(parent)
        self.categories = {}
        self.category_buttons = []
        self.unit_buttons = []
        self.category_sections = {}
        self.active_category = None
        self.selected_unit = None
        self.unit_line = {}
        self.line_order = []
        self.icon_files = {}
        self.icon_dir = ""
        self.icon_px = 36
        self._pixmaps = {}
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)

        self.root = QVBoxLayout(self)
        self.root.setContentsMargins(0, 0, 0, 0)
        self.root.setSpacing(6)

        self.empty_label = QLabel("No available-unit data for this civilization.")
        self.empty_label.setObjectName("muted")
        self.empty_label.setWordWrap(True)
        self.empty_label.hide()
        self.root.addWidget(self.empty_label)

        self.tabs_host = QWidget()
        self.tabs_grid = QGridLayout(self.tabs_host)
        self.tabs_grid.setContentsMargins(0, 0, 0, 0)
        self.tabs_grid.setHorizontalSpacing(4)
        self.tabs_grid.setVerticalSpacing(4)
        self.root.addWidget(self.tabs_host)

        self.units_host = QWidget()
        self.units_host.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.units_layout = QVBoxLayout(self.units_host)
        self.units_layout.setContentsMargins(0, 2, 0, 2)
        self.units_layout.setSpacing(5)
        self.root.addWidget(self.units_host)

    def configure(self, counter_data, icon_dir):
        """Line grouping comes from unit_counters_v2.json, portraits from UnitIcons/."""
        units = (counter_data or {}).get("units") or {}
        self.unit_line = {name: entry.get("line", name) for name, entry in units.items()}
        self.line_order = list((counter_data or {}).get("line_order") or [])
        self.group_order = list((counter_data or {}).get("group_order") or [])
        self.unit_group = {name: entry.get("group", "Other") for name, entry in units.items()}
        self.line_members = (counter_data or {}).get("lines") or {}
        self.icon_dir = icon_dir
        manifest = load_json(os.path.join(icon_dir, "manifest.json"), {})
        self.icon_files = manifest if isinstance(manifest, dict) else {}

    def set_icon_size(self, size):
        size = max(30, int(size))
        if size != self.icon_px:
            self.icon_px = size
            if self.active_category:
                self._activate(self.active_category, notify=False)

    def set_categories(self, categories):
        self.clear()
        self.categories = categories or {}

        if not self.categories:
            self.empty_label.show()
            self.tabs_host.hide()
            self.units_host.hide()
            self.contentChanged.emit()
            return

        self.tabs_host.show()
        self.units_host.show()
        for index, category in enumerate(self.categories):
            button = ElidedButton(self._category_display_name(category), margin=6)
            button.setObjectName("categoryTab")
            button.setCursor(Qt.PointingHandCursor)
            button.setToolTip(category)
            button.setCheckable(True)
            button.clicked.connect(lambda _checked=False, cat=category: self.toggle_category(cat))
            self.tabs_grid.addWidget(button, index // self.TAB_COLUMNS, index % self.TAB_COLUMNS)
            self.category_buttons.append(button)
            self.category_sections[category] = {"button": button, "unit_buttons": []}
        for col in range(self.TAB_COLUMNS):
            self.tabs_grid.setColumnStretch(col, 1)
            self.tabs_grid.setColumnMinimumWidth(col, 0)
        self._activate(next(iter(self.categories)), notify=False)

    def show_units(self, category):
        if category in self.category_sections and category != self.active_category:
            self.toggle_category(category)

    def toggle_category(self, category):
        """Select a category tab; one category is always shown."""
        if category not in self.category_sections:
            return
        changed = category != self.active_category
        self._activate(category, notify=changed)
        if not changed:
            self.category_sections[category]["button"].setChecked(True)

    def select_unit(self, unit_name):
        self.selected_unit = unit_name
        for button in self.unit_buttons:
            button.setChecked(unit_name in button.property("members"))

    # -- building the rows ----------------------------------------------------
    def _pixmap(self, unit):
        file_name = self.icon_files.get(unit)
        if not file_name:
            return None
        if file_name not in self._pixmaps:
            pix = QPixmap(os.path.join(self.icon_dir, file_name))
            self._pixmaps[file_name] = pix if not pix.isNull() else None
        return self._pixmaps[file_name]

    def _line_groups(self, units):
        """[(line key, [units in upgrade order])] with generic lines first."""
        groups = {}
        for unit in units:
            groups.setdefault(self.unit_line.get(unit, unit), []).append(unit)
        for key, members in groups.items():
            chain = self.line_members.get(key, [])
            members.sort(key=lambda u: chain.index(u) if u in chain else len(chain))

        def order(key):
            if key in self.line_order:
                return (0, self.line_order.index(key), "")
            return (1, 0, key)
        return [(key, groups[key]) for key in sorted(groups, key=order)]

    def _slots(self, members):
        """Collapse neighbours with an identical portrait into one slot (highest tier wins)."""
        slots = []
        for unit in members:
            icon = self.icon_files.get(unit)
            if slots and icon and self.icon_files.get(slots[-1][-1]) == icon:
                slots[-1].append(unit)
            else:
                slots.append([unit])
        return slots

    def _make_button(self, slot):
        unit = slot[-1]
        button = UnitIconButton(unit, " / ".join(slot), self._pixmap(unit), self.icon_px)
        button.setProperty("members", list(slot))
        button.setChecked(self.selected_unit in slot)
        button.clicked.connect(lambda _checked=False, name=unit: self._clicked(name))
        button.hoveredChanged.connect(self.unitHovered.emit)
        self.unit_buttons.append(button)
        return button

    def _add_row(self, text, tooltip, slots):
        row = QHBoxLayout()
        row.setSpacing(4)
        label = QLabel("")
        label.setObjectName("lineLabel")
        label.setFixedWidth(self.LABEL_WIDTH)
        label.setText(label.fontMetrics().elidedText(text, Qt.ElideRight, self.LABEL_WIDTH - 4))
        label.setToolTip(tooltip)
        row.addWidget(label)
        for slot in slots:
            row.addWidget(self._make_button(slot))
        row.addStretch()
        self.units_layout.addLayout(row)

    def _clicked(self, unit):
        self.select_unit(unit)
        self.unitSelected.emit(unit)

    def _activate(self, category, notify=True):
        self.active_category = category
        for name, section in self.category_sections.items():
            section["button"].setChecked(name == category)
        self._clear_units()

        # Standard upgrade lines (Militia -> Champion) get a row each; every other unit is
        # collected under a type name (Siege, Gunpowder, ...) so no icon is left unlabelled.
        grouped = {}
        for key, members in self._line_groups(self.categories.get(category, [])):
            slots = self._slots(members)
            if len(slots) >= 2 and key in LINE_LABELS:
                self._add_row(LINE_LABELS[key], f"{key} line", slots)
            else:
                group = self.unit_group.get(members[0], "Other")
                grouped.setdefault(group, []).extend(slots)
        group_rank = {name: i for i, name in enumerate(self.group_order)}
        for group in sorted(grouped, key=lambda g: group_rank.get(g, len(group_rank))):
            slots = grouped[group]
            for start in range(0, len(slots), self.PER_ROW):
                self._add_row(group if start == 0 else "", group, slots[start:start + self.PER_ROW])

        self.category_sections[category]["unit_buttons"] = list(self.unit_buttons)
        if notify:
            self.categoryOpened.emit()
        self.contentChanged.emit()
        self._resize_top()

    def _clear_units(self):
        def wipe(layout):
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                child = item.layout()
                if child is not None:
                    wipe(child)
                if widget:
                    widget.hide()
                    widget.setParent(None)
                    widget.deleteLater()
        wipe(self.units_layout)
        self.unit_buttons = []

    def clear(self):
        self.categories = {}
        self.category_buttons = []
        self.category_sections = {}
        self.active_category = None
        self.selected_unit = None
        self.empty_label.hide()
        while self.tabs_grid.count():
            item = self.tabs_grid.takeAt(0)
            widget = item.widget()
            if widget:
                widget.hide()
                widget.setParent(None)
                widget.deleteLater()
        self._clear_units()

    def _resize_top(self):
        self.adjustSize()
        top = self.window()
        if top:
            top.adjustSize()
            top.updateGeometry()

    def _category_display_name(self, category):
        names = {
            "Archery Range": "Archery",
            "Siege Workshop": "Siege",
            "Monastery / Church": "Monks",
            "Monastery": "Monks",
            "Defensive Structures": "Defense",
            "Hero Units": "Hero",
        }
        return names.get(category, category)


class CivMatchupPanel(QWidget):
    def __init__(self, civ_data_path="civ_data.json", units_db_path="units_db.json",
                 strategies_path="typical_strategies.json", assets_root=None, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.setMinimumWidth(0)
        self.assets_root = assets_root or os.path.dirname(os.path.abspath(__file__))
        self.civ_data_path = self._resolve(civ_data_path)
        self.units_db_path = self._resolve(units_db_path)
        self.strategies_path = self._resolve(strategies_path)
        self.civicons_dir = os.path.join(self.assets_root, "CivIcons")
        self.ageicons_dir = os.path.join(self.assets_root, "AgeIcons")

        self.civ_data = load_json(self.civ_data_path, {})
        self.units_db = load_json(self.units_db_path, {})
        catalog = load_json(os.path.join(self.assets_root, "techtree_data.json"), {})
        if catalog.get("civs") and catalog.get("units"):
            from editable_catalog import apply_catalog_edits
            catalog = apply_catalog_edits(
                catalog, load_json(os.path.join(self.assets_root, "civ_data.json"), {}), self.civ_data,
                load_json(os.path.join(self.assets_root, "units_db.json"), {}), self.units_db)
            self.civ_data = catalog["civs"]
            self.units_db = catalog["units"]
        self.counter_data = load_json(os.path.join(self.assets_root, "unit_counters_v2.json"), {})
        self._selected_unit = None
        write_json_if_missing(self.strategies_path, self._default_strategies())
        self.typical_strategies = load_json(self.strategies_path, {})

        self.current_civ = None
        self.current_player_name = None
        self.player_civ = None
        self.category_buttons = {}
        self.category_units = {}
        self.active_unit_category = None
        self.scale_factor = 1.0
        self.base_font_size = 9
        self._strategy_open = False
        self._strategy_anim = None

        self._build_ui()
        self.clear_selection()

    def _resolve(self, path):
        if os.path.isabs(path):
            return path
        return os.path.join(self.assets_root, path)

    def _default_strategies(self):
        return {
            civ: {
                "summary": "",
                "typical_strategies": [],
                "notes": ""
            }
            for civ in sorted(self.civ_data.keys())
        }

    def _build_ui(self):
        self.setStyleSheet(f"""
            QWidget {{
                background: transparent;
                color: {FG};
                font-family: 'Segoe UI';
            }}
            QLabel#panelHint {{
                color: {MUTED};
            }}
            QLabel#civName {{
                color: {FG};
                font-weight: 700;
            }}
            QLabel#sectionTitle {{
                color: {ACCENT};
                font-weight: 700;
            }}
            QLabel#counterTitle {{
                color: {COUNTER_ACCENT};
                font-weight: 700;
            }}
            QLabel#muted {{
                color: {MUTED};
            }}
            QTextEdit {{
                background: rgba(6, 12, 19, 0.46);
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 8px;
                padding: 6px;
                color: {FG};
            }}
            QPushButton {{
                background: rgba(255, 255, 255, 0.055);
                border: 1px solid rgba(255, 255, 255, 0.13);
                border-radius: 7px;
                padding: 4px 7px;
                color: {FG};
            }}
            QPushButton:hover {{
                background: rgba(255, 255, 255, 0.14);
            }}
            QPushButton#categoryTab {{
                background: rgba(255, 255, 255, 0.045);
                border: 1px solid rgba(255, 255, 255, 0.09);
                border-radius: 7px;
                padding: 4px 1px;
                color: {MUTED};
                font-weight: 600;
            }}
            QPushButton#categoryTab:hover {{
                background: rgba(255, 255, 255, 0.12);
                color: {FG};
            }}
            QPushButton#categoryTab:checked {{
                background: rgba(167, 243, 208, 0.18);
                border-color: rgba(167, 243, 208, 0.50);
                color: {ACCENT};
            }}
            QPushButton#unitIcon {{
                background: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 7px;
                padding: 0px;
                color: {FG};
                font-weight: 700;
            }}
            QPushButton#unitIcon:hover {{
                background: rgba(255, 255, 255, 0.15);
                border-color: rgba(255, 255, 255, 0.35);
            }}
            QPushButton#unitIcon:checked {{
                background: rgba(167, 243, 208, 0.20);
                border: 2px solid rgba(167, 243, 208, 0.80);
            }}
            QLabel#lineLabel {{
                color: {MUTED};
                font-size: 8pt;
            }}
            QLabel#unitCaption {{
                color: {FG};
                font-weight: 600;
            }}
            QPushButton#strategyToggle {{
                text-align: left;
                color: {ACCENT};
                font-weight: 700;
                padding: 4px 8px;
            }}
            QFrame#counterChip {{
                background: rgba(253, 164, 175, 0.07);
                border: 1px solid rgba(253, 164, 175, 0.22);
                border-radius: 7px;
            }}
            QLabel#counterClass {{
                color: {COUNTER_ACCENT};
                font-weight: 700;
            }}
            QPushButton#unitButton {{
                text-align: left;
                background: rgba(255, 255, 255, 0.055);
                border: 1px solid rgba(255, 255, 255, 0.09);
                border-radius: 8px;
                padding: 6px 6px;
            }}
            QPushButton#unitButton:hover {{
                background: rgba(255, 255, 255, 0.13);
            }}
            QPushButton#unitButton:pressed {{
                background: rgba(167, 243, 208, 0.18);
                border-color: rgba(167, 243, 208, 0.42);
            }}
            QPushButton#lineToggle {{
                text-align: left;
                color: {COUNTER_ACCENT};
                font-weight: 700;
                background: transparent;
                border: none;
                padding: 4px 2px;
            }}
            QPushButton#lineToggle:hover {{
                background: rgba(255, 255, 255, 0.08);
            }}
            QPushButton#categoryToggle {{
                text-align: left;
                color: {ACCENT};
                font-weight: 700;
                background: rgba(255, 255, 255, 0.055);
                border: 1px solid rgba(255, 255, 255, 0.10);
                border-radius: 8px;
                padding: 7px 5px;
            }}
            QPushButton#categoryToggle:hover {{
                background: rgba(255, 255, 255, 0.12);
            }}
            QPushButton#saveButton {{
                padding: 5px 12px;
            }}
            QFrame#unitCard {{
                background: rgba(255, 255, 255, 0.04);
                border: 1px solid rgba(255, 255, 255, 0.11);
                border-radius: 8px;
            }}
            QLabel#unitTitle {{
                color: {FG};
                font-weight: 700;
            }}
            QLabel#counterUnitName {{
                color: {FG};
                font-weight: 400;
            }}
            QLabel#unitCounters {{
                color: {MUTED};
            }}
            QScrollArea#availableArea {{
                background: rgba(167, 243, 208, 0.035);
                border: 1px solid rgba(167, 243, 208, 0.18);
                border-radius: 10px;
                padding: 6px;
            }}
            QScrollArea#counterArea {{
                background: rgba(253, 164, 175, 0.045);
                border: 1px solid rgba(253, 164, 175, 0.22);
                border-radius: 10px;
                padding: 6px;
            }}
        """)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 4, 0, 0)
        root.setSpacing(6)

        self.hint = QLabel(DEFAULT_HINT)
        self.hint.setObjectName("panelHint")
        self.hint.setWordWrap(True)
        root.addWidget(self.hint)

        # One row: Strategy toggle, civ icon, civ name, Hide.
        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(8)

        self.strategy_button = QPushButton("Strategy")
        self.strategy_button.setObjectName("strategyToggle")
        self.strategy_button.setCursor(Qt.PointingHandCursor)
        self.strategy_button.setToolTip("Show team bonus and typical strategies")
        self.strategy_button.clicked.connect(self.toggle_strategy)
        set_chevron(self.strategy_button, False)
        header.addWidget(self.strategy_button)

        self.icon = QLabel()
        self.icon.setFixedSize(24, 24)
        self.icon.setScaledContents(True)
        header.addWidget(self.icon)

        self.civ_name = QLabel("")
        self.civ_name.setObjectName("civName")
        # The civilization name must not become the panel's preferred width.
        # The overlay owns the width and this label uses the space left between
        # the icon and the Hide button.
        self.civ_name.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.civ_name.setMinimumWidth(0)
        header.addWidget(self.civ_name, 1)

        self.close_button = QPushButton("Hide")
        self.close_button.clicked.connect(self.clear_selection)
        header.addWidget(self.close_button)

        root.addLayout(header)

        self.strategy_box = QWidget()
        strategy_layout = QVBoxLayout(self.strategy_box)
        strategy_layout.setContentsMargins(0, 0, 0, 0)
        strategy_layout.setSpacing(4)
        self.team_bonus = QLabel("")
        self.team_bonus.setObjectName("muted")
        self.team_bonus.setWordWrap(True)
        strategy_layout.addWidget(self.team_bonus)
        self.strategy_text = QTextEdit()
        self.strategy_text.setReadOnly(True)
        self.strategy_text.setMinimumHeight(49)
        self.strategy_text.setMaximumHeight(70)
        strategy_layout.addWidget(self.strategy_text)
        self.strategy_box.hide()
        root.addWidget(self.strategy_box)

        self.unit_title = QLabel("Available Units")
        self.unit_title.setObjectName("sectionTitle")
        self.unit_caption = QLabel("")
        self.unit_caption.setObjectName("unitCaption")
        self.unit_caption.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.unit_caption.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.unit_caption.setMinimumWidth(0)
        unit_title_row = QHBoxLayout()
        unit_title_row.setContentsMargins(0, 0, 0, 0)
        unit_title_row.addWidget(self.unit_title)
        unit_title_row.addWidget(self.unit_caption, 1)
        root.addLayout(unit_title_row)

        self.unit_scroll = QScrollArea()
        self.unit_scroll.setObjectName("availableArea")
        self.unit_scroll.viewport().setStyleSheet("background: transparent;")
        self.unit_scroll.setWidgetResizable(True)
        self.unit_scroll.setFrameShape(QFrame.NoFrame)
        self.unit_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.unit_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.unit_scroll.setMinimumHeight(1)
        self.unit_scroll.setMaximumHeight(260)
        self.unit_browser = UnitCategoryBrowser()
        self.unit_browser.configure(self.counter_data, os.path.join(self.assets_root, "UnitIcons"))
        self.unit_browser.unitSelected.connect(self._show_counters_for_unit)
        self.unit_browser.unitHovered.connect(self._show_unit_caption)
        self.unit_browser.categoryOpened.connect(self._hide_counters)
        self.unit_browser.contentChanged.connect(self._fit_unit_area)
        self.unit_browser.contentChanged.connect(lambda: QTimer.singleShot(0, self._fit_unit_area))
        self.unit_scroll.setWidget(self.unit_browser)
        root.addWidget(self.unit_scroll)

        self.counter_title = QLabel("Select a unit to see counters you can make")
        self.counter_title.setObjectName("counterTitle")
        self.counter_title.setWordWrap(True)
        root.addWidget(self.counter_title)

        self.counter_scroll = QScrollArea()
        self.counter_scroll.setObjectName("counterArea")
        self.counter_scroll.viewport().setStyleSheet("background: transparent;")
        self.counter_scroll.setWidgetResizable(True)
        self.counter_scroll.setFrameShape(QFrame.NoFrame)
        self.counter_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.counter_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.counter_scroll.setMinimumHeight(1)
        self.counter_scroll.setMaximumHeight(240)
        self.counter_host = QWidget()
        self.counter_cards = QGridLayout(self.counter_host)
        self.counter_cards.setContentsMargins(0, 0, 0, 0)
        self.counter_cards.setHorizontalSpacing(8)
        self.counter_cards.setVerticalSpacing(8)
        self.counter_scroll.setWidget(self.counter_host)
        root.addWidget(self.counter_scroll)

        self.detail_widgets = [
            self.icon, self.civ_name, self.close_button, self.strategy_button,
            self.unit_title, self.unit_caption, self.unit_scroll, self.counter_title, self.counter_scroll
        ]

    def clear_selection(self):
        self.current_civ = None
        self.current_player_name = None
        self.player_civ = None
        self.hint.setText(DEFAULT_HINT)
        self.hint.show()
        for widget in self.detail_widgets:
            widget.hide()
        self.unit_browser.clear()
        self._clear_grid(self.counter_cards)
        self.counter_title.hide()
        self.counter_scroll.hide()
        self.strategy_text.clear()
        self.strategy_box.hide()
        self.hide()
        self.updateGeometry()
        top = self.window()
        if top:
            top.layout().invalidate() if top.layout() else None
            top.adjustSize()
            top.updateGeometry()

    def select_civ(self, civ_name, player_name=None, player_civ=None):
        if not civ_name:
            return
        if civ_name not in self.civ_data:
            # A civilisation newer than the bundled tech-tree data: say so instead of doing nothing.
            self.show()
            self.hint.setText(f"No unit data for {civ_name} yet - update Age of Duck for the latest civilisations.")
            self.hint.show()
            for widget in self.detail_widgets:
                widget.hide()
            self.strategy_box.hide()
            self._resize_top()
            return
        self.hint.setText(DEFAULT_HINT)
        self.show()
        self.current_civ = civ_name
        self._selected_unit = None
        self.unit_caption.setText("")
        self.current_player_name = player_name
        self.player_civ = player_civ
        self.hint.hide()
        for widget in self.detail_widgets:
            widget.show()

        civ = self.civ_data.get(civ_name, {})
        self.civ_name.setText(civ_name)
        self.civ_name.setToolTip(civ_name if not player_name else f"{player_name} - {civ_name}")
        self.team_bonus.setText(f"Team bonus: {civ.get('civTeamBonus', 'No team bonus data')}")

        icon_path = os.path.join(self.civicons_dir, f"{civ_name}_AoE2.webp")
        pix = QPixmap(icon_path)
        if pix.isNull():
            self.icon.hide()
        else:
            self.icon.show()
            self.icon.setPixmap(pix)

        self.strategy_text.setPlainText(self._strategy_text(civ_name, civ))
        self.strategy_box.setVisible(self._strategy_open)
        if self._strategy_open:
            self.strategy_box.setMaximumHeight(16777215)
        units_by_category = self._available_units_by_category(civ_name)
        self._populate_unit_categories(units_by_category)
        self._hide_counters()
        self._resize_top()

    def set_scale(self, factor, base_overlay_pt=None):
        self.scale_factor = factor
        self.base_font_size = base_overlay_pt or max(8, int(9 * factor))
        base = self.base_font_size
        self.civ_name.setFont(QFont("Segoe UI", base + 2, QFont.DemiBold))
        for label in (self.hint, self.team_bonus, self.unit_title, self.counter_title):
            label.setFont(QFont("Segoe UI", base))
        self.strategy_text.setFont(QFont("Segoe UI", base))
        self.strategy_button.setFont(QFont("Segoe UI", base, QFont.DemiBold))
        self.close_button.setFont(QFont("Segoe UI", base))
        icon_size = max(22, int(round(24 * factor)))
        self.icon.setFixedSize(icon_size, icon_size)
        tab_font = QFont("Segoe UI", max(7, base - 1))
        self.unit_browser.setFont(tab_font)
        self.unit_caption.setFont(QFont("Segoe UI", base, QFont.DemiBold))
        self.unit_browser.set_icon_size(round(36 * factor))
        self._fit_unit_area()

    def toggle_strategy(self):
        """Slide the team bonus / strategy text open or closed under the header."""
        self._strategy_open = not self._strategy_open
        set_chevron(self.strategy_button, self._strategy_open)
        if self._strategy_anim:
            self._strategy_anim.stop()
        box = self.strategy_box
        box.setMaximumHeight(16777215)
        box.setVisible(True)
        self.layout().activate()
        full = box.sizeHint().height()
        start = box.height() if box.isVisible() else 0
        anim = QVariantAnimation(self)
        anim.setDuration(200)
        anim.setEasingCurve(QEasingCurve.InOutCubic)
        anim.setStartValue(start if not self._strategy_open else 0)
        anim.setEndValue(full if self._strategy_open else 0)
        anim.valueChanged.connect(lambda value: (box.setMaximumHeight(int(value)), self._resize_top()))

        def finished():
            if self._strategy_open:
                box.setMaximumHeight(16777215)
            else:
                box.hide()
            self._resize_top()

        anim.finished.connect(finished)
        self._strategy_anim = anim
        anim.start()

    def _fit_unit_area(self):
        """Size the unit area to its content (scrolls only when unusually tall)."""
        browser = self.unit_browser
        browser.layout().activate()
        height = browser.sizeHint().height() + 14
        self.unit_scroll.setFixedHeight(max(40, min(260, height)))
        self._resize_top()

    def _strategy_text(self, civ_name, civ):
        custom = self.typical_strategies.get(civ_name, {})
        parts = []

        summary = custom.get("summary") if isinstance(custom, dict) else ""
        if summary:
            parts.append(summary)

        strategies = custom.get("typical_strategies", []) if isinstance(custom, dict) else []
        if strategies:
            parts.append("Typical openings/plans:\n" + "\n".join(f"- {item}" for item in strategies))

        notes = custom.get("notes") if isinstance(custom, dict) else ""
        if notes:
            parts.append("Notes:\n" + notes)

        if not parts:
            existing = civ.get("civStrategy", "")
            if existing:
                parts.append(existing)
            else:
                parts.append("No strategy information is available for this civilization.")

        return "\n\n".join(parts)

    def _available_units_by_category(self, civ_name):
        civ = self.civ_data.get(civ_name, {})
        categories = {}
        units_available = civ.get("unitsAvailable", {}) or {}
        unique_units = civ.get("unique_units_by_category", {}) or {}

        for category, values in units_available.items():
            if category in HIDDEN_UNIT_CATEGORIES:
                continue
            if isinstance(values, dict):
                label = self._category_label(category)
                categories.setdefault(label, [])
                for unit, available in values.items():
                    if available:
                        categories[label].append(unit)

        for category, values in unique_units.items():
            if isinstance(values, list):
                label = self._category_label(category)
                categories.setdefault(label, [])
                categories[label].extend(values)

        ordered = {}
        for category in self._category_order():
            if category in categories:
                ordered[category] = sorted(dict.fromkeys(categories[category]))
        for category in sorted(k for k in categories if k not in ordered):
            ordered[category] = sorted(dict.fromkeys(categories[category]))
        return ordered

    def _populate_unit_categories(self, units_by_category):
        self.category_buttons = {}
        self.category_units = {}
        self.active_unit_category = None
        self.unit_browser.set_categories(units_by_category)
        self._hide_counters()
        self._resize_top()

    def _hide_counters(self):
        self._clear_grid(self.counter_cards)
        self.counter_scroll.setMinimumHeight(1)
        self.counter_scroll.setMaximumHeight(1)
        self.counter_title.hide()
        self.counter_scroll.hide()
        self._resize_top()

    def _show_unit_caption(self, unit_name):
        """Hovering a portrait names it; leaving falls back to the selected unit."""
        self.unit_caption.setText(unit_name or self._selected_unit or "")

    def _show_counters_for_unit(self, unit_name):
        self._selected_unit = unit_name
        self.unit_caption.setText(unit_name)
        self._clear_grid(self.counter_cards)
        civ_text = self.player_civ or "your civ"
        self.counter_title.setText(f"{civ_text} counters for {unit_name}")
        self.counter_title.show()
        self.counter_scroll.show()
        columns = 3
        row = 0

        source_unit = self.units_db.get(unit_name, {})
        if source_unit.get("source") == "aoe2techtree.net":
            card = UnitCard(unit_name, source_unit.get("unitDescription", "Description unavailable."))
            self.counter_cards.addWidget(card, row, 0, 1, columns)
            row += 1
            sections = [(f"Weak vs. {name}", units) for name, units in self._class_counters(unit_name)]
            seen = {u for _title, units in sections for u in units}
            sections += self._unique_counters(unit_name, seen)
            if sections:
                for title_text, units in sections:
                    title = QLabel(title_text)
                    title.setObjectName("counterClass")
                    self.counter_cards.addWidget(title, row, 0, 1, columns)
                    row += 1
                    for index, unit in enumerate(units):
                        chip = CounterChip(unit, self.ageicons_dir, self.unit_browser._pixmap(unit))
                        self.counter_cards.addWidget(chip, row + index // columns, index % columns)
                    row += (len(units) + columns - 1) // columns
            elif source_unit.get("unitDescription", "").find("Weak vs") != -1:
                card = UnitCard("No buildable counters found",
                                f"{civ_text} has no unit matching this unit's weaknesses.")
                self.counter_cards.addWidget(card, row, 0, 1, columns)
        else:
            counters = self._counter_units_for_player_civ(unit_name)
            if not counters:
                card = UnitCard("No buildable counters found", f"{civ_text} has no matching counter units in the current data.")
                self.counter_cards.addWidget(card, row, 0, 1, columns)
            else:
                grouped, standalone = self._group_counter_units(counters)
                for line_name, units in grouped:
                    card = CounterLineCard(line_name, units, self.ageicons_dir)
                    card.expandedChanged.connect(self._schedule_counter_resize)
                    self.counter_cards.addWidget(card, row, 0, 1, columns)
                    row += 1
                for index, unit in enumerate(standalone):
                    card = UnitCard(unit)
                    self.counter_cards.addWidget(card, row + (index // 2), index % 2)

        for col in range(columns):
            self.counter_cards.setColumnStretch(col, 1)
            self.counter_cards.setColumnMinimumWidth(col, 0)

        self._resize_counter_area()
        QTimer.singleShot(0, self._resize_counter_area)
        QTimer.singleShot(50, self._resize_counter_area)

    MAX_COUNTERS_PER_CLASS = 9
    UNIQUE_CLASS_ORDER = ["Cavalry", "Mounted Units", "Infantry", "Foot Archers", "Archery Units", "Ranged Soldiers",
                          "Skirmishers", "Siege Weapons", "Gunpowder Units", "Monks", "Camel Riders", "Spearman-line",
                          "Scout Cavalry-line", "Mounted Archers", "units at close range", "melee units"]

    def _class_counters(self, unit_name):
        """Counter units per weakness class, limited to what the player's civ can build.

        Data comes from unit_counters_v2.json: each unit lists the classes it is
        weak against and each class lists its unit lines (upgrade chains). The
        best available upgrade of every line is offered.
        """
        entry = (self.counter_data.get("units") or {}).get(unit_name) or {}
        classes = self.counter_data.get("classes") or {}
        buildable = set(self._available_units(self.player_civ)) if self.player_civ else None
        seen = set()
        sections = []
        for class_name in entry.get("weak_vs", []):
            best = []
            for chain in classes.get(class_name, []):
                options = [u for u in chain if buildable is None or u in buildable]
                if not options:
                    continue
                unit = options[-1]
                if unit in seen:
                    continue
                best.append(unit)
            if not best:
                continue
            seen.update(best)
            sections.append((class_name, best[:self.MAX_COUNTERS_PER_CLASS]))
        return sections

    def _unique_counters(self, unit_name, seen):
        """Unique units of the player's civ whose own description says they are strong vs. this unit.

        Counter classes come from the selected unit's weaknesses, which never name unique units
        (a Varangian Guard is "Strong vs. Cavalry" but no cavalry is "weak vs." it). So look at it
        from the other side: every available unique unit whose "Strong vs." classes include one
        the selected unit belongs to.
        """
        data = self.counter_data.get("units") or {}
        entry = data.get(unit_name) or {}
        targets = set(entry.get("member_of", [])) - {"Unique Units"}
        if entry.get("unique"):
            targets |= {"Unique Units"} & set(entry.get("member_of", []))
        if not targets:
            return []
        lines = self.counter_data.get("lines") or {}
        buildable = set(self._available_units(self.player_civ)) if self.player_civ else None
        own_line = entry.get("line")
        found = {}
        for name, info in data.items():
            if not info.get("unique") or info.get("line") == own_line or name in seen:
                continue
            if buildable is not None and name not in buildable:
                continue
            chain = lines.get(info.get("line"), [name])
            usable = [u for u in chain if buildable is None or u in buildable]
            if not usable or name != usable[-1]:
                continue        # show only the best upgrade of each line
            matched = [c for c in info.get("strong_vs", []) if c in targets]
            if not matched:
                continue
            klass = min(matched, key=lambda c: self.UNIQUE_CLASS_ORDER.index(c) if c in self.UNIQUE_CLASS_ORDER else 99)
            found.setdefault(klass, []).append(name)
        order = lambda c: self.UNIQUE_CLASS_ORDER.index(c) if c in self.UNIQUE_CLASS_ORDER else 99
        return [(f"Unique units · strong vs. {klass}", sorted(units)[:self.MAX_COUNTERS_PER_CLASS])
                for klass, units in sorted(found.items(), key=lambda item: order(item[0]))]

    def _group_counter_units(self, counters):
        groups = {}
        order = []
        for unit in counters:
            line = self._counter_line(unit)
            if line:
                if line not in groups:
                    groups[line] = []
                    order.append(line)
                groups[line].append(unit)

        grouped = []
        standalone = []
        for line in order:
            members = groups[line]
            if len(members) >= 2:
                canonical = COUNTER_UNIT_LINES.get(line, [])
                members.sort(key=lambda name: canonical.index(name) if name in canonical else len(canonical))
                grouped.append((line, members))
            else:
                standalone.extend(members)
        standalone.extend(unit for unit in counters if not self._counter_line(unit))
        return grouped, standalone

    def _counter_line(self, unit):
        configured = self.units_db.get(unit, {}).get("configLine", "").strip()
        if configured and configured != "Other units":
            return configured
        for line, members in COUNTER_UNIT_LINES.items():
            if unit in members:
                return line
        return None

    def _schedule_counter_resize(self):
        QTimer.singleShot(0, self._resize_counter_area)

    def _resize_counter_area(self):
        self.counter_cards.invalidate()
        self.counter_cards.activate()
        self.counter_host.updateGeometry()
        target_height = min(340, max(68, self.counter_cards.sizeHint().height() + 16))
        self.counter_scroll.setMinimumHeight(target_height)
        self.counter_scroll.setMaximumHeight(target_height)
        self._resize_top()

    def _counter_units_for_player_civ(self, unit_name):
        countered_by = self._relation_units(self.units_db.get(unit_name, {}), "countered_by")
        if not self.player_civ:
            return countered_by
        buildable = set(self._available_units(self.player_civ))
        return [unit for unit in countered_by if unit in buildable]

    def _available_units(self, civ_name):
        units = []
        for values in self._available_units_by_category(civ_name).values():
            units.extend(values)
        return sorted(dict.fromkeys(units))

    def _category_label(self, category):
        labels = {
            "Military": "Barracks",
            "Archery": "Archery Range",
            "Cavalry": "Stable",
            "Siege": "Siege Workshop",
            "Castle Units": "Castle",
            "Monastery/Church": "Monastery / Church",
            "Docks": "Dock",
            "Defensive Structures": "Defensive Structures",
            "Hero Unit": "Hero Units",
        }
        return labels.get(category, category)

    def _category_order(self):
        return [
            "Barracks",
            "Archery Range",
            "Stable",
            "Siege Workshop",
            "Castle",
            "Monastery / Church",
            "Dock",
            "Defensive Structures",
            "Hero Units",
        ]

    def _clear_grid(self, grid):
        while grid.count():
            item = grid.takeAt(0)
            widget = item.widget()
            if widget:
                widget.hide()
                widget.setParent(None)
                widget.deleteLater()

    def _clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            child_layout = item.layout()
            if child_layout:
                self._clear_layout(child_layout)
            if widget:
                widget.deleteLater()

    def _resize_top(self):
        self.updateGeometry()
        top = self.window()
        if top:
            layout = top.layout()
            if layout:
                layout.invalidate()
                layout.activate()
            top.adjustSize()
            top.updateGeometry()

    def _relation_units(self, data, key):
        values = []
        for entry in data.get(key, []) if isinstance(data, dict) else []:
            if isinstance(entry, dict) and entry.get("unit"):
                values.append(entry["unit"])
            elif isinstance(entry, str):
                values.append(entry)
        return values

