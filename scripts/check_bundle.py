"""Check the onedir EXE and spec-declared data, without launching the application."""
import argparse
import ast
import hashlib
from pathlib import Path


def data_entries(project):
    tree = ast.parse((project / 'AgeOfDuck.spec').read_text(encoding='utf-8'))
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == 'Analysis':
            return ast.literal_eval(next(k.value for k in node.keywords if k.arg == 'datas'))
    raise ValueError('No Analysis datas list found in AgeOfDuck.spec')


def digest(path):
    return hashlib.sha256(path.read_bytes()).digest()


def check_bundle(project, bundle):
    errors = []
    if not (bundle / 'AgeOfDuck.exe').is_file():
        errors.append('Missing AgeOfDuck.exe')
    # PyInstaller 6 puts support files under _internal; older onedir builds use the root.
    assets = bundle / '_internal' if (bundle / '_internal').is_dir() else bundle
    for pattern, destination in data_entries(project):
        sources = list(project.glob(pattern))
        if not sources:
            errors.append('Source pattern matches no resources: ' + pattern)
        for source in sources:
            if source.is_dir():
                pairs = [(p, assets / destination / p.relative_to(source))
                         for p in source.rglob('*') if p.is_file()]
            else:
                pairs = [(source, assets / destination / source.name)]
            for original, packaged in pairs:
                if not packaged.is_file():
                    errors.append('Missing bundled resource: ' + str(packaged.relative_to(bundle)))
                elif digest(original) != digest(packaged):
                    errors.append('Bundled resource differs from source: ' + str(packaged.relative_to(bundle)))
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('bundle', type=Path)
    args = parser.parse_args()
    errors = check_bundle(Path(__file__).resolve().parents[1], args.bundle)
    for error in errors:
        print(error)
    if not errors:
        print('Windows executable and all spec-declared data are present and match their sources.')
    return bool(errors)


if __name__ == '__main__':
    raise SystemExit(main())
