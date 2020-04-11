import os
import json

path=r'/Users/covid19warriors/Desktop/labware2'

for files in os.listdir(path):
    with open(os.path.join(path,files)) as file:
        a=json.load(file)
        print(a['parameters']['loadName'])
