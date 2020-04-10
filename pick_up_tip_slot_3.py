from opentrons import protocol_api

metadata = {'apiLevel': '2.0'}

def run(protocol):
    tiprack = protocol.load_labware('opentrons_96_filtertiprack_20ul', 3)
    pipette = protocol.load_instrument('p20_single_gen2', mount='right', tip_racks=[tiprack])

    pipette.pick_up_tip()
