import json
json_file = 'serverVars.json'

def write(var_name: str,value,guild: int):
    try:
        with open(json_file,'r') as f:
            data = json.load(f)
    except:
        data = []
    for i in data:
        if not i.get(str(guild)) == None:
            server_data = i.get(str(guild))
            server_data.update({var_name: value})
            break
    else:
        data.append({
            str(guild): {
                var_name: value
            }
        })
    if len(data) == 0:
        data.append({
            str(guild): {
                var_name: value
            }
        })
    with open(json_file,'w') as f:
        f.write(json.dumps(data, indent=4))

def get(var_name: str,guild: int):
    try:
        with open(json_file,'r') as f:
            data = json.load(f)
    except:
        print("Warning: Cannot open JSON file")
        return None
    for i in data:
        if not i.get(str(guild)) == None:
            server_data = i.get(str(guild))
            value = server_data.get(var_name)
            return value
    return None

def remove_guild(guild: int):
    try:
        with open(json_file,'r') as f:
            data = json.load(f)
    except:
        print("Warning: Cannot open JSON file")
        return None
    for i in data:
        if not i.get(str(guild)) == None:
            data.remove(i)
            with open(json_file,'w') as f:
                f.write(json.dumps(data, indent=4))
