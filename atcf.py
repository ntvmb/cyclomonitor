import datetime
import calendar
import requests
import json

url = 'https://www.nrlmry.navy.mil/tcdat/sectors/atcf_sector_file'

class ATCFError(Exception):
    pass

def get_data():
    global cyclones, names, timestamps, lats, longs, basins, winds, pressures
    cyclones = []
    names = []
    timestamps = []
    lats = []
    longs = []
    basins = []
    winds = []
    pressures = []
    try:
        r = requests.get(url, verify=False)
    except:
        get_data_alt()
        return
    open('atcf_sector_file','wb').write(r.content)
    file = open('atcf_sector_file',mode='r')
    for line in file:
        storm = line.split()
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
    if len(cyclones) == 0:
        get_data_alt()

def get_data_alt():
    global cyclones, names, timestamps, lats, longs, basins, winds, pressures
    cyclones = []
    names = []
    timestamps = []
    lats = []
    longs = []
    basins = []
    winds = []
    pressures = []
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

    for d in tc_list:
        storm = d.get('atcf_sector_file').split()
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

def reset():
    global cyclones, names, timestamps, lats, longs, basins, winds, pressures
    cyclones = []
    names = []
    timestamps = []
    lats = []
    longs = []
    basins = []
    winds = []
    pressures = []