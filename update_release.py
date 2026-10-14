"""Select a newer Windows installer from GitHub release metadata."""
import re

from packaging.version import Version


def select_update(release, current_version):
    if release.get('draft') or release.get('prerelease'):
        return None, None
    latest = (release.get('tag_name') or '').removeprefix('v')
    if not latest or Version(latest) <= Version(current_version):
        return None, None
    for asset in release.get('assets', []):
        name = (asset.get('name') or '').lower()
        url = asset.get('browser_download_url')
        if name.endswith('.exe') and url and (
            'installer' in name or name.endswith('-setup.exe')
            or re.fullmatch(r'ageofduck-setup-v[^/\\]+\.exe', name)
        ):
            return latest, url
    return None, None
