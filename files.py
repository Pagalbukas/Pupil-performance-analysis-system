import os
import shutil

from typing import List, Tuple

DATA_PATH = os.path.join(os.environ["APPDATA"], "Pagalbukas-Analizatorius")
TEMP_PATH = os.path.join(DATA_PATH, "temp")

IGNORED_ITEMS_SOURCE_PATH = os.path.join(os.curdir, "data", "ignoruoti_dalykai.txt")
IGNORED_ITEMS_TARGET_PATH = os.path.join(DATA_PATH, "ignoruoti_dalykai.txt")

def get_data_dir() -> str:
    if not os.path.exists(DATA_PATH):
        os.mkdir(DATA_PATH)
    return DATA_PATH

def get_temp_dir() -> str:
    if not os.path.exists(TEMP_PATH):
        os.mkdir(TEMP_PATH)
    return TEMP_PATH

def get_log_file() -> str:
    return os.path.join(get_data_dir(), "log.log")

def copy_config_to_data() -> None:

    # Force creation of the data directory
    get_data_dir()

    if not os.path.exists(IGNORED_ITEMS_SOURCE_PATH):
        return

    if not os.path.exists(IGNORED_ITEMS_TARGET_PATH):
        shutil.copy(IGNORED_ITEMS_SOURCE_PATH, IGNORED_ITEMS_TARGET_PATH)

def get_ignored_item_filters() -> List[Tuple[int, str]]:
    copy_config_to_data()
    if not os.path.exists(IGNORED_ITEMS_TARGET_PATH):
        return []

    filters = []
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
