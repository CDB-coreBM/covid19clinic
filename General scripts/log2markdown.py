from pytablewriter import MarkdownTableWriter
import json

path='/Users/covid19warriors/Documents/covid19clinic/Station_B/station_b_log_17_4_2020.json'

with open(path) as f:
    data=json.load(f)

steps=data.keys()
print(steps)

values=[]
for s in steps:
    values.append(data[s]["Time:"])


def get_sec(time_str):
    """Get Seconds from time."""
    h, m, s = time_str.split(':')
    return int(h) * 3600 + int(m) * 60 + int(s[:1])

v=0
for val in values:
    v=v+(get_sec(val))
print(v)
