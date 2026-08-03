import json
import os
from pathlib import Path

_CONFIG_PATH = Path(__file__).parent / "config.json"

def _load():
    with open(_CONFIG_PATH, "r") as f:
        return json.load(f)

CONFIG = _load()

def get(dotted_key: str, default=None):
    """Acceso a config por clave dotted: get('models.agent')"""
    keys = dotted_key.split(".")
    val = CONFIG
    for k in keys:
        if isinstance(val, dict):
            val = val.get(k)
        else:
            return default
        if val is None:
            return default
    return val
