import pickle
import json
import sys
import os
from datetime import datetime
now = datetime.now()
timestamp = now.strftime("%y_%d_%m_%H_%M")

def key_to_json(data):
    if data is None or isinstance(data, (bool, int, float, str)):
        return data
    if isinstance(data, (tuple, frozenset)):
        return str(data)
    raise TypeError

def to_json(data):
    if data is None or isinstance(data, (bool, int, float, tuple, range, str, list)):
        return data
    if isinstance(data, (set, frozenset)):
        return sorted(data)
    if isinstance(data, dict):
        return {key_to_json(key): to_json(data[key]) for key in data}
    if isinstance(data, map):
        return list(data)
    if isinstance(data, datetime):
        return str(data)
    print(type(data))
    raise TypeError

# open pickle file
with open(sys.argv[1], 'rb') as infile:
    obj = pickle.load(infile)

# convert pickle object to json object
json_obj = json.loads(json.dumps(to_json(obj)))

# write the json file
with open(
        './backup_jsons/' + timestamp + os.path.splitext(sys.argv[1])[0] + '.json',
        'w',
        encoding='utf-8'
    ) as outfile:
    json.dump(json_obj, outfile, ensure_ascii=False, indent=4)
