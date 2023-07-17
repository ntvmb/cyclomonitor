# uptime module
import time
import math
start_time = time.time()
    
def process_uptime():
    return time.time() - start_time

def process_uptime_human_readable():
    t_uptime = math.floor(process_uptime())
    days = math.floor(t_uptime / 86400)
    hours = math.floor((t_uptime % 86400) / 3600)
    minutes = math.floor((t_uptime % 3600) / 60)
    seconds = math.floor(t_uptime % 60)
    if days > 0:
        p_days = str(days) + " days, "
    else:
        p_days = ""
    if hours > 0:
        p_hours = str(hours) + " hours, "
    else:
        p_hours = ""
    if minutes > 0:
        p_minutes = str(minutes) + " minutes, "
    else:
        p_minutes = ""
    return p_days + p_hours + p_minutes + str(seconds) + " seconds"