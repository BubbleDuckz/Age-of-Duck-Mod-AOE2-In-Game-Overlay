"""Load object-shaped preferences and validate saved pixel dimensions."""
import json
from pathlib import Path

def read_object(path):
    try:
        value=json.loads(Path(path).read_text(encoding='utf-8'))
    except (OSError,ValueError):
        return {}
    return value if isinstance(value,dict) else {}

def valid_size(value):
    return (isinstance(value,(list,tuple)) and len(value)==2
            and all(isinstance(v,int) and not isinstance(v,bool) and v>0 for v in value))

def voice_volume(value,default=100):
    try:return max(0,min(100,int(value)))
    except (TypeError,ValueError,OverflowError):return default
