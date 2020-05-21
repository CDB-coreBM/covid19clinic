#!/usr/bin/env python3
import subprocess
import os
import time
import shutil

# set path to watch
target_dir="/run/user/1003/gvfs/smb-share:server=opn.cdb.nas.csc.es,share=opentrons/RUNS/"
# set path to the script sh
script_path="/run/user/1003/gvfs/smb-share:server=opn.cdb.nas.csc.es,share=opentrons/code/covid19clinic/automation/KF_config/rmarkdown_runner.sh"

def generate_list_folders(target_dir):
    dirs = os.listdir(target_dir)
    dirs_return = dirs.copy()
    for d in dirs:
        for file in os.listdir(target_dir+d+'/results/'):
            if file.endswith('.html'):
                dirs_return.remove(d)
                break
    return dirs_return

watching = []
while True:
    time.sleep(10)
    runs = generate_list_folders(target_dir)
    for run in runs:
        if run not in watching:
            watching.append(run)
            os.system(script_path + ' '+ run)
