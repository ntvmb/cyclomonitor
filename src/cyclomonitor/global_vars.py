# see server_vars.py for documentation on related functions
# CycloMonitor Copyright (C) 2023 Nathaniel Greenwell
# This program comes with ABSOLUTELY NO WARRANTY; for details see main.py
import json
import logging

log = logging.getLogger(__name__)
json_file = "globalVars.json"


def write(var_name: str, value):
    try:
        with open(json_file, "r") as f:
            data = json.load(f)
    except FileNotFoundError:
        data = {}
    data.update({var_name: value})
    with open(json_file, "w") as f:
        f.write(json.dumps(data, indent=4))


def get(var_name: str):
    try:
        with open(json_file, "r") as f:
            data = json.load(f)
    except Exception:
        log.warning("Cannot open JSON file")
        return None
    value = data.get(var_name)
    return value
