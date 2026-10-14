# Updating game data

Click-for-Counter uses three related artifacts: techtree_data.json,
unit_counters_v2.json and UnitIcons/manifest.json. Regenerate them together when
updating the saved source snapshot, rather than editing generated entries by hand.

1. Obtain a compatible English source snapshot from the Siege Engineers
   aoe2techtree project (https://github.com/SiegeEngineers/aoe2techtree).
   Update techtree_source/data.json, strings.json and trees/*.json as a set.
   Each civilisation in data.json must have its corresponding tree file.
   Record the upstream revision and game patch in the contribution description;
   do not mix files from different revisions. The current generator depends on
   the existing JSON schema and English description markers such as "Weak vs.".
2. Rebuild in this order, from the project directory:

   ```bat
   python build_techtree_data.py
   python build_counters_data.py
   ```

   Inspect missing-description output and unmatched counter-class text. A new
   unit class may need an explicit mapping in build_counters_data.py. Counters
   are class-based advice derived from descriptions, not a combat simulation.
3. When new portraits are required, regenerate them from a local game install:

   ```bat
   python fetch_unit_icons.py "C:\Program Files (x86)\Steam\steamapps\common\AoE2DE"
   ```

   Inspect the missing-portrait list and add civilisation emblems if needed.
   Review NOTICE.md and CONTRIBUTING.md before submitting game artwork; only
   contribute assets you have the right to share. Keep source attribution and
   techtree_source/LICENSE.
4. Check cross-file integrity without Qt or a game installation:

   ```bat
   python check_game_data.py
   python -m unittest test_game_data
   ```

   This checks source hashes, civilisation/unit coverage, upgrade lines, counter
   classes, descriptions and portrait file references. With requirements installed,
   also run the existing UI coverage tests on Windows:

   ```bat
   python -m unittest test_civ_coverage test_techtree_catalog
   ```

5. Review the generated diff and inspect changed civilisations in the overlay.
   Check both available units and the counters filtered to your own civilisation.
   Include the source revision, generation commands and validation results in the PR.

The catalog's retrieved_utc is currently written at generation time; it does
not independently establish the upstream snapshot's age. Source hashes detect
mixed generated/source artifacts, but cannot establish that the snapshot matches
the latest game patch. Missing descriptions or unmatched class text still need
human review even when the integrity check passes.
