# CycloMonitor Copyright (C) 2023 Nathaniel Greenwell
# This program comes with ABSOLUTELY NO WARRANTY; for details see main.py
import datetime
import calendar
import requests
import json

# initalize variables
url = 'https://www.nrlmry.navy.mil/tcdat/sectors/atcf_sector_file'
url_interp = 'https://www.nrlmry.navy.mil/tcdat/sectors/interp_sector_file'
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

class ATCFError(Exception):
    pass
def parse_storm(line: str, *, mode="std"):
    storm = line.split()
    if not mode == "interp":
        cyclones.append(storm[0])
        names.append(storm[1])
        time = storm[2] + storm[3]
        # convert the timestamp from the given data to Unix time
        timestamp = datetime.datetime(int('20'+time[0]+time[1]),int(time[2]+time[3]),int(time[4]+time[5]),int(time[6]+time[7]))
        utc_time = calendar.timegm(timestamp.utctimetuple())
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


def load():
    try:
        with open('atcf_sector_file','r') as file:
            for line in file:
                parse_storm(line)
    except Exception:
        return
    
    try:
        with open('interp_sector_file','r') as file:
            storms = []
            for line in file:
                storms.append(line.split())
            for tc in cyclones:
                for storm in storms:
                    cid = storm[0][2] + storm[0][3] + storm[6]
                    if cid == tc:
                        lats_real.append(float(storm[4]))
                        longs_real.append(float(storm[5]))
                        tc_classes.append(storm[7])
                        break
                else:
                    raise ATCFError("How did you get here?")
    except Exception:
        raise ATCFError("Failure to get interp data")

# load cached data upon bringing in the module
load()

def get_data():
    global cyclones, names, timestamps, lats, longs, basins, winds, pressures, tc_classes, lats_real, longs_real
    reset()
    try:
        ra = requests.get(url, verify=False)
        ri = requests.get(url_interp,verify=False)
    except:
        get_data_alt()
        return
    open('atcf_sector_file','wb').write(ra.content)
    open('interp_sector_file','wb').write(ri.content)
    load()
    # safeguard for some situations where the main ATCF website is down
    if len(cyclones) == 0:
        get_data_alt()    

def get_data_alt():
    global cyclones, names, timestamps, lats, longs, basins, winds, pressures, tc_classes, lats_real, longs_real
    reset()
    try:
        r = requests.get("https://api.knackwx.com/atcf/v1",verify=False)
    except:
        raise ATCFError("Failed to get ATCF data.")
    open('atcf_sector_file.tmp','wb').write(r.content)
    with open('atcf_sector_file.tmp','r') as f:
        tc_list = json.load(f)

    # for debugging
    with open('atcf_sector_file','w') as f:
        for d in tc_list:
            f.write(d.get('atcf_sector_file')+"\n")
    
    with open('interp_sector_file','w') as f:
        for d in tc_list:
            f.write(d.get('interp_sector_file')+"\n")

    for d in tc_list:
        parse_storm(d.get('atcf_sector_file'))
        parse_storm(d.get('interp_sector_file'),mode="interp")

def reset():
    global cyclones, names, timestamps, lats, longs, basins, winds, pressures, tc_classes, lats_real, longs_real
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
