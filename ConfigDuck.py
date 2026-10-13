import copy
import json
import os
import shutil
import sys
import re
from datetime import datetime

from PyQt5.QtCore import QStandardPaths, Qt
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFileDialog,
    QFormLayout, QHBoxLayout, QInputDialog, QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QMainWindow, QMenu, QMessageBox, QPushButton, QSplitter, QTabWidget, QTextEdit,
    QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget,
)


APP_DATA_DIR = os.path.join(
    QStandardPaths.writableLocation(QStandardPaths.AppDataLocation), "AgeOfDuck"
)
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
BUNDLE_DIR = getattr(sys, "_MEIPASS", PROJECT_DIR)
CATEGORIES = [
    "Military", "Archery", "Cavalry", "Siege", "Defensive Structures",
    "Castle Units", "Monastery/Church", "Docks", "Hero Unit",
]
UNIT_LINES = {
    "Militia line": {"Militia", "Man-at-Arms", "Long Swordsman", "Two-Handed Swordsman", "Champion"},
    "Spearman line": {"Spearman", "Pikeman", "Halberdier"},
    "Archer line": {"Archer", "Crossbowman", "Arbalester"},
    "Skirmisher line": {"Skirmisher", "Elite Skirmisher", "Imperial Skirmisher"},
    "Cavalry Archer line": {"Cavalry Archer", "Heavy Cavalry Archer"},
    "Scout Cavalry line": {"Scout Cavalry", "Light Cavalry", "Hussar", "Winged Hussar"},
    "Knight line": {"Knight", "Cavalier", "Paladin", "Savar"},
    "Camel line": {"Camel Scout", "Camel Rider", "Heavy Camel Rider", "Imperial Camel Rider"},
    "Steppe Lancer line": {"Steppe Lancer", "Elite Steppe Lancer"},
    "Battle Elephant line": {"Battle Elephant", "Elite Battle Elephant"},
    "Ram line": {"Battering Ram", "Capped Ram", "Siege Ram"},
    "Mangonel line": {"Mangonel", "Onager", "Siege Onager"},
    "Scorpion line": {"Scorpion", "Heavy Scorpion"},
    "Tower line": {"Watch Tower", "Guard Tower", "Keep", "Bombard Tower"},
    "Galley line": {"Galley", "War Galley", "Galleon"},
    "Fire Ship line": {"Fire Galley", "Fire Ship", "Fast Fire Ship"},
    "Demolition Ship line": {"Demolition Raft", "Demolition Ship", "Heavy Demo Ship", "Heavy Demolition Ship"},
    "Cannon Galleon line": {"Cannon Galleon", "Elite Cannon Galleon"},
}
UNIT_TYPE_OPTIONS = [
    "Infantry", "Archer", "Cavalry", "Cavalry Archer", "Camel", "Siege",
    "Gunpowder Unit", "Monk", "Ship", "Structure", "Ranged", "Melee",
    "Unique Unit", "Hero Unit",
]
TEXT_FIELDS = [
    ("civSummary", "Summary"),
    ("civTeamBonus", "Team bonus"),
    ("civStrength", "Strengths"),
    ("civWeakness", "Weaknesses"),
    ("civStrategy", "Built-in strategy"),
]


def base_unit_name(name):
    return re.sub(r"-(Dark|Feud|Castle\s*|Imp)$", "", name).strip()


def unit_line(name, unit_data=None):
    configured = (unit_data or {}).get("configLine", "").strip()
    if configured:
        return configured
    base = base_unit_name(name)
    for line, members in UNIT_LINES.items():
        if base in members:
            return line
    return "Other units"


def split_unit_types(value):
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [item.strip() for item in str(value or "").split("/") if item.strip()]


def primary_unit_type(value):
    values = split_unit_types(value)
    return values[0] if values else "Uncategorized"


def read_json(path, fallback):
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except Exception:
        return copy.deepcopy(fallback)


def write_json(path, data):
    temp = path + ".tmp"
    with open(temp, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=False)
    os.replace(temp, path)


def relation_names(entries):
    result = []
    for entry in entries or []:
        name = entry.get("unit") if isinstance(entry, dict) else entry
        if name and name not in result:
            result.append(name)
    return result


def relation_entry(name, old_entries=None):
    for entry in old_entries or []:
        if isinstance(entry, dict) and entry.get("unit") == name:
            return copy.deepcopy(entry)
    return {"unit": name, "strength": "Unknown", "reason": ""}


class DataStore:
    def __init__(self):
        os.makedirs(APP_DATA_DIR, exist_ok=True)
        self.paths = {
            "civs": os.path.join(APP_DATA_DIR, "civ_data.json"),
            "units": os.path.join(APP_DATA_DIR, "units_db.json"),
            "strategies": os.path.join(APP_DATA_DIR, "typical_strategies.json"),
            "options": os.path.join(APP_DATA_DIR, "config_options.json"),
        }
        self._seed()
        self.reload()

    def _seed(self):
        for filename, key in (
            ("civ_data.json", "civs"),
            ("units_db.json", "units"),
            ("typical_strategies.json", "strategies"),
        ):
            target = self.paths[key]
            source = os.path.join(BUNDLE_DIR, filename)
            if not os.path.exists(target) and os.path.exists(source):
                shutil.copy2(source, target)

    def reload(self):
        self.civs = read_json(self.paths["civs"], {})
        self.units = read_json(self.paths["units"], {})
        self.strategies = read_json(self.paths["strategies"], {})
        self.options = read_json(self.paths["options"], {
            "custom_lines": [], "custom_types": [], "hidden_lines": [], "hidden_types": []
        })

    def backup(self):
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        folder = os.path.join(APP_DATA_DIR, "backups", stamp)
        os.makedirs(folder, exist_ok=True)
        for path in self.paths.values():
            if os.path.exists(path):
                shutil.copy2(path, os.path.join(folder, os.path.basename(path)))
        return folder

    def save_all(self):
        backup = self.backup()
        write_json(self.paths["civs"], self.civs)
        write_json(self.paths["units"], self.units)
        write_json(self.paths["strategies"], self.strategies)
        write_json(self.paths["options"], self.options)
        return backup

    def line_options(self):
        values = set(UNIT_LINES) | {"Other units"} | set(self.options.get("custom_lines", []))
        values.update(data.get("configLine") for data in self.units.values() if data.get("configLine"))
        return sorted(values - set(self.options.get("hidden_lines", [])))

    def type_options(self):
        values = set(UNIT_TYPE_OPTIONS) | set(self.options.get("custom_types", []))
        for data in self.units.values():
            values.update(split_unit_types(data.get("unitType", "")))
        return sorted(values - set(self.options.get("hidden_types", [])))

    def add_option(self, kind, value):
        key = "custom_lines" if kind == "line" else "custom_types"
        hidden = "hidden_lines" if kind == "line" else "hidden_types"
        self.options.setdefault(key, [])
        self.options.setdefault(hidden, [])
        if value not in self.options[key]:
            self.options[key].append(value)
        if value in self.options[hidden]:
            self.options[hidden].remove(value)

    def delete_option(self, kind, value):
        key = "custom_lines" if kind == "line" else "custom_types"
        hidden = "hidden_lines" if kind == "line" else "hidden_types"
        self.options.setdefault(key, [])
        self.options.setdefault(hidden, [])
        if value in self.options[key]:
            self.options[key].remove(value)
        if value not in self.options[hidden]:
            self.options[hidden].append(value)
        if kind == "line":
            for data in self.units.values():
                if data.get("configLine") == value:
                    data["configLine"] = "Other units"
        else:
            for data in self.units.values():
                types = [item for item in split_unit_types(data.get("unitType", "")) if item != value]
                data["unitType"] = " / ".join(types)

    def all_category_units(self):
        result = {category: set() for category in CATEGORIES}
        for civ in self.civs.values():
            for category, values in (civ.get("unitsAvailable") or {}).items():
                result.setdefault(category, set()).update(values.keys())
            for category, values in (civ.get("unique_units_by_category") or {}).items():
                result.setdefault(category, set()).update(values)
        for unit, data in self.units.items():
            category = data.get("configCategory")
            if category:
                result.setdefault(category, set()).add(unit)
        return {key: sorted(value) for key, value in result.items()}

    def new_civ(self, name):
        roster = self.all_category_units()
        self.civs[name] = {
            "civName": name,
            "civSummary": "",
            "civWeakness": "",
            "civStrength": "",
            "civStrategy": "",
            "civTeamBonus": "",
            "unitsAvailable": {
                category: {unit: False for unit in roster.get(category, [])}
                for category in CATEGORIES
            },
            "unique_units_by_category": {},
        }
        self.strategies[name] = {
            "summary": "", "typical_strategies": [], "notes": ""
        }

    def ensure_unit(self, name, category=None):
        if name not in self.units:
            self.units[name] = {
                "unitDescription": "", "unitType": "", "cost": "",
                "strong_vs": [], "countered_by": [],
            }
        if category:
            self.units[name]["configCategory"] = category
            for civ in self.civs.values():
                civ.setdefault("unitsAvailable", {}).setdefault(category, {}).setdefault(name, False)

    def set_relationships(self, unit_name, strong_names, weak_names):
        self.ensure_unit(unit_name)
        strong_names = {name for name in strong_names if name != unit_name}
        weak_names = {name for name in weak_names if name != unit_name}
        for name in strong_names | weak_names:
            self.ensure_unit(name)

        # Remove every old edge involving this unit from both representations.
        for other_name, data in self.units.items():
            if other_name == unit_name:
                continue
            data["strong_vs"] = [
                e for e in data.get("strong_vs", [])
                if (e.get("unit") if isinstance(e, dict) else e) != unit_name
            ]
            data["countered_by"] = [
                e for e in data.get("countered_by", [])
                if (e.get("unit") if isinstance(e, dict) else e) != unit_name
            ]

        current = self.units[unit_name]
        old_strong = current.get("strong_vs", [])
        old_weak = current.get("countered_by", [])
        current["strong_vs"] = [relation_entry(n, old_strong) for n in sorted(strong_names)]
        current["countered_by"] = [relation_entry(n, old_weak) for n in sorted(weak_names)]

        # A strong against B is exactly B weak against A, and vice versa.
        for target in strong_names:
            entries = self.units[target].setdefault("countered_by", [])
            if unit_name not in relation_names(entries):
                entries.append(relation_entry(unit_name))
        for attacker in weak_names:
            entries = self.units[attacker].setdefault("strong_vs", [])
            if unit_name not in relation_names(entries):
                entries.append(relation_entry(unit_name))


class MultiSelectDropdown(QWidget):
    def __init__(self, options, parent=None):
        super().__init__(parent)
        self.options = list(options)
        self.button = QPushButton("Select types...")
        self.menu = QMenu(self.button)
        self.button.setMenu(self.menu)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.button)
        self.set_values([])

    def set_options(self, options):
        selected = [value for value in self.values() if value in options]
        self.options = list(options)
        self.set_values(selected)

    def set_values(self, values):
        selected = set(values)
        self.menu.clear()
        for value in list(dict.fromkeys(self.options + sorted(selected))):
            action = self.menu.addAction(value)
            action.setCheckable(True)
            action.setChecked(value in selected)
            action.toggled.connect(self._update_text)
        self._update_text()

    def values(self):
        return [action.text() for action in self.menu.actions() if action.isChecked()]

    def _update_text(self, _checked=False):
        values = self.values()
        summary = ", ".join(values)
        if len(values) > 3 or len(summary) > 70:
            summary = ", ".join(values[:2]) + f"  (+{len(values) - 2} more)"
        self.button.setText(summary if values else "Select types...")


class CheckList(QWidget):
    def __init__(self, title):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        header = QHBoxLayout()
        header.addWidget(QLabel(title))
        header.addStretch()
        self.sort = QComboBox()
        self.sort.addItems(["Group by type", "Sort by name"])
        header.addWidget(self.sort)
        layout.addLayout(header)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Filter units...")
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.names = []
        self.type_map = {}
        layout.addWidget(self.search)
        layout.addWidget(self.tree)
        self.search.textChanged.connect(self.apply_filter)
        self.sort.currentIndexChanged.connect(self.rebuild)

    def set_items(self, names, checked, type_map=None):
        self.names = list(names)
        self.type_map = type_map or {}
        self._checked_names = set(checked)
        self.rebuild()

    def _unit_item(self, name):
        item = QTreeWidgetItem([name])
        item.setData(0, Qt.UserRole, name)
        item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
        item.setCheckState(0, Qt.Checked if name in self._checked_names else Qt.Unchecked)
        return item

    def rebuild(self):
        if hasattr(self, "tree") and self.tree.topLevelItemCount():
            self._checked_names = set(self.checked())
        self.tree.clear()
        if self.sort.currentIndex() == 0:
            groups = {}
            for name in self.names:
                groups.setdefault(primary_unit_type(self.type_map.get(name, "")), []).append(name)
            for unit_type in sorted(groups):
                parent = QTreeWidgetItem([unit_type])
                parent.setFlags(parent.flags() & ~Qt.ItemIsSelectable)
                self.tree.addTopLevelItem(parent)
                for name in sorted(groups[unit_type]):
                    parent.addChild(self._unit_item(name))
                parent.setExpanded(True)
        else:
            for name in sorted(self.names):
                self.tree.addTopLevelItem(self._unit_item(name))
        self.apply_filter(self.search.text())

    def checked(self):
        values = []
        for i in range(self.tree.topLevelItemCount()):
            top = self.tree.topLevelItem(i)
            items = [top.child(j) for j in range(top.childCount())] if top.childCount() else [top]
            for item in items:
                if item.data(0, Qt.UserRole) and item.checkState(0) == Qt.Checked:
                    values.append(item.data(0, Qt.UserRole))
        return values

    def apply_filter(self, text):
        needle = text.casefold().strip()
        for i in range(self.tree.topLevelItemCount()):
            top = self.tree.topLevelItem(i)
            if top.childCount():
                visible = False
                for j in range(top.childCount()):
                    child = top.child(j)
                    matches = needle in child.text(0).casefold() or needle in top.text(0).casefold()
                    child.setHidden(not matches)
                    visible = visible or matches
                top.setHidden(not visible)
            else:
                top.setHidden(needle not in top.text(0).casefold())


class AddUniqueDialog(QDialog):
    def __init__(self, unit_names, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add unique unit")
        layout = QFormLayout(self)
        self.name = QComboBox()
        self.name.setEditable(True)
        self.name.addItems(sorted(unit_names))
        self.category = QComboBox()
        self.category.addItems(CATEGORIES)
        layout.addRow("Unit name", self.name)
        layout.addRow("Category", self.category)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)


class CivEditor(QWidget):
    def __init__(self, store, changed_callback):
        super().__init__()
        self.store = store
        self.changed_callback = changed_callback
        self.current = None
        root = QVBoxLayout(self)
        toolbar = QHBoxLayout()
        self.search = QLineEdit(); self.search.setPlaceholderText("Find civilization...")
        add = QPushButton("Add civilization")
        save = QPushButton("Save civilization")
        toolbar.addWidget(self.search, 1); toolbar.addWidget(add); toolbar.addWidget(save)
        root.addLayout(toolbar)
        split = QSplitter()
        self.civ_list = QListWidget(); split.addWidget(self.civ_list)
        editor = QTabWidget()
        details_page = QWidget(); details_layout = QVBoxLayout(details_page)
        form = QFormLayout()
        self.name = QLineEdit(); form.addRow("Name", self.name)
        self.fields = {}
        for key, label in TEXT_FIELDS:
            field = QTextEdit(); field.setMinimumHeight(55)
            self.fields[key] = field; form.addRow(label, field)
        self.strategy_summary = QTextEdit(); self.strategy_summary.setMaximumHeight(70)
        self.strategy_plans = QTextEdit(); self.strategy_plans.setMaximumHeight(90)
        self.strategy_notes = QTextEdit(); self.strategy_notes.setMaximumHeight(70)
        form.addRow("Typical strategy summary", self.strategy_summary)
        form.addRow("Typical plans (one per line)", self.strategy_plans)
        form.addRow("Typical strategy notes", self.strategy_notes)
        details_layout.addLayout(form)
        details_layout.addStretch()

        units_page = QWidget(); units_layout = QVBoxLayout(units_page)
        units_layout.addWidget(QLabel(
            "Available units (Category > unit line > unit). Check everything this civilization can make."
        ))
        self.unit_tree = QTreeWidget(); self.unit_tree.setHeaderLabels(["Category / unit line / unit", "Available"])
        self.unit_tree.setMinimumHeight(520)
        self.unit_tree.setColumnWidth(0, 440)
        units_layout.addWidget(self.unit_tree, 5)
        unique_bar = QHBoxLayout(); unique_bar.addWidget(QLabel("Unique units")); unique_bar.addStretch()
        add_unique = QPushButton("Add unique unit"); remove_unique = QPushButton("Remove selected")
        unique_bar.addWidget(add_unique); unique_bar.addWidget(remove_unique)
        units_layout.addLayout(unique_bar)
        self.unique_tree = QTreeWidget(); self.unique_tree.setHeaderLabels(["Category", "Unique unit"])
        self.unique_tree.setMinimumHeight(150)
        units_layout.addWidget(self.unique_tree, 1)
        editor.addTab(details_page, "Civilization details & strategies")
        editor.addTab(units_page, "Units & unique units")
        split.addWidget(editor); split.setStretchFactor(1, 4); root.addWidget(split, 1)
        self.search.textChanged.connect(self.refresh_list)
        self.civ_list.currentTextChanged.connect(self.load_civ)
        add.clicked.connect(self.add_civ); save.clicked.connect(self.save_civ)
        add_unique.clicked.connect(self.add_unique); remove_unique.clicked.connect(self.remove_unique)
        self.refresh_list()

    def refresh_list(self):
        selected = self.current
        needle = self.search.text().casefold()
        self.civ_list.clear()
        for name in sorted(self.store.civs):
            if needle in name.casefold(): self.civ_list.addItem(name)
        matches = self.civ_list.findItems(selected or "", Qt.MatchExactly)
        if matches: self.civ_list.setCurrentItem(matches[0])

    def load_civ(self, name):
        if not name or name not in self.store.civs: return
        self.current = name; civ = self.store.civs[name]
        self.name.setText(name)
        for key, field in self.fields.items(): field.setPlainText(civ.get(key, ""))
        strategy = self.store.strategies.get(name, {})
        self.strategy_summary.setPlainText(strategy.get("summary", "") if isinstance(strategy, dict) else "")
        self.strategy_plans.setPlainText("\n".join(strategy.get("typical_strategies", [])) if isinstance(strategy, dict) else "")
        self.strategy_notes.setPlainText(strategy.get("notes", "") if isinstance(strategy, dict) else "")
        self.unit_tree.clear()
        roster = self.store.all_category_units()
        available = civ.get("unitsAvailable") or {}
        unique_by_category = civ.get("unique_units_by_category") or {}
        for category in CATEGORIES:
            parent = QTreeWidgetItem([category, ""]); self.unit_tree.addTopLevelItem(parent)
            unique_names = set(unique_by_category.get(category, []))
            names = sorted(
                set(roster.get(category, []))
                | set((available.get(category) or {}).keys())
                | unique_names
            )
            grouped = {}
            for unit in names:
                grouped.setdefault(unit_line(unit, self.store.units.get(unit)), []).append(unit)
            configured_lines = sorted(line for line in grouped if line not in UNIT_LINES and line != "Other units")
            line_order = list(UNIT_LINES) + configured_lines + ["Other units"]
            for line in line_order:
                if line not in grouped:
                    continue
                line_item = QTreeWidgetItem([line, ""])
                parent.addChild(line_item)
                for unit in grouped[line]:
                    child = QTreeWidgetItem([unit, ""])
                    child.setData(0, Qt.UserRole, unit)
                    child.setFlags(child.flags() | Qt.ItemIsUserCheckable)
                    is_available = (available.get(category) or {}).get(unit, False) or unit in unique_names
                    child.setCheckState(0, Qt.Checked if is_available else Qt.Unchecked)
                    line_item.addChild(child)
                line_item.setExpanded(category == "Military")
            parent.setExpanded(category == "Military")
        self.unique_tree.clear()
        for category, names in (civ.get("unique_units_by_category") or {}).items():
            for unit in names: self.unique_tree.addTopLevelItem(QTreeWidgetItem([category, unit]))

    def add_civ(self):
        name, ok = self._ask("New civilization", "Civilization name")
        if not ok or not name.strip(): return
        name = name.strip()
        if name in self.store.civs:
            QMessageBox.warning(self, "Already exists", f"{name} already exists."); return
        self.store.new_civ(name); self.current = name; self.refresh_list(); self.load_civ(name)

    def _ask(self, title, label):
        dialog = QDialog(self); dialog.setWindowTitle(title); layout = QFormLayout(dialog)
        edit = QLineEdit(); layout.addRow(label, edit)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept); buttons.rejected.connect(dialog.reject); layout.addRow(buttons)
        return (edit.text(), True) if dialog.exec_() == QDialog.Accepted else ("", False)

    def save_civ(self):
        if not self.current: return
        new_name = self.name.text().strip()
        if not new_name:
            QMessageBox.warning(self, "Name required", "Enter a civilization name."); return
        if new_name != self.current and new_name in self.store.civs:
            QMessageBox.warning(self, "Already exists", f"{new_name} already exists."); return
        civ = self.store.civs[self.current]
        civ["civName"] = new_name
        for key, field in self.fields.items(): civ[key] = field.toPlainText().strip()
        units_available = {}
        for i in range(self.unit_tree.topLevelItemCount()):
            parent = self.unit_tree.topLevelItem(i); category = parent.text(0); values = {}
            for j in range(parent.childCount()):
                line_item = parent.child(j)
                for k in range(line_item.childCount()):
                    child = line_item.child(k)
                    unit = child.data(0, Qt.UserRole) or child.text(0)
                    values[unit] = child.checkState(0) == Qt.Checked
            units_available[category] = values
        civ["unitsAvailable"] = units_available
        unique = {}
        for i in range(self.unique_tree.topLevelItemCount()):
            item = self.unique_tree.topLevelItem(i); unique.setdefault(item.text(0), []).append(item.text(1))
        civ["unique_units_by_category"] = unique
        self.store.strategies[self.current] = {
            "summary": self.strategy_summary.toPlainText().strip(),
            "typical_strategies": [x.strip() for x in self.strategy_plans.toPlainText().splitlines() if x.strip()],
            "notes": self.strategy_notes.toPlainText().strip(),
        }
        if new_name != self.current:
            del self.store.civs[self.current]; self.store.civs[new_name] = civ
            self.store.strategies[new_name] = self.store.strategies.pop(self.current)
            self.current = new_name
        backup = self.store.save_all(); self.changed_callback(); self.refresh_list()
        QMessageBox.information(self, "Saved", f"Civilization saved.\nBackup: {backup}")

    def add_unique(self):
        if not self.current: return
        dialog = AddUniqueDialog(self.store.units, self)
        if dialog.exec_() != QDialog.Accepted: return
        name = dialog.name.currentText().strip(); category = dialog.category.currentText()
        if not name: return
        self.store.ensure_unit(name)
        existing = [self.unique_tree.topLevelItem(i).text(1) for i in range(self.unique_tree.topLevelItemCount())]
        if name not in existing: self.unique_tree.addTopLevelItem(QTreeWidgetItem([category, name]))
        self.changed_callback()

    def remove_unique(self):
        for item in self.unique_tree.selectedItems():
            self.unique_tree.takeTopLevelItem(self.unique_tree.indexOfTopLevelItem(item))


class UnitEditor(QWidget):
    def __init__(self, store, changed_callback):
        super().__init__(); self.store = store; self.changed_callback = changed_callback; self.current = None
        root = QVBoxLayout(self)
        bar = QHBoxLayout(); self.search = QLineEdit(); self.search.setPlaceholderText("Find unit...")
        add = QPushButton("Add unit"); save = QPushButton("Save unit and reciprocal counters")
        bar.addWidget(self.search, 1); bar.addWidget(add); bar.addWidget(save); root.addLayout(bar)
        split = QSplitter(); self.unit_list = QListWidget(); split.addWidget(self.unit_list)
        editor = QWidget(); editor_layout = QVBoxLayout(editor); form = QFormLayout()
        self.name = QLineEdit(); self.unit_type = MultiSelectDropdown(self.store.type_options()); self.cost = QLineEdit(); self.description = QTextEdit()
        self.category = QComboBox(); self.category.addItems(CATEGORIES)
        self.line = QComboBox(); self.line.setEditable(True)
        self.line.addItems(self.store.line_options())
        self.line.setToolTip("Choose an existing upgrade line or type a new line name.")
        line_field = QWidget(); line_layout = QHBoxLayout(line_field); line_layout.setContentsMargins(0, 0, 0, 0)
        add_line = QPushButton("Add"); delete_line = QPushButton("Delete")
        line_layout.addWidget(self.line, 1); line_layout.addWidget(add_line); line_layout.addWidget(delete_line)
        type_field = QWidget(); type_layout = QHBoxLayout(type_field); type_layout.setContentsMargins(0, 0, 0, 0)
        add_type = QPushButton("Add"); delete_type = QPushButton("Delete")
        type_layout.addWidget(self.unit_type, 1); type_layout.addWidget(add_type); type_layout.addWidget(delete_type)
        form.addRow("Name", self.name); form.addRow("Category", self.category)
        form.addRow("Unit line", line_field)
        form.addRow("Type", type_field); form.addRow("Cost", self.cost); form.addRow("Description", self.description)
        editor_layout.addLayout(form)
        relations = QSplitter(); self.strong = CheckList("Strong against"); self.weak = CheckList("Weak against / countered by")
        relations.addWidget(self.strong); relations.addWidget(self.weak); editor_layout.addWidget(relations, 1)
        split.addWidget(editor); split.setStretchFactor(1, 4); root.addWidget(split, 1)
        self.search.textChanged.connect(self.refresh_list); self.unit_list.currentTextChanged.connect(self.load_unit)
        add.clicked.connect(self.add_unit); save.clicked.connect(self.save_unit); self.refresh_list()
        add_line.clicked.connect(self.add_line_option); delete_line.clicked.connect(self.delete_line_option)
        add_type.clicked.connect(self.add_type_option); delete_type.clicked.connect(self.delete_type_option)

    def refresh_option_controls(self):
        current_line = self.line.currentText()
        self.line.clear(); self.line.addItems(self.store.line_options())
        self.line.setCurrentText(current_line if current_line in self.store.line_options() else "Other units")
        self.unit_type.set_options(self.store.type_options())

    def add_line_option(self):
        value, ok = QInputDialog.getText(self, "Add unit line", "New unit line name")
        value = value.strip()
        if not ok or not value:
            return
        self.store.add_option("line", value)
        self.store.save_all()
        self.refresh_option_controls()
        self.line.setCurrentText(value)

    def delete_line_option(self):
        value = self.line.currentText().strip()
        if not value:
            return
        if value in UNIT_LINES or value == "Other units":
            QMessageBox.information(self, "Core unit line", "Built-in unit lines cannot be deleted.")
            return
        if QMessageBox.question(
            self, "Delete unit line",
            f"Delete '{value}' globally? Units using it will move to Other units.",
            QMessageBox.Yes | QMessageBox.No,
        ) != QMessageBox.Yes:
            return
        self.store.delete_option("line", value)
        self.store.save_all()
        self.refresh_option_controls()
        self.line.setCurrentText("Other units")

    def add_type_option(self):
        value, ok = QInputDialog.getText(self, "Add unit type", "New unit type name")
        value = value.strip()
        if not ok or not value:
            return
        self.store.add_option("type", value)
        self.store.save_all()
        selected = self.unit_type.values()
        self.unit_type.set_options(self.store.type_options())
        self.unit_type.set_values(selected + [value])

    def delete_type_option(self):
        options = self.store.type_options()
        value, ok = QInputDialog.getItem(self, "Delete unit type", "Unit type", options, 0, False)
        if not ok or not value:
            return
        if value in UNIT_TYPE_OPTIONS:
            QMessageBox.information(self, "Core unit type", "Built-in unit types cannot be deleted.")
            return
        if QMessageBox.question(
            self, "Delete unit type",
            f"Delete '{value}' globally? It will be removed from every unit using it.",
            QMessageBox.Yes | QMessageBox.No,
        ) != QMessageBox.Yes:
            return
        self.store.delete_option("type", value)
        self.store.save_all()
        self.unit_type.set_options(self.store.type_options())

    def refresh_list(self):
        selected = self.current; needle = self.search.text().casefold(); self.unit_list.clear()
        for name in sorted(self.store.units):
            if needle in name.casefold(): self.unit_list.addItem(name)
        matches = self.unit_list.findItems(selected or "", Qt.MatchExactly)
        if matches: self.unit_list.setCurrentItem(matches[0])

    def inferred_category(self, name):
        explicit = self.store.units.get(name, {}).get("configCategory")
        if explicit in CATEGORIES: return explicit
        for civ in self.store.civs.values():
            for category, units in (civ.get("unitsAvailable") or {}).items():
                if name in units: return category
            for category, units in (civ.get("unique_units_by_category") or {}).items():
                if name in units: return category
        return "Castle Units"

    def load_unit(self, name):
        if not name or name not in self.store.units: return
        self.current = name; data = self.store.units[name]; self.name.setText(name)
        self.unit_type.set_values(split_unit_types(data.get("unitType", ""))); self.cost.setText(data.get("cost", ""))
        self.description.setPlainText(data.get("unitDescription", ""))
        self.category.setCurrentText(self.inferred_category(name))
        self.line.setCurrentText(unit_line(name, data))
        others = sorted(n for n in self.store.units if n != name)
        type_map = {unit: self.store.units[unit].get("unitType", "") for unit in others}
        self.strong.set_items(others, relation_names(data.get("strong_vs")), type_map)
        self.weak.set_items(others, relation_names(data.get("countered_by")), type_map)

    def add_unit(self):
        self.current = None; self.name.clear(); self.unit_type.set_values([]); self.cost.clear(); self.description.clear()
        self.category.setCurrentIndex(0); self.line.setCurrentText("Other units"); names = sorted(self.store.units)
        type_map = {unit: self.store.units[unit].get("unitType", "") for unit in names}
        self.strong.set_items(names, [], type_map); self.weak.set_items(names, [], type_map); self.name.setFocus()

    def save_unit(self):
        name = self.name.text().strip()
        if not name: QMessageBox.warning(self, "Name required", "Enter a unit name."); return
        if self.current and name != self.current:
            QMessageBox.warning(self, "Rename not supported", "Create a new unit instead of renaming an existing one."); return
        is_new = name not in self.store.units
        self.store.ensure_unit(name, self.category.currentText() if is_new else None)
        data = self.store.units[name]; data["configCategory"] = self.category.currentText()
        data["configLine"] = self.line.currentText().strip() or "Other units"
        data["unitType"] = " / ".join(self.unit_type.values()); data["cost"] = self.cost.text().strip()
        data["unitDescription"] = self.description.toPlainText().strip()
        self.store.set_relationships(name, self.strong.checked(), self.weak.checked())
        self.current = name; backup = self.store.save_all(); self.changed_callback(); self.refresh_list(); self.load_unit(name)
        QMessageBox.information(self, "Saved", f"Unit and reciprocal relationships saved.\nBackup: {backup}")


class ConfigDuck(QMainWindow):
    def __init__(self):
        super().__init__(); self.store = DataStore()
        self.setWindowTitle("Config Duck v1.1.16")
        icon = os.path.join(BUNDLE_DIR, "duck.ico")
        if os.path.exists(icon): self.setWindowIcon(QIcon(icon))
        self.setMinimumSize(1100, 850)
        self.resize(1280, 1000)
        tabs = QTabWidget(); self.setCentralWidget(tabs)
        self.civ_editor = CivEditor(self.store, self.data_changed)
        self.unit_editor = UnitEditor(self.store, self.data_changed)
        tabs.addTab(self.civ_editor, "Civilizations")
        tabs.addTab(self.unit_editor, "Units and counters")
        self.statusBar().showMessage(f"Editing shared Age of Duck data: {APP_DATA_DIR}")

    def data_changed(self):
        self.unit_editor.refresh_list()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Config Duck")
    window = ConfigDuck(); window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
