NEW_SERIAL_NUMBER = "S2-A2"

from opentrons import robot
import os

robot.comment(f"Setting serial number to {NEW_SERIAL_NUMBER}.")

if not robot.is_simulating():
    with open("/var/serial", "w") as serial_number_file:
        serial_number_file.write(NEW_SERIAL_NUMBER + "\n")
    with open("/etc/machine-info", "w") as serial_number_file:
        serial_number_file.write(f"DEPLOYMENT=production\nPRETTY_HOSTNAME={NEW_SERIAL_NUMBER}\n")
    with open("/etc/hostname", "w") as serial_number_file:
        serial_number_file.write(NEW_SERIAL_NUMBER + "\n")

    os.sync()

    robot.comment("Done.")
