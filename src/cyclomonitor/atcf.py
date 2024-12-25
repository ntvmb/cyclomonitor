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
import aiohttp
import asyncio
import json
import logging
import aiofiles
from itertools import zip_longest
from .locales import *

# initalize variables
# For whatever reason I have yet to discover, the domain `www.nrlmry.navy.mil`
# causes requests from aiohttp to take much longer than expected, so I have to
# directly connect to its IP address.
URL = "https://199.9.2.136/geoips/tcdat/sectors/atcf_sector_file"
URL_INTERP = "https://199.9.2.136/geoips/tcdat/sectors/interp_sector_file"
URL_ALT = "https://api.knackwx.com/atcf/v2"
BASE_URL_NHC = (
    "https://www.nhc.noaa.gov/storm_graphics/{0}/{1}_5day_cone_with_line_and_wind.png"
)
BASE_URL_JTWC = "https://www.metoc.navy.mil/jtwc/products/{0}.gif"
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
long_cids = []
log = logging.getLogger(__name__)

# increase compatibility with python<3.11
if not hasattr(datetime, "UTC"):
    datetime.UTC = datetime.timezone.utc


class ATCFError(Exception):
    """An Exception for general ATCF errors."""

    pass


class WrongData(ATCFError):
    """An Exception for incorrectly formatted data."""

    pass


class NoActiveStorms(ATCFError):
    """Used by get_forecast() to signal that no storms are active."""

    pass


async def main():
    print("CycloMonitor ATCF Module")
    print("CLI coming soon")


def reset():
    """Reset ATCF data."""
    cyclones.clear()
    names.clear()
    timestamps.clear()
    lats.clear()
    longs.clear()
    basins.clear()
    winds.clear()
    pressures.clear()
    tc_classes.clear()
    lats_real.clear()
    longs_real.clear()
    movement_speeds.clear()
    movement_dirs.clear()
    long_cids.clear()


def parse_storm(line: str, *, mode="std"):
    """Parse ATCF data.

    Arguments:
    line -- the data to be parsed
    Keyword arguments:
    mode -- parsing mode (default "std")
    If mode is "interp", parse extra data provided in ATCF's
    interp_sector_file.
    """
    log.debug(ATCF_PARSE_STORM.format(line, mode))
    storm = line.split()
    try:
        if mode == "interp":
            assert len(storm) == 12, ATCF_ERROR_COL.format(12, mode, len(storm))
        else:
            assert len(storm) == 9, ATCF_ERROR_COL.format(9, mode, len(storm))
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
            long_cids.append(storm[0])
    except (AssertionError, LookupError, ValueError) as e:
        # remove the faulty entry
        faulty_entry = len(cyclones) - 1
        for index, (cy, n, ts, lat, lon, b, w, p) in enumerate(
            zip_longest(
                cyclones, names, timestamps, lats, longs, basins, winds, pressures
            )
        ):
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
            for index, (la, lo, c, ms, md) in enumerate(
                zip_longest(
                    lats_real, longs_real, tc_classes, movement_speeds, movement_dirs
                )
            ):
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

        log.exception(ATCF_WRONG_DATA.format(line))
        raise WrongData(ATCF_WRONG_DATA.format(line)) from e


# Do NOT make this function a coroutine.
def load():
    """Load ATCF data saved on disk."""
    try:
        with open("atcf_sector_file", "r") as file:
            for line in file:
                try:
                    parse_storm(line)
                except WrongData:
                    continue
    except FileNotFoundError:
        log.info(ATCF_NO_DATA)
        return

    try:
        with open("interp_sector_file", "r") as file:
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
                        long_cids.append(storm[0])
                        break
                else:  # no break
                    raise ATCFError(ERROR_HDYGH)
    except Exception as e:
        raise ATCFError(ATCF_GET_INTERP_FAILED) from e


# load cached data upon bringing in the module
load()


async def get_data():
    """Download ATCF data."""
    global cyclones, names, timestamps, lats, longs, basins, winds, pressures
    global tc_classes, lats_real, longs_real, movement_speeds, movement_dirs
    reset()
    log.info(ATCF_USING_MAIN)
    async with aiohttp.ClientSession(
        timeout=aiohttp.ClientTimeout(connect=10), raise_for_status=True
    ) as session:
        try:
            async with session.get(URL, ssl=False) as r:
                async with aiofiles.open("atcf_sector_file", "w") as f:
                    await f.write(await r.text())
            async with session.get(URL_INTERP, ssl=False) as r:
                async with aiofiles.open("interp_sector_file", "w") as f:
                    await f.write(await r.text())
        except Exception as e:
            log.warning(ATCF_USING_MAIN_FAILED.format(e))
            await get_data_alt()
            return
    load()
    # safeguard for some situations where the main ATCF website is down
    if not cyclones:
        await get_data_alt()


async def get_data_alt():
    """Download ATCF data (alt source)."""
    global cyclones, names, timestamps, lats, longs, basins, winds, pressures
    global tc_classes, lats_real, longs_real, movement_speeds, movement_dirs
    reset()
    log.info(ATCF_USING_ALT)
    async with aiohttp.ClientSession(
        timeout=aiohttp.ClientTimeout(connect=10), raise_for_status=True
    ) as session:
        try:
            async with session.get(URL_ALT) as r:
                tc_list = await r.json()
        except asyncio.TimeoutError as e:
            raise ATCFError(ERROR_TIMED_OUT) from e
        except aiohttp.ClientError as exc:
            raise ATCFError(ERROR_ATCF_GET_DATA_FAILED) from exc

    async with aiofiles.open("atcf_sector_file", "w") as f:
        for d in tc_list:
            await f.write(d["atcf_sector_file"] + "\n")

    async with aiofiles.open("interp_sector_file", "w") as f:
        for d in tc_list:
            await f.write(d["interp_sector_file"] + "\n")

    for d in tc_list:
        try:
            parse_storm(d["atcf_sector_file"])
            parse_storm(d["interp_sector_file"], mode="interp")
        except WrongData:
            continue


async def get_forecast(*, name="", cid=""):
    """Download the official forecast image for an active TC.
    Returns the extension of the downloaded image file.

    Keyword arguments:
    name -- Search by name
    cid -- Search by identifier
    You must specify either name or cid. name has priority over cid.
    """
    if not (cyclones and names):
        raise NoActiveStorms()
    if not (name or cid):
        raise ValueError(ERROR_GET_FORECAST_NO_PARAMS)
    if name:
        name = name.upper()
        try:
            index = names.index(name)
        except ValueError:
            index = -1
    else:
        index = -1
    if index == -1 or not name:
        try:
            index = cyclones.index(cid)
        except ValueError:
            return None

    basin = basins[index][:2]  # 2-char basin identifier
    num = cyclones[index][:2]  # 2-digit storm number
    jtwc_year = long_cids[index][6:]  # Last 2 digits of the year
    atcf_id = long_cids[index].upper()
    if basin == "AT" or basin == "EP" or basin == "CP":
        nhc_basin = basin
    else:
        nhc_basin = None

    async with aiohttp.ClientSession(
        timeout=aiohttp.ClientTimeout(connect=10), raise_for_status=True
    ) as session:
        if nhc_basin is not None:
            nhc_id = f"{nhc_basin}{num}"
            coro = session.get(BASE_URL_NHC.format(nhc_id, atcf_id))
        else:
            basin = basin.lower()
            jtwc_id = f"{basin}{num}{jtwc_year}"
            coro = session.get(BASE_URL_JTWC.format(jtwc_id))

        async with coro as r:
            # assuming everything is good, this will either be png or gif
            ext = r.content_type.split("/")[1]
            async with aiofiles.open(f"forecast.{ext}", "wb") as img:
                await img.write(await r.read())
    return ext


if __name__ == "__main__":
    asyncio.run(main())
