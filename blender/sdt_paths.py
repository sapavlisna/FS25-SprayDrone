"""Cesty mimo projekt: instalace hry a Blender.

Pořadí: proměnná prostředí, pak `local_paths.json` v kořeni projektu ({"FS25_GAME_DIR": "...", "SDT_BLENDER": "..."}),
pak výchozí instalace ze Steamu.
"""
import json
import os

PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOCAL_FILE = os.path.join(PROJECT, "local_paths.json")
DEFAULTS = {
    "FS25_GAME_DIR": r"C:\Program Files (x86)\Steam\steamapps\common\Farming Simulator 25",
    "SDT_BLENDER": "blender",
}


def _local():
    try:
        with open(LOCAL_FILE, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def get(name):
    return os.environ.get(name) or _local().get(name) or DEFAULTS[name]


GAME_DIR = get("FS25_GAME_DIR")
BLENDER = get("SDT_BLENDER")
