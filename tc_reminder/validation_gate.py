"""Approval is tied to reviewed screenshot calibration, not a user checkbox."""
import hashlib
import json
from .paths import ROOT

ALGORITHM_VERSION = '2026-09-30-tc-allowlist-overlay-v4'

def fingerprint():
    h=hashlib.sha256(ALGORITHM_VERSION.encode())
    for name in ('calibration.json','clock-calibration.json','population-glyphs.json'):
        h.update((ROOT/name).read_bytes())
    p=json.loads((ROOT/'calibration.json').read_text())
    for template in p['templates']:
        h.update((ROOT/template['file']).read_bytes())
    return h.hexdigest()

def approved():
    try:
        a=json.loads((ROOT/'validation-approval.json').read_text())
        return a.get('approved') is True and a.get('fingerprint')==fingerprint()
    except (OSError,ValueError,KeyError):
        return False
