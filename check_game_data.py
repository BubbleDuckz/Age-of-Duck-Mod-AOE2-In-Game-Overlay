"""Validate bundled game data and portraits without Qt or a game installation."""
import argparse
import hashlib
import json
from pathlib import Path

ECONOMY = {'Villager', 'Trade Cart', 'Trade Cog', 'Fishing Ship', 'Transport Ship'}


def validate_data(source, catalog, counters, portraits, source_hash, files):
    errors = []
    if catalog.get('metadata', {}).get('data_sha256') != source_hash:
        errors.append('Catalog source hash differs from techtree_source/data.json; rebuild the catalog.')
    if counters.get('metadata', {}).get('source_data_sha256') != source_hash:
        errors.append('Counter source hash differs from techtree_source/data.json; rebuild counters.')
    if set(source['civs']) != set(catalog['civs']):
        errors.append('Source and catalog civilisation sets differ.')
    units = catalog['units']
    counter_units = counters['units']
    if set(units) != set(counter_units):
        errors.append('Catalog and counter unit sets differ.')
    for civ, data in catalog['civs'].items():
        if 'CivIcons/' + civ + '_AoE2.webp' not in files:
            errors.append(civ + ': missing civilisation emblem')
        for group in data['unitsAvailable'].values():
            for name, available in group.items():
                if available and name not in units:
                    errors.append(civ + ': available unit missing from catalog: ' + name)
    for name, unit in units.items():
        if not unit.get('unitDescription', '').strip():
            errors.append(name + ': empty description')
        if name not in ECONOMY:
            file = portraits.get(name)
            if not file or 'UnitIcons/' + file not in files:
                errors.append(name + ': missing unit portrait')
    memberships = {label for unit in counter_units.values() for label in unit.get('member_of', [])}
    for name, unit in counter_units.items():
        line = unit.get('line')
        if name not in counters['lines'].get(line, []):
            errors.append(name + ': counter upgrade line is missing or does not contain the unit')
        for label in unit.get('weak_vs', []):
            if label not in counters['classes']:
                errors.append(name + ': unknown weakness class: ' + label)
        # Strength classes match member_of; some have no weak_vs upgrade-chain entry.
        for label in unit.get('strong_vs', []):
            if label not in memberships:
                errors.append(name + ': strength class has no target members: ' + label)
    for line, members in counters['lines'].items():
        for name in members:
            if name not in units:
                errors.append(line + ': upgrade line refers to unknown unit: ' + name)
    for label, chains in counters['classes'].items():
        for chain in chains:
            for name in chain:
                if name not in units:
                    errors.append(label + ': counter class refers to unknown unit: ' + name)
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parent)
    root = parser.parse_args().root
    try:
        raw = (root / 'techtree_source/data.json').read_bytes()
        def read(path):
            return json.loads((root / path).read_text(encoding='utf-8'))
        errors = validate_data(json.loads(raw), read('techtree_data.json'),
                               read('unit_counters_v2.json'), read('UnitIcons/manifest.json'),
                               hashlib.sha256(raw).hexdigest(),
                               {p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()})
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        print('Cannot validate game data:', exc)
        return 1
    for error in errors:
        print(error)
    if not errors:
        print('Catalog, counters, source hashes and portrait references are consistent.')
    return int(bool(errors))


if __name__ == '__main__':
    raise SystemExit(main())
