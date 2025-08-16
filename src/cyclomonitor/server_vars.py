# CycloMonitor Copyright (C) 2023 Nathaniel Greenwell
# This program comes with ABSOLUTELY NO WARRANTY; for details see main.py
import json
import logging

log = logging.getLogger(__name__)
json_file = "serverVars.json"


def write(var_name: str, value, guild: int):
    # if the json file exists, load it, otherwise initialize a blank list
    try:
        with open(json_file, "r") as f:
            data = json.load(f)
    except FileNotFoundError:
        data = []
    for i in data:
        if i.get(str(guild)) is not None:
            server_data = i.get(str(guild))
            server_data.update({var_name: value})
            break
    # this code segment is run if the loop was not broken
    else:
        data.append({str(guild): {var_name: value}})
    if len(data) == 0:
        data.append({str(guild): {var_name: value}})
    with open(json_file, "w") as f:
        f.write(json.dumps(data, indent=4))


# this is expected to be assigned to a variable, so we return None if no data can be loaded
def get(var_name: str, guild: int):
    try:
        with open(json_file, "r") as f:
            data = json.load(f)
    except Exception:
        log.warning("Cannot open JSON file")
        return None
    for i in data:
        if i.get(str(guild)) is not None:
            server_data = i.get(str(guild))
            value = server_data.get(var_name)
            return value
    return None


def remove_guild(guild: int):
    try:
        with open(json_file, "r") as f:
            data = json.load(f)
    except Exception:
        log.warning("Cannot open JSON file")
        return None
    for i in data:
        if i.get(str(guild)) is not None:
            data.remove(i)
            with open(json_file, "w") as f:
                f.write(json.dumps(data, indent=4))
