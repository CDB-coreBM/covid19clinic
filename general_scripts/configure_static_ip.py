STATIC_IP = "169.254.1.3/16"

keyfile_contents = f"""\
# This file was placed here by Opentrons Support to work around suspected issues with mDNS.
# Normally, IP addresses are assigned dynamically by the "wired-linklocal" or "wired" connection.
# This overrides both of those to set a known, static IP address.

[connection]
id=support-team-wired-static-ip
type=ethernet
autoconnect-priority=20
interface-name=eth0
permissions=

[ethernet]
cloned-mac-address=permanent
mac-address-blacklist=

[ipv4]
dns-search=
method=manual
addresses={STATIC_IP}
"""

from opentrons import robot
import os

robot.comment(f"Run this protocol to permanently set the wired IP address of your OT-2 to {STATIC_IP}.")

if not robot.is_simulating():
	with open("/var/lib/NetworkManager/system-connections/support-team-wired-static-ip", "w") as keyfile:
		keyfile.write(keyfile_contents)
	os.sync()
	robot.comment("Done.")

robot.comment("Restart your OT-2 to apply the changes.")
