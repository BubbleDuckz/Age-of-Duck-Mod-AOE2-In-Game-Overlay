"""Generate unit_counters_v2.json from techtree_data.json.

Every unit description from aoe2techtree.net states what the unit is weak and
strong against ("Weak vs. Spearman-line, Camel Riders and Monks"). This script
turns those class names into concrete unit lines, so the overlay can answer
"what can *my* civilization build to counter this unit?" without hand-written
per-unit lists.

Output layout:
  classes: class name -> list of lines; a line is its upgrade chain, weakest first.
  units:   unit name  -> {"line", "weak_vs": [class names], "strong_vs": [class names]}
  lines:   line key   -> upgrade chain (also used to group the Available Units browser)
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# Generic upgrade chains. Anything not listed becomes a line of its own, and
# unique units are paired with their Elite upgrade automatically.
CHAINS = [
    ["Militia", "Man-at-Arms", "Long Swordsman", "Two-Handed Swordsman", "Champion"],
    ["Spearman", "Pikeman", "Halberdier"],
    ["Eagle Scout", "Eagle Warrior", "Elite Eagle Warrior"],
    ["Archer", "Crossbowman", "Arbalester"],
    ["Skirmisher", "Elite Skirmisher", "Imperial Skirmisher"],
    ["Cavalry Archer", "Heavy Cavalry Archer"],
    ["Scout Cavalry", "Light Cavalry", "Hussar", "Winged Hussar"],
    ["Knight", "Cavalier", "Paladin"],
    ["Camel Rider", "Heavy Camel Rider", "Imperial Camel Rider"],
    ["Steppe Lancer", "Elite Steppe Lancer"],
    ["Battle Elephant", "Elite Battle Elephant"],
    ["Battering Ram", "Capped Ram", "Siege Ram"],
    ["Mangonel", "Onager", "Siege Onager"],
    ["Scorpion", "Heavy Scorpion"],
    ["Galley", "War Galley", "Galleon"],
    ["Fire Galley", "Fire Ship", "Fast Fire Ship"],
    ["Demolition Raft", "Demolition Ship", "Heavy Demo Ship"],
    ["Hulk", "War Hulk", "Carrack"],
    ["Cannon Galleon", "Elite Cannon Galleon"],
    ["Composite Bowman", "E. Composite Bowman"],
]

NOT_COUNTER_UNITS = {
    "Villager", "Trade Cart", "Trade Cog", "Fishing Ship", "Transport Ship",
    "Liu Bei", "Cao Cao", "Sun Jian",
}

# These common units have no generic upgrade chain, but are not civilisation-unique.
GENERIC_SINGLE_UNITS = {"Monk", "Hand Cannoneer", "Bombard Cannon", "Trebuchet", "Siege Tower", "Petard"}


def first_sentence(text):
    first = re.split(r"(?<=\.)\s", text)[0]
    return re.sub(r"^(?:\w+ )?unique ", "", first, flags=re.I)


def tags_for(name, unit):
    first = first_sentence(unit["unitDescription"])
    low = re.sub(r"anti-\w+", "", first.lower())
    buildings = set(unit["buildings"])
    tags = set()
    if "foot archer" in low:
        tags |= {"foot_archer", "archery"}
    if "mounted archer" in low:
        tags |= {"mounted_archer", "archery"}
    if "skirmisher" in low:
        tags |= {"skirmisher", "archery"}
    if "gunner" in low or "gunpowder shock infantry" in low:
        tags.add("gunner")
    if "Archery Range" in buildings:
        tags.add("archery")
    if "siege" in low or "Siege Workshop" in buildings:
        tags.add("siege")
    if "monk" in low or name in ("Monk", "Missionary", "Warrior Priest"):
        tags.add("monk")
    if "infantry" in low and "siege" not in low:
        tags.add("infantry")
    if "cavalry" in low and not {"mounted_archer", "siege"} & tags and "hero" not in low:
        tags.add("cavalry")
    if "Stable" in buildings and "siege" not in tags and "mounted_archer" not in tags:
        tags.add("cavalry")
    if "warship" in low or "Dock" in buildings:
        tags.add("ship")
    if {"infantry", "cavalry"} & tags and not {"archery", "gunner", "siege", "monk", "ship"} & tags:
        tags.add("melee")
    if "ranged melee" in low or "throws" in low:
        tags.add("melee")
    if {"archery", "gunner", "mounted_archer"} & tags:
        tags.add("ranged")
    return tags


GROUP_ORDER = ["Infantry", "Archers", "Cav. Archers", "Cavalry", "Gunpowder", "Siege", "Monks", "Ships", "Other"]


def group_for(tags):
    """Row label used by the Available Units browser for units outside the standard lines."""
    if "siege" in tags:
        return "Siege"
    if "gunner" in tags:
        return "Gunpowder"
    if "monk" in tags:
        return "Monks"
    if "ship" in tags:
        return "Ships"
    if "mounted_archer" in tags:
        return "Cav. Archers"
    if "archery" in tags:
        return "Archers"
    if "cavalry" in tags:
        return "Cavalry"
    if "infantry" in tags:
        return "Infantry"
    return "Other"


def main():
    catalog = json.loads((ROOT / "techtree_data.json").read_text(encoding="utf-8"))
    units = catalog["units"]
    source_units = json.loads((ROOT / "techtree_source/data.json").read_text(encoding="utf-8"))['data']['Unit']

    line_of, line_members = {}, {}
    for chain in CHAINS:
        members = [name for name in chain if name in units]
        for name in members:
            line_of[name] = members[0]
        line_members[members[0]] = members
    for name in units:
        if name in line_of:
            continue
        base = re.sub(r"^(Elite |E\. |Heavy |H\. )", "", name)
        key = base if base != name and base in units and base not in line_of or base in line_members else name
        line_of[name] = key
        members = line_members.setdefault(key, [])
        if key not in members and key in units:
            members.insert(0, key)
        if name not in members:
            members.append(name)

    tags = {name: tags_for(name, unit) for name, unit in units.items()}

    def lines_where(predicate):
        keys = []
        for key, members in line_members.items():
            if members[0] in NOT_COUNTER_UNITS:
                continue
            if any(predicate(m) for m in members):
                keys.append(key)
        generic = [k for k in keys if k in {c[0] for c in CHAINS}]
        unique = [k for k in keys if k not in generic]
        return [line_members[k] for k in generic + sorted(unique)]

    def named(*names):
        wanted = set(names)
        return lambda unit: unit in wanted

    def tagged(*wanted):
        return lambda unit: bool(set(wanted) & tags[unit])

    classes = {
        "Spearman-line": named("Spearman", "Pikeman", "Halberdier"),
        "Camel Riders": named("Camel Rider", "Heavy Camel Rider", "Imperial Camel Rider"),
        "Archery Units": tagged("archery"),
        "Cavalry": tagged("cavalry"),
        "Skirmishers": tagged("skirmisher"),
        "Monks": tagged("monk"),
        "Siege Weapons": tagged("siege"),
        "Ranged Soldiers": tagged("ranged"),
        "Ranged Soldiers at long range": tagged("ranged"),
        "Militia-line": named("Militia", "Man-at-Arms", "Long Swordsman", "Two-Handed Swordsman", "Champion"),
        "Gunners": tagged("gunner"),
        "Foot Archers": tagged("foot_archer"),
        "Foot Archers at long range": tagged("foot_archer"),
        "Infantry": tagged("infantry"),
        "Mangonel-line": named("Mangonel", "Onager", "Siege Onager"),
        "Fire Ships": named("Fire Galley", "Fire Ship", "Fast Fire Ship"),
        "Galleys": named("Galley", "War Galley", "Galleon"),
        "Galley-line": named("Galley", "War Galley", "Galleon"),
        "Scorpions": named("Scorpion", "Heavy Scorpion"),
        "Hulk-line": named("Hulk", "War Hulk", "Carrack"),
        "Scout Cavalry-line": named("Scout Cavalry", "Light Cavalry", "Hussar", "Winged Hussar"),
        "Eagle Warriors": named("Eagle Scout", "Eagle Warrior", "Elite Eagle Warrior"),
        "Mounted Archers": tagged("mounted_archer"),
        "Demolition Ships": named("Demolition Raft", "Demolition Ship", "Heavy Demo Ship"),
        "units at close range": tagged("melee"),
        "melee units": tagged("melee"),
    }
    class_lines = {label: lines_where(predicate) for label, predicate in classes.items()}

    # ---- the other direction: which classes does a unit belong to, and what is it "Strong vs."? ----
    generic_lines = {chain[0] for chain in CHAINS}

    def is_unique(unit):
        return (line_of[unit] not in generic_lines and unit not in NOT_COUNTER_UNITS
                and unit not in GENERIC_SINGLE_UNITS)

    camels = named("Camel Rider", "Heavy Camel Rider", "Imperial Camel Rider")
    membership = dict(classes)
    membership.update({
        # Mounted archers carry cavalry armour too, so "Strong vs. Cavalry" applies to them.
        "Cavalry": lambda unit: bool({"cavalry", "mounted_archer"} & tags[unit]),
        "Mounted Units": lambda unit: bool({"cavalry", "mounted_archer"} & tags[unit]) or camels(unit),
        "Gunpowder Units": tagged("gunner"),
        "Warships": tagged("ship"),
        # Samurai's unique-unit bonus targets armour class 19, not every civ-exclusive unit.
        "Unique Units": lambda unit: any(a['Class']==19 for a in
            source_units.get(str(units[unit]['id']),{}).get('Armours',[])),
    })
    member_of = {name: [label for label, predicate in membership.items() if predicate(name)] for name in units}

    STRONG_CLASSES = {
        "cavalry": "Cavalry", "mounted units": "Mounted Units", "infantry": "Infantry",
        "archery units": "Archery Units", "foot archers": "Foot Archers", "ranged soldiers": "Ranged Soldiers",
        "siege weapons": "Siege Weapons", "gunpowder units": "Gunpowder Units", "camel riders": "Camel Riders",
        "spearman-line": "Spearman-line", "skirmisher-line": "Skirmishers", "skirmishers": "Skirmishers",
        "scout cavalry-line": "Scout Cavalry-line", "monks": "Monks", "monastery units": "Monks",
        "units at close range": "units at close range", "melee units": "melee units",
        "units at long range": "Ranged Soldiers", "units at range": "Ranged Soldiers",
        "units at medium and close range": "Ranged Soldiers",
        "fire ships": "Fire Ships", "galley-line": "Galley-line", "hulk-line": "Hulk-line",
        "mounted archers": "Mounted Archers",
        "most warships": "Warships", "large groups of ships": "Warships", "unique units": "Unique Units",
    }
    # Tokens that describe situations or targets that are not a unit class (buildings, crowds ...).
    NOT_A_CLASS = ("buildings", "building", "tight groups", "large groups of units", "slow", "land units",
                   "fire galleys", "non-ranged", "units at long range", "groups of units")

    def parse_strong(description):
        """Class names from 'Strong vs. ...'; second value lists tokens that match no class."""
        classes_found, unmatched = [], []
        # "Strong vs. X." and also "Exceptionally strong vs. Y." (many unique units use the latter).
        for match in re.finditer(r"(?i)strong vs\.?\s*(.*?)(?:\.\s|\.$|$)", description):
            text = match.group(1)
            text = text.replace("units at medium and close range", "units at range")
            text = text.replace("Scout Cavalry- and Skirmisher-line", "Scout Cavalry-line, Skirmisher-line")
            text = re.sub(r",?\s*especially.*$", "", text)
            for part in re.split(r",\s*(?:and\s+)?|\s+and\s+", text):
                key = part.strip().lower()
                if not key:
                    continue
                if key in STRONG_CLASSES:
                    if STRONG_CLASSES[key] not in classes_found:
                        classes_found.append(STRONG_CLASSES[key])
                elif not any(key.startswith(prefix) for prefix in NOT_A_CLASS):
                    unmatched.append(part.strip())
        return classes_found, unmatched

    audit = {}

    def parse(description, marker):
        match = re.search(marker + r"\s*(.*?)(?:\.\s|\.$|$)", description)
        if not match:
            return []
        found = []
        for part in re.split(r",\s*(?:and\s+)?|\s+and\s+", match.group(1)):
            label = part.strip().replace("Foot Archers", "Foot Archers")
            label = re.sub(r"\s+(?:and\s+)?especially.*$", "", label)
            if label:
                found.append(label)
        return found

    out_units = {}
    for name, unit in units.items():
        description = unit["unitDescription"]
        weak = [c for c in parse(description, r"Weak vs\.?") if c in class_lines]
        strong, unmatched = parse_strong(description)
        if unmatched:
            audit[name] = unmatched
        out_units[name] = {"line": line_of[name], "group": group_for(tags[name]), "unique": is_unique(name),
                           "weak_vs": weak, "strong_vs": strong, "member_of": member_of[name],
                           "attack_range": source_units.get(str(unit['id']),{}).get('Range',0)}

    result = {
        "metadata": {
            "description": "Counter classes derived from the 'Weak vs.' text of each unit description (aoe2techtree.net).",
            "source_data_sha256": catalog.get("metadata", {}).get("data_sha256", ""),
            "class_count": len(class_lines),
            "unit_count": len(out_units),
        },
        "group_order": GROUP_ORDER,
        "line_order": [chain[0] for chain in CHAINS],
        "lines": {key: members for key, members in line_members.items()},
        "classes": class_lines,
        "units": out_units,
    }
    (ROOT / "unit_counters_v2.json").write_text(json.dumps(result, indent=1, ensure_ascii=False), encoding="utf-8")
    print("classes:", {k: len(v) for k, v in class_lines.items()})
    if audit:
        print("strong-vs text that matches no unit class:", audit)
    print("units with weak_vs:", sum(1 for u in out_units.values() if u["weak_vs"]), "of", len(out_units))


if __name__ == "__main__":
    main()

