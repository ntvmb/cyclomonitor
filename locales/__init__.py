"""CycloMonitor locales"""

import locale
import json
import pathlib
import os
import sys as _sys
import logging as _logging

LOG_TENDO_NOT_FOUND = "LOG_TENDO_NOT_FOUND"
ERROR_ALREADY_RUNNING = "ERROR_ALREADY_RUNNING"
LOG_MONITOR_STOP = "LOG_MONITOR_STOP"
LOG_TIMESTAMP_COMPARISON = "LOG_TIMESTAMP_COMPARISON"
LOG_AUTO_UPDATE_BEGIN = "LOG_AUTO_UPDATE_BEGIN"
ERROR_AUTO_UPDATE_FAILED = "ERROR_AUTO_UPDATE_FAILED"
LOG_SUPPRESSED = "LOG_SUPPRESSED"
LOG_SUPPRESSED_TRY_2 = "LOG_SUPPRESSED_TRY_2"
CM_SUPPRESSED_MESSAGE = "CM_SUPPRESSED_MESSAGE"
NEXT_AUTO_UPDATE = "NEXT_AUTO_UPDATE"
CM_ERROR_WHILE_UPDATING = "CM_ERROR_WHILE_UPDATING"
CM_ATTACH_LOG = "CM_ATTACH_LOG"
ERROR_LOG_SEND_FAIL = "ERROR_LOG_SEND_FAIL"
LOG_NO_OWNER = "LOG_NO_OWNER"
CM_AUTO_UPDATE_FAILED_MESSAGE = "CM_AUTO_UPDATE_FAILED_MESSAGE"
LOG_IBTRACS_UPDATE_BEGIN = "LOG_IBTRACS_UPDATE_BEGIN"
LOG_IBTRACS_UPDATE_FAILED_ATTEMPT_1 = "LOG_IBTRACS_UPDATE_FAILED_ATTEMPT_1"
LOG_NEXT_ATTEMPT = "LOG_NEXT_ATTEMPT"
LOG_ATTEMPT_FAILED = "LOG_ATTEMPT_FAILED"
ERROR_IBTRACS_UPDATE_FAILED = "ERROR_IBTRACS_UPDATE_FAILED"
LOG_TRY_AGAIN = "LOG_TRY_AGAIN"
LOG_UPDATE_GUILD = "LOG_UPDATE_GUILD"
NOT_AVAILABLE = "NOT_AVAILABLE"
STORM_MOVEMENT = "STORM_MOVEMENT"
LOG_BASIN = "LOG_BASIN"
CLASS_AOI = "CLASS_AOI"
CLASS_PTC = "CLASS_PTC"
CLASS_RL = "CLASS_RL"
CLASS_TD = "CLASS_TD"
CLASS_SD = "CLASS_SD"
CLASS_TS = "CLASS_TS"
CLASS_SS = "CLASS_SS"
CLASS_HU = "CLASS_HU"
CLASS_MH = "CLASS_MH"
CLASS_TY = "CLASS_TY"
CLASS_STY = "CLASS_STY"
CLASS_CY = "CLASS_CY"
LOG_NEW_RECORD = "LOG_NEW_RECORD"
LOG_NO_RECORD = "LOG_NO_RECORD"
CM_STORM_INFO = "CM_STORM_INFO"
LOG_GUILD_UNAVAILABLE = "LOG_GUILD_UNAVAILABLE"
CM_NO_STORMS = "CM_NO_STORMS"
NO_AUTO_UPDATE = "NO_AUTO_UPDATE"
CM_NEXT_AUTO_UPDATE = "CM_NEXT_AUTO_UPDATE"
CM_MORE_INFO = "CM_MORE_INFO"
CM_WATCHING = "CM_WATCHING"
LOG_READY = "LOG_READY"
LOG_NEW_GUILD = "LOG_NEW_GUILD"
CM_GUILD_ADDED = "CM_GUILD_ADDED"
LOG_GUILD_REMOVED = "LOG_GUILD_REMOVED"
CM_NO_PERMISSION = "CM_NO_PERMISSION"
LOG_NO_PERMISSION = "LOG_NO_PERMISSION"
CM_NO_DM = "CM_NO_DM"
LOG_COMMAND_ERROR = "LOG_COMMAND_ERROR"
CM_COMMAND_ERROR = "CM_COMMAND_ERROR"
ERROR_CANNOT_RESPOND = "ERROR_CANNOT_RESPOND"
CM_PING = "CM_PING"
CM_PONG = "CM_PONG"
CM_SET_TRACKING_CHANNEL = "CM_SET_TRACKING_CHANNEL"
CM_CHANNEL_TO_USE = "CM_CHANNEL_TO_USE"
ERROR_NOT_A_TEXT_CHANNEL = "ERROR_NOT_A_TEXT_CHANNEL"
CM_SET_CHANNEL_SUCCESS = "CM_SET_CHANNEL_SUCCESS"
CM_CANNOT_SEND_MESSAGE = "CM_CANNOT_SEND_MESSAGE"
CM_UPDATE = "CM_UPDATE"
CM_UPDATE_SUCCESS = "CM_UPDATE_SUCCESS"
ERROR_NO_TRACKING_CHANNEL = "ERROR_NO_TRACKING_CHANNEL"
CM_UPDATE_ALT = "CM_UPDATE_ALT"
CM_SET_BASINS = "CM_SET_BASINS"
CM_NATL = "CM_NATL"
CM_EPAC = "CM_EPAC"
CM_CPAC = "CM_CPAC"
CM_WPAC = "CM_WPAC"
CM_NIO = "CM_NIO"
CM_SHEM = "CM_SHEM"
CM_BASINS_SAVED = "CM_BASINS_SAVED"
CM_UPDATE_ALL = "CM_UPDATE_ALL"
CM_UPDATE_ALL_ALT = "CM_UPDATE_ALL_ALT"
CM_ANNOUNCE_ALL = "CM_ANNOUNCE_ALL"
CM_TO_ANNOUNCE = "CM_TO_ANNOUNCE"
CM_ANNOUNCE_ALL_SUCCESS = "CM_ANNOUNCE_ALL_SUCCESS"
CM_ANNOUNCE_BASIN = "CM_ANNOUNCE_BASIN"
CM_BASIN_TO_ANNOUNCE = "CM_BASIN_TO_ANNOUNCE"
CM_BASIN_ANNOUNCEMENT = "CM_BASIN_ANNOUNCEMENT"
CM_ANNOUNCE_BASIN_SUCCESS = "CM_ANNOUNCE_BASIN_SUCCESS"
CM_ANNOUNCE_FILE = "CM_ANNOUNCE_FILE"
CM_TXT_FILE = "CM_TXT_FILE"
ERROR_NOT_A_TXT_FILE = "ERROR_NOT_A_TXT_FILE"
CM_INVITE = "CM_INVITE"
CM_INVITE_MESSAGE = "CM_INVITE_MESSAGE"
CM_STATISTICS_DESC = "CM_STATISTICS_DESC"
ERROR_NO_GLOBAL_VARS = "ERROR_NO_GLOBAL_VARS"
CM_STATISTICS = "CM_STATISTICS"
CM_YIKES = "CM_YIKES"
CM_INC_YIKES_COUNT = "CM_INC_YIKES_COUNT"
CM_YIKES_RESPONSE = "CM_YIKES_RESPONSE"
CM_GET_DATA = "CM_GET_DATA"
CM_GET_DATA_SUCCESS = "CM_GET_DATA_SUCCESS"
CM_GET_DATA_FAILED = "CM_GET_DATA_FAILED"
CM_GET_DATA_ALT = "CM_GET_DATA_ALT"
CM_ATCF_RESET = "CM_ATCF_RESET"
CM_ATCF_RESET_SUCCESS = "CM_ATCF_RESET_SUCCESS"
CM_GITHUB = "CM_GITHUB"
CM_GITHUB_RESPONSE = "CM_GITHUB_RESPONSE"
CM_COPYRIGHT = "CM_COPYRIGHT"
CM_RSMC_LIST = "CM_RSMC_LIST"
CM_RSMC_LIST_RESPONSE = "CM_RSMC_LIST_RESPONSE"
CM_GET_LOG = "CM_GET_LOG"
LOG_REQUESTED = "LOG_REQUESTED"
CM_LOG_SENT = "CM_LOG_SENT"
CM_SUSPEND_UPDATES = "CM_SUSPEND_UPDATES"
CM_SUSPEND_UPDATES_SUCCESS = "CM_SUSPEND_UPDATES_SUCCESS"
CM_UPDATES_ALREADY_SUSPENDED = "CM_UPDATES_ALREADY_SUSPENDED"
CM_RESUME_UPDATES = "CM_RESUME_UPDATES"
CM_RESUME_UPDATES_SUCCESS = "CM_RESUME_UPDATES_SUCCESS"
CM_UPDATES_ALREADY_RUNNING = "CM_UPDATES_ALREADY_RUNNING"
CM_FEEDBACK = "CM_FEEDBACK"
CM_FEEDBACK_TO_SEND = "CM_FEEDBACK_TO_SEND"
CM_FEEDBACK_RECEIVED = "CM_FEEDBACK_RECEIVED"
CM_FEEDBACK_SENT = "CM_FEEDBACK_SENT"
CM_NO_OWNER = "CM_NO_OWNER"
CM_GET_PAST_STORM = "CM_GET_PAST_STORM"
CM_PAST_STORM_NAME = "CM_PAST_STORM_NAME"
CM_PAST_STORM_SEASON = "CM_PAST_STORM_SEASON"
CM_PAST_STORM_BASIN = "CM_PAST_STORM_BASIN"
CM_PAST_STORM_ATCF = "CM_PAST_STORM_ATCF"
CM_PAST_STORM_SID = "CM_PAST_STORM_SID"
CM_PAST_STORM_TABLE = "CM_PAST_STORM_TABLE"
CM_WAIT_FOR_IBTRACS_UPDATE = "CM_WAIT_FOR_IBTRACS_UPDATE"
CM_SEARCHING = "CM_SEARCHING"
CM_ERROR = "CM_ERROR"
CM_MULTIPLE_STORMS = "CM_MULTIPLE_STORMS"
CM_UNNAMED_STORM = "CM_UNNAMED_STORM"
CM_UNKNOWN = "CM_UNKNOWN"
CM_PAST_STORM_INFO = "CM_PAST_STORM_INFO"
CM_NO_RESULTS = "CM_NO_RESULTS"
ERROR_WTF = "ERROR_WTF"
CM_SET_LANGUAGE = "CM_SET_LANGUAGE"
CM_LANG_TO_USE = "CM_LANG_TO_USE"
CM_SET_LANGUAGE_SUCCESS = "CM_SET_LANGUAGE_SUCCESS"
ATCF_PARSE_STORM = "ATCF_PARSE_STORM"
ATCF_ERROR_COL = "ATCF_ERROR_COL"
ATCF_WRONG_DATA = "ATCF_WRONG_DATA"
ATCF_NO_DATA = "ATCF_NO_DATA"
ERROR_HDYGH = "ERROR_HDYGH"
ATCF_GET_INTERP_FAILED = "ATCF_GET_INTERP_FAILED"
ATCF_USING_MAIN = "ATCF_USING_MAIN"
ATCF_USING_MAIN_FAILED = "ATCF_USING_MAIN_FAILED"
ATCF_USING_ALT = "ATCF_USING_ALT"
ERROR_TIMED_OUT = "ERROR_TIMED_OUT"
ERROR_ATCF_GET_DATA_FAILED = "ERROR_ATCF_GET_DATA_FAILED"
ERROR_GET_FORECAST_NO_PARAMS = "ERROR_GET_FORECAST_NO_PARAMS"
CM_GET_FORECAST = "CM_GET_FORECAST"
CM_NO_ACTIVE_STORMS = "CM_NO_ACTIVE_STORMS"
CM_CANNOT_FIND_STORM = "CM_CANNOT_FIND_STORM"
CM_IS_AN_INVEST = "CM_IS_AN_INVEST"

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
