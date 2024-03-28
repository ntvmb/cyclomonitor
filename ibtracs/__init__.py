"""
CycloMonitor IBTrACS module

Classes:
Storm -- dataclass representing a TC
Query -- like Storm but less detailed
Generators:
query_group -- self-explanatory
Functions:
update_db -- update database
init_db -- initialize database
get_storm -- find TCs
:copyright: (c) 2024 by Nathaniel Greenwell.
"""
import sqlite3
import requests
import logging
import os
import subprocess
import io
from dataclasses import dataclass
from collections.abc import Iterable
log = logging.getLogger(__name__)
PATH = os.path.dirname(os.path.realpath(__file__))
DB = f"{PATH}/BestTrack.db"
base_uri = "https://www.ncei.noaa.gov/data/international-best-track-archive-for-climate-stewardship-ibtracs/v04r00/access/csv"
if not os.path.exists(DB):
    log.info("Best track database not found.")


@dataclass(frozen=True)
class Storm:
    """A dataclass representing a TC.

    Attributes:
    atcf_id -- the storm's ATCF ID
    basin -- the basin the storm formed in
    peak_winds -- the storm's maximum wind speed
    peak_pres -- the storm's minimum pressure
    time_of_peak -- time the storm peaked in ISO format
    name -- the storm's name
    best_track_id -- the storm's IBTrACS ID
    season -- the year the storm formed in
    Methods:
    nature() -- cyclonic nature at peak
    is_subtropical()
    """
    atcf_id: str
    basin: str
    peak_winds: int
    peak_pres: int
    time_of_peak: str
    name: str = "NOT_NAMED"
    best_track_id: str = ""
    season: int = 0

    def nature(self) -> str:
        """Based on peak winds, return a string."""
        subtropical = self.is_subtropical()
        if self.peak_winds:
            if self.peak_winds < 34:
                if subtropical:
                    return "SUBTROPICAL DEPRESSION"
                else:
                    return "TROPICAL DEPRESSION"
            if self.peak_winds < 64:
                if subtropical:
                    return "SUBTROPICAL STORM"
                else:
                    return "TROPICAL STORM"
            if self.basin == "WP":
                if self.peak_winds < 130:
                    return "TYPHOON"
                else:
                    return "SUPER TYPHOON"
            if self.basin == "NA" or self.basin == "SA" or self.basin == "EP":
                return "HURRICANE"
        if subtropical:
            return "SUBTROPICAL CYCLONE"
        # this value does double-duty as a generic term and the term for hurricane-strength storms in basins not listed above
        return "TROPICAL CYCLONE"

    def is_subtropical(self, *, table="LastThreeYears"):
        if not self.peak_winds:
            return False
        for v in self.__dict__.values():
            if isinstance(v, str) and ("'" in v or ";" in v):
                return False
        con = sqlite3.connect(DB)
        cur = con.cursor()
        if self.best_track_id:
            params = [self.best_track_id, self.peak_winds, self.peak_winds]
            conds = f"SID = ? AND NATURE != 'ET' AND (WMO_WIND = ? OR USA_WIND = ?)"
        else:
            params = [self.name, self.season, self.basin, self.peak_winds, self.peak_winds]
            conds = f"NAME = ? AND SEASON = ? AND BASIN = ? AND NATURE != 'ET' AND (WMO_WIND = ? OR USA_WIND = ?)"
        res = cur.execute(f"SELECT NATURE FROM {table} WHERE {conds}", params)
        natures = res.fetchall()
        con.close()
        if natures:
            if (("SS",) in natures or ("DS",) in natures) and ("TS",) not in natures:
                return True
        else:
            if not natures and table == "LastThreeYears":
                return self.is_subtropical(table="AllBestTrack")
        return False


@dataclass(frozen=True, repr=False)
class Query:
    """General TC info; no peak.

    Attributes:
    sid -- IBTrACS ID
    season -- year of formation
    basin -- basin the storm formed in
    name -- the storm's name
    """
    sid: str
    season: int
    basin: str
    name: str

    def __repr__(self):
        return f"{self.name} ({self.season}) from {self.basin} (IBTrACS ID: {self.sid})"


def query_group(queries: Iterable[tuple[str, int, str, str]]):
    """Yield Query objects.

    Arguments:
    queries -- an iterable consisting of tuples with length 4
    """
    for sid, season, basin, name in queries:
        yield Query(sid, season, basin, name)


def _remove_headers(csv: os.PathLike | str):
    if isinstance(csv, os.PathLike):
        csv = os.fspath(csv)
    csv_name = os.path.splitext(csv)[0]
    with open(csv) as f:
        lines = f.readlines()
        data = lines[2:]
    new_name = f"{csv_name}_NO_HEADING.csv"
    try:
        with open(new_name, "w") as f:
            f.writelines(data)
    # There has to be an except or finally clause before an else clause.
    except OSError:
        pass
    else:
        os.unlink(csv)
    finally:
        # free up RAM
        del data, lines


def update_db(mode="last3"):
    """Update the best track database.

    Arguments:
    mode -- Table(s) to update (default "last3")
    mode can be one of "last3", "all", or "full".
    If mode == "last3", update the table LastThreeYears.
    If mode == "all", update the table AllBestTrack.
    If mode == "full", update both tables.
    """
    get_last3 = mode == "last3" or mode == "full"
    get_all = mode == "all" or mode == "full"
    if not (get_last3 or get_all):
        raise ValueError(f"Illegal mode: {mode}\nValid options are: last3, all, full")
    if mode == "last3":
        log.info("Performing update in mode last3.")
    elif mode == "all":
        log.info("Performing update in mode all.")
    else:
        log.info("Performing full update.")
    log.info("Getting IBTrACS data (this may take a while)...")
    if get_last3:
        csv = "ibtracs_last3.csv"
        r = requests.get(f"{base_uri}/ibtracs.last3years.list.v04r00.csv",
                         timeout=15)
        try:
            r.raise_for_status()
            with open(f"{PATH}/{csv}", "wb") as f:
                f.write(r.content)
        except Exception:
            log.exception("Error getting or writing IBTrACS data")
            raise
        finally:
            # Calling close does not delete the object.
            # We want to delete the resource afterwards to save RAM because we may be working with a large amount of data.
            del r
        _remove_headers(f"{PATH}/{csv}")
        subprocess.run(["sqlite3", DB],
                       input=f".cd {PATH}\n.read ibtracs_LAST3.sql",
                       encoding="UTF-8",
                       check=True)
        os.unlink(f"{PATH}/ibtracs_last3_NO_HEADING.csv")
    if get_all:
        csv = "ibtracs_all.csv"
        r = requests.get(f"{base_uri}/ibtracs.ALL.list.v04r00.csv",
                         timeout=15)
        try:
            r.raise_for_status()
            with open(f"{PATH}/{csv}", "wb") as f:
                f.write(r.content)
        except Exception:
            log.exception("Error getting or writing IBTrACS data")
            raise
        finally:
            del r
        _remove_headers(f"{PATH}/{csv}")
        subprocess.run(["sqlite3", DB],
                       input=f".cd {PATH}\n.read ibtracs_ALL.sql",
                       encoding="UTF-8",
                       check=True)
        os.unlink(f"{PATH}/ibtracs_all_NO_HEADING.csv")


def init_db():
    """Equivalent to update_db("full")"""
    update_db("full")


def get_storm(*, name=None, season: int = 0, basin=None, atcf_id=None, ibtracs_id=None, table=None):
    """Find a TC and return either a query_group() or a Storm().

    If only one storm is found, return a Storm() object.
    If more than one storm is found, return a query_group() object.
    Keyword arguments:
    name -- Filter by name (default None)
    season -- Filter by year (default 0)
    basin -- Filter by basin (default None)
    basin can be one of "NA", "SA", "NI", "SI", "SP", "EP", or "WP".
    atcf_id -- Filter by ATCF ID (default None)
    ibtracs_id -- Filter by IBTrACS ID (default None)
    table -- Set preferred database table (default "LastThreeYears")
    table can be one of "LastThreeYears" or "AllBestTrack".
    At least one of the above keyword arguments (except for table) must be
    specified by the user.
    """
    if not os.path.exists(DB):
        raise FileNotFoundError("Best track database not found. Please call this module's init_db() function.")
    if table is not None and table not in ["LastThreeYears", "AllBestTrack"]:
        raise ValueError(f"Invalid table: {table}")
    conds_buff = io.StringIO()
    params = []
    if isinstance(basin, str):
        if basin.upper() not in ["NA", "SA", "NI", "SI", "SP", "EP", "WP"]:
            raise ValueError(f"Invalid basin: {basin}")
    if not isinstance(season, int):
        raise TypeError("season must be an integer")
    if name is not None:
        params.append(name.upper())
        conds_buff.write("NAME = ?")
    if season:
        if params:
            conds_buff.write(" AND ")
        params.append(season)
        conds_buff.write("SEASON = ?")
    if basin is not None:
        if params:
            conds_buff.write(" AND ")
        params.append(basin.upper())
        conds_buff.write(f"BASIN = ?")
    if atcf_id is not None:
        if params:
            conds_buff.write(" AND ")
        params.append(atcf_id.upper())
        conds_buff.write(f"USA_ATCF_ID = ?")
    if ibtracs_id is not None:
        if params:
            conds_buff.write(" AND ")
        params.append(ibtracs_id.upper())
        conds_buff.write(f"SID = ?")
    if not params:
        raise ValueError("Please specify at least one of name, season, basin, atcf_id, or ibtracs_id.")
    conds = conds_buff.getvalue()
    conds_buff.close()
    con = sqlite3.connect(DB)
    cur = con.cursor()
    if table is None:
        table = "LastThreeYears"
    log.debug(f"Conditions: {conds}")
    res = cur.execute(f"SELECT SID, SEASON, BASIN, NAME FROM {table} WHERE {conds}", params)
    data = res.fetchall()
    if not data:
        table = "AllBestTrack"
        res = cur.execute(f"SELECT SID, SEASON, BASIN, NAME FROM AllBestTrack WHERE {conds}", params)
        data = res.fetchall()
        if not data:
            return None
    storms = sorted(set(data)) # Deduplicate and sort data
    sid = storms[0][0]
    if len(storms) > 1:
        for storm in storms:
            if sid not in storm:
                con.close()
                return query_group(storms)
    params = [sid]
    res = cur.execute(f"SELECT USA_ATCF_ID, BASIN, MAX(USA_WIND), USA_PRES, ISO_TIME, NAME, SEASON FROM {table} WHERE SID = ? AND USA_WIND != ' ' AND NATURE != 'ET'", params)
    atcf_id, basin, wind, pres, time, name, season = res.fetchone()
    if pres == " ":
        params = [sid, time]
        res = cur.execute(f"SELECT WMO_PRES FROM {table} WHERE SID = ? and ISO_TIME = ?", params)
        pres = res.fetchone()[0]
    if name is None:
        params = [sid]
        res = cur.execute(f"SELECT USA_ATCF_ID, BASIN, MAX(WMO_WIND), WMO_PRES, ISO_TIME, NAME, SEASON FROM {table} WHERE SID = ? AND WMO_WIND != ' '", params)
        atcf_id, basin, wind, pres, time, name, season = res.fetchone()
        if name is None:
            res = cur.execute(f"SELECT USA_ATCF_ID, BASIN, MAX(USA_SSHS), WMO_PRES, ISO_TIME, NAME, SEASON FROM {table} WHERE SID = params")
            atcf_id, basin, sshs, pres, time, name, season = res.fetchone()
            wind = 0
    if pres == " ":
        pres = 0
    if atcf_id == " ":
        atcf_id = None
    con.close()
    return Storm(atcf_id, basin, wind, pres, time, name, sid, season)


# SQLite type conversions
def varchar(val: bytes):
    return val.decode("UTF-8")


def numeric(val):
    if not val:
        return None
    else:
        return float(val)


def bit(val):
    if not val:
        return None
    else:
        return int(val)


sqlite3.register_converter("BIT", bit)
sqlite3.register_converter("VARCHAR", varchar)
sqlite3.register_converter("NUMERIC", numeric)
