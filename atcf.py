import datetime
import calendar
import requests

url = 'https://www.nrlmry.navy.mil/tcdat/sectors/atcf_sector_file'

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
    r = requests.get(url, verify=False)
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