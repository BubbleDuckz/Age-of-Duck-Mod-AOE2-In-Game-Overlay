"""Build UnitIcons/ from the unit portraits of a local Age of Empires II: DE install.

The game stores each portrait as widgetui/textures/ingame/units/<picture index>_50730.DDS.
The tech-tree data (techtree_source/trees/*.json) gives every unit's picture_index; units are
joined to techtree_data.json by unit id. Portraits are converted to 64px PNGs plus
UnitIcons/manifest.json (unit name -> file). Run once; the PNGs are bundled with the app.

usage: python fetch_unit_icons.py [path to AoE2DE folder]
"""
import json
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "UnitIcons"
DEFAULT_GAME = Path(r"C:\Program Files (x86)\Steam\steamapps\common\AoE2DE")
SKIP = {"Villager", "Trade Cart", "Trade Cog", "Fishing Ship", "Transport Ship"}
SIZE = 64


def picture_indexes():
    """unit id -> picture_index, from the bundled tech-tree trees."""
    indexes = {}
    for tree in sorted((ROOT / "techtree_source" / "trees").glob("*.json")):
        for node in json.loads(tree.read_text(encoding="utf-8"))["units_techs"]:
            if node.get("use_type") == "Unit" and node.get("picture_index") is not None:
                indexes.setdefault(node["node_id"], node["picture_index"])
    return indexes


def find_portrait(folder, index):
    for suffix in ("DDS", "dds"):
        path = folder / f"{index:03d}_50730.{suffix}"
        if path.exists():
            return path
    return None


def main():
    game = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_GAME
    source = game / "widgetui" / "textures" / "ingame" / "units"
    OUT.mkdir(exist_ok=True)
    catalog = json.loads((ROOT / "techtree_data.json").read_text(encoding="utf-8"))
    indexes = picture_indexes()
    manifest, missing = {}, []
    for name, unit in catalog["units"].items():
        if name in SKIP:
            continue
        dds = find_portrait(source, indexes[unit["id"]]) if unit["id"] in indexes else None
        try:
            image = Image.open(dds).convert("RGBA")
            image = image.resize((SIZE, SIZE), Image.LANCZOS)
        except Exception:
            missing.append(name)
            continue
        # Named by picture index so units sharing a portrait (X / Elite X) share one file.
        file_name = f"{indexes[unit['id']]:03d}.png"
        image.save(OUT / file_name, optimize=True)
        manifest[name] = file_name
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=1, ensure_ascii=False), encoding="utf-8")
    print("converted", len(manifest), "missing", missing)


if __name__ == "__main__":
    main()
