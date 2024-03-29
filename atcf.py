# CycloMonitor Copyright (C) 2023 Nathaniel Greenwell
# This program comes with ABSOLUTELY NO WARRANTY; for details see main.py
"""
CycloMonitor ATCF module

Classes:
ATCFError -- base exception for ATCF errors
WrongData -- exception for invalid data
Functions:
reset -- reset ATCF data
parse_storm -- parse ATCF data
load -- load ATCF data
get_data -- get ATCF data
get_data_alt -- get ATCF data (alt source)
"""
import datetime
import requests
import json
import logging
from itertools import zip_longest

# initalize variables
url = "https://www.nrlmry.navy.mil/tcdat/sectors/atcf_sector_file"
url_interp = "https://www.nrlmry.navy.mil/tcdat/sectors/interp_sector_file"
url_alt = "https://api.knackwx.com/atcf/v2"
cyclones = []
names = []
timestamps = []
lats = []
longs = []
basins = []
winds = []
pressures = []
tc_classes = []
lats_real = []
longs_real = []
movement_speeds = []
movement_dirs = []
log = logging.getLogger(__name__)


class ATCFError(Exception):
    """An Exception for general ATCF errors."""
    pass


class WrongData(Exception):
    """An Exception for incorrectly formatted data."""
    pass


def main():
    print("CycloMonitor ATCF Module")
    print("CLI coming soon")


def reset():
    """Reset ATCF data."""
    global cyclones, names, timestamps, lats, longs, basins, winds, pressures
    global tc_classes, lats_real, longs_real, movement_speeds, movement_dirs
    cyclones = []
    names = []
    timestamps = []
    lats = []
    longs = []
    basins = []
    winds = []
    pressures = []
    tc_classes = []
    lats_real = []
    longs_real = []
    movement_speeds = []
    movement_dirs = []


def parse_storm(line: str, *, mode="std"):
    """Parse ATCF data.

    Arguments:
    line -- the data to be parsed
    Keyword arguments:
    mode -- parsing mode (default "std")
    If mode is "interp", parse extra data provided in ATCF's
    interp_sector_file.
    """
    log.debug(f"Parsing line {line} in mode {mode}")
    storm = line.split()
    try:
        if mode == "interp":
            assert len(storm) == 12, f"Expected 12 columns for mode interp, got {len(storm)}."
        else:
            assert len(storm) == 9, f"Expected 9 columns for mode std, got {len(storm)}."
        if not mode == "interp":
            cyclones.append(storm[0])
            names.append(storm[1])
            time = storm[2] + storm[3]
            # convert the timestamp from the given data to Unix time
            timestamp = datetime.datetime.strptime(time, "%y%m%d%H%M")
            timestamp = timestamp.replace(tzinfo=datetime.UTC)
            utc_time = int(timestamp.timestamp())
            timestamps.append(utc_time)
            lats.append(storm[4])
            longs.append(storm[5])
            basins.append(storm[6])
            winds.append(int(storm[7]))
            pressures.append(int(storm[8]))
        else:
            lats_real.append(float(storm[4]))
            longs_real.append(float(storm[5]))
            tc_classes.append(storm[7])
            movement_speeds.append(float(storm[10]))
            movement_dirs.append(float(storm[11]))
    except Exception as e:
        # remove the faulty entry
        faulty_entry = len(cyclones) - 1
        for index, (cy, n, ts, lat, lon, b, w, p) in enumerate(zip_longest(cyclones, names, timestamps, lats, longs, basins, winds, pressures)):
            if index == faulty_entry:
                if cy is not None:
                    cyclones.remove(cy)
                if n is not None:
                    names.remove(n)
                if ts is not None:
                    timestamps.remove(ts)
                if lat is not None:
                    lats.remove(lat)
                if lon is not None:
                    longs.remove(lon)
                if b is not None:
                    basins.remove(b)
                if w is not None:
                    winds.remove(w)
                if p is not None:
                    pressures.remove(p)

        if mode == "interp":
            for index, (la, lo, c, ms, md) in enumerate(zip_longest(lats_real, longs_real, tc_classes, movement_speeds, movement_dirs)):
                if index == faulty_entry:
                    if la is not None:
                        lats_real.remove(la)
                    if lo is not None:
                        longs_real.remove(lo)
                    if c is not None:
                        tc_classes.remove(c)
                    if ms is not None:
                        movement_speeds.remove(ms)
                    if md is not None:
                        movement_dirs.remove(md)

        log.exception(f"Entry {line} is formatted incorrectly. It will not be counted.")
        raise WrongData(f"Entry {line} is formatted incorrectly.") from e


def load():
    """Load ATCF data saved on disk."""
    try:
        with open('atcf_sector_file', 'r') as file:
            for line in file:
                try:
                    parse_storm(line)
                except WrongData:
                    continue
    except FileNotFoundError:
        log.info("No cached data found.")
        return

    try:
        with open('interp_sector_file', 'r') as file:
            storms = []
            for line in file:
                storms.append(line.split())
            for tc in cyclones:
                for storm in storms:
                    # sort interp data
                    cid = storm[0][2] + storm[0][3] + storm[6]
                    if cid == tc:
                        lats_real.append(float(storm[4]))
                        longs_real.append(float(storm[5]))
                        tc_classes.append(storm[7])
                        movement_speeds.append(float(storm[10]))
                        movement_dirs.append(float(storm[11]))
                        break
                else: # no break
                    raise ATCFError("How did you get here?")
    except Exception as e:
        raise ATCFError("Failure to get interp data") from e


# load cached data upon bringing in the module
load()


def get_data():
    """Download ATCF data."""
    global cyclones, names, timestamps, lats, longs, basins, winds, pressures
    global tc_classes, lats_real, longs_real, movement_speeds, movement_dirs
    reset()
    log.info("Using main ATCF source.")
    try:
        ra = requests.get(url, verify=False, timeout=15)
        ra.raise_for_status()
        ri = requests.get(url_interp, verify=False, timeout=15)
        ri.raise_for_status()
    except requests.RequestException as e:
        log.warning(f"Getting data from main source failed: {e}.")
        get_data_alt()
        return
    with open('atcf_sector_file', 'wb') as f:
        f.write(ra.content)
    with open('interp_sector_file', 'wb') as f:
        f.write(ri.content)
    load()
    # safeguard for some situations where the main ATCF website is down
    if len(cyclones) == 0:
        get_data_alt()


def get_data_alt():
    """Download ATCF data (alt source)."""
    global cyclones, names, timestamps, lats, longs, basins, winds, pressures
    global tc_classes, lats_real, longs_real, movement_speeds, movement_dirs
    reset()
    log.info("Using alternate ATCF source.")
    try:
        r = requests.get(url_alt, verify=False, timeout=15)
        r.raise_for_status()
    except requests.Timeout as e:
        raise ATCFError("Request timed out.") from e
    except requests.RequestException as exc:
        raise ATCFError("Failed to get ATCF data.") from exc
    with open('atcf_sector_file.tmp', 'wb') as f:
        f.write(r.content)
    with open('atcf_sector_file.tmp', 'r') as f:
        tc_list = json.load(f)

    # for debugging
    with open('atcf_sector_file', 'w') as f:
        for d in tc_list:
            f.write(d['atcf_sector_file']+"\n")

    with open('interp_sector_file', 'w') as f:
        for d in tc_list:
            f.write(d['interp_sector_file']+"\n")

    for d in tc_list:
        try:
            parse_storm(d['atcf_sector_file'])
            parse_storm(d['interp_sector_file'], mode="interp")
        except WrongData:
            continue


if __name__ == "__main__":
    main()
