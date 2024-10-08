import os
import shutil
import subprocess
import sys

from typing import List, Tuple

if sys.platform == "win32":
    DATA_PATH = os.path.join(os.environ["APPDATA"], "Pagalbukas-Analizatorius")
else:
    config_dir = os.path.join(os.environ["HOME"], ".config")
    if not os.path.exists(config_dir):
        os.mkdir(config_dir)
    DATA_PATH = os.path.join(config_dir, "pagalbukas-analizatorius")
    del config_dir

TEMP_PATH = os.path.join(DATA_PATH, "temp")

if "__compiled__" in dir():
    EXECUTABLE_PATH = os.curdir
else:
    EXECUTABLE_PATH = os.path.dirname(os.path.realpath(__file__))

IGNORED_ITEMS_SOURCE_PATH = os.path.join(EXECUTABLE_PATH, 'data', 'ignoruoti_dalykai.txt')
IGNORED_ITEMS_TARGET_PATH = os.path.join(DATA_PATH, "ignoruoti_dalykai.txt")

def get_data_dir() -> str:
    if not os.path.exists(DATA_PATH):
        os.mkdir(DATA_PATH)
    return DATA_PATH

def get_home_dir() -> str:
    """Returns home directory for the current platform."""
    if sys.platform == "win32":
        return os.environ["USERPROFILE"]
    return os.environ["HOME"]

def get_temp_dir() -> str:
    if not os.path.exists(TEMP_PATH):
        os.mkdir(TEMP_PATH)
    return TEMP_PATH

def get_log_file() -> str:
    return os.path.join(get_data_dir(), "log.log")

def copy_config_to_data() -> None:

    # Force creation of the data directory
    _ = get_data_dir()

    if not os.path.exists(IGNORED_ITEMS_SOURCE_PATH):
        return

    if not os.path.exists(IGNORED_ITEMS_TARGET_PATH):
        shutil.copy(IGNORED_ITEMS_SOURCE_PATH, IGNORED_ITEMS_TARGET_PATH)

def get_ignored_item_filters() -> List[Tuple[int, str]]:
    copy_config_to_data()
    if not os.path.exists(IGNORED_ITEMS_TARGET_PATH):
        return []

    filters: List[Tuple[int, str]] = []
    with open(IGNORED_ITEMS_TARGET_PATH, "r", encoding="utf-8") as f:
        while line := f.readline():
            string = line.rstrip()

            if string == "" or None:
                continue

            val = 1
            if string.endswith("*"):
                string = string[:-1]
                val |= 1 << 1
            if string.startswith("*"):
                string = string[1:]
                val |= 1 << 2

            filters.append((val, string))
    return filters

def open_path(path: str) -> None:
    """Opens the path in a file browser."""
    if sys.platform == "win32":
        return os.startfile(path)
    _ = subprocess.check_call(
        ['xdg-open', path],
        stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT
    )
