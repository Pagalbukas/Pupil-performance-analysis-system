import os

DATA_PATH = os.path.join(os.environ["APPDATA"], "Pagalbukas-Analizatorius")
TEMP_PATH = os.path.join(DATA_PATH, "temp")

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
