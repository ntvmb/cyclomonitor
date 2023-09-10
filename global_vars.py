## see server_vars.py for documentation on related functions

import json
import logging
json_file = 'globalVars.json'

def write(var_name: str,value):
    try:
        with open(json_file,'r') as f:
            data = json.load(f)
    except:
        data = {}
    data.update({var_name: value})
    with open(json_file,'w') as f:
        f.write(json.dumps(data, indent=4))

def get(var_name: str):
    try:
        with open(json_file,'r') as f:
            data = json.load(f)
    except:
        logging.exception("Cannot open JSON file")
        return None
    value = data.get(var_name)
    return value
