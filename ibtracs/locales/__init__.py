"""CycloMonitor locales (IBTrACS module)"""

import locale
import json
import pathlib
import os
import sys as _sys
import logging as _logging

IBTRACS_DB_NOT_FOUND = "IBTRACS_DB_NOT_FOUND"
CLASS_TD = "CLASS_TD"
CLASS_SD = "CLASS_SD"
CLASS_TS = "CLASS_TS"
CLASS_SS = "CLASS_SS"
CLASS_HU = "CLASS_HU"
CLASS_TY = "CLASS_TY"
CLASS_STY = "CLASS_STY"
CLASS_TC = "CLASS_TC"
CLASS_STC = "CLASS_STC"
QUERY_REPR = "QUERY_REPR"
ERROR_ILLEGAL_UPDATE_MODE = "ERROR_ILLEGAL_UPDATE_MODE"
IBTRACS_UPDATE_LAST3 = "IBTRACS_UPDATE_LAST3"
IBTRACS_UPDATE_ALL = "IBTRACS_UPDATE_ALL"
IBTRACS_UPDATE_FULL = "IBTRACS_UPDATE_FULL"
IBTRACS_GETTING_DATA = "IBTRACS_GETTING_DATA"
ERROR_IBTRACS_UPDATE_FAILURE = "ERROR_IBTRACS_UPDATE_FAILURE"
ERROR_MISSING_IBTRACS_DB = "ERROR_MISSING_IBTRACS_DB"
ERROR_INVALID_TABLE = "ERROR_INVALID_TABLE"
ERROR_INVALID_BASIN = "ERROR_INVALID_BASIN"
ERROR_INVALID_SEASON = "ERROR_INVALID_SEASON"
ERROR_NO_PARAMS = "ERROR_NO_PARAMS"
IBTRACS_CONDS = "IBTRACS_CONDS"
IBTRACS_UPDATE_SUCCESS = "IBTRACS_UPDATE_SUCCESS"

_log = _logging.getLogger(__name__)
locale.setlocale(locale.LC_ALL, "")
_PATH = os.path.dirname(os.path.realpath(__file__))


def set_locale(lang="C"):
    """Set the locale to `lang`. Returns the language that was set."""
    json_file = pathlib.Path(f"{_PATH}/{lang}.json")
    try:
        with json_file.open() as f:
            lc = json.load(f)
    except OSError:
        _log.exception(f"Locale {lang} not found. Falling back to default locale (C).")
        lang = "C"
        with open(f"{_PATH}/C.json") as f:
            lc = json.load(f)

    globals().update({k: v for k, v in lc.items()})
    return lang


def locale_init():
    global lang
    if _sys.platform.startswith("win32"):
        import ctypes

        windll = ctypes.windll.kernel32
        lang = locale.windows_locale[windll.GetUserDefaultUILanguage()]
    else:
        lang, _ = locale.getlocale()
    lang = set_locale(lang)


locale_init()
