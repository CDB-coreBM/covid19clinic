metadata = {
    "apiLevel": "2.2"
}

import json
import os
from pathlib import Path

new_mount_offset = [-34, 0, 0] # Equal to the hard-coded default that the OT-2 uses when the robot_settings file doesn't exist.
new_switch_clearance = 15 # Double the default of 7.5.

robot_settings_path = Path("/data/robot_settings.json")

def run(protocol):
    json_contents = json.loads(robot_settings_path.read_text())
    protocol.comment(f"Current mount offset: {json_contents['mount_offset']}")
    protocol.comment(f"Current tip probe switch clearance: {json_contents['tip_probe']['switch_clearance']}")
    protocol.comment(f"Run this script to set the mount offset to {new_mount_offset} and the tip probe switch clearance to {new_switch_clearance}.")
    if not protocol.is_simulating():
        json_contents["mount_offset"] = new_mount_offset
        json_contents["tip_probe"]["switch_clearance"] = new_switch_clearance
        robot_settings_path.write_text(json.dumps(json_contents, indent=4))
        os.sync()
        protocol.comment("Done.")
