import math
from opentrons.types import Point
from opentrons import protocol_api

# metadata
metadata = {
    'protocolName': 'Pipette testing',
    'author': 'Nick <protocols@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.0'
}

"""
REAGENT SETUP:

- slot 2 12-channel reservoir:
    - beads and isopropanol: channels 1-2
    - 70% ethanol: channels 4-5
    - nuclease-free water: channel 12

"""

NUM_SAMPLES = 16
transfer_volume = 310
pipette = 'p300_multi_gen2'
tip_model = 'opentrons_96_filtertiprack_200ul'

def run(ctx: protocol_api.ProtocolContext):

    # load labware and modules
    reagent_res = ctx.load_labware('nest_12_reservoir_15ml', '2',
                                       'reagent deepwell plate 1')

    deepwell2=reagent_res.load_labware('nest_12_reservoir_15ml','96-deepwell sample plate')

    # Load tip_racks
    tips = [
        ctx.load_labware(
            tip_model, slot, 'tiprack')
        for slot in [ '1']
    ]
    # Load pipette
    pip = ctx.load_instrument(pipette, 'right', tip_racks=tips) # Load multi pipette

    water = reagent_res.wells('A1')
    isopropanol = reagent_res.wells('A4')
    ethanol = reagent_res.wells('A6')
    beads = reagent_res.wells('A7')
    destinations = deepwell2.wells()[:NUM_SAMPLES]

    for dest in destinations:
        pip.pick_up_tip()
        pip.transfer(transfer_volume, water, deepwell2.wells()[0].top(), new_tip='never', air_gap=10)
        pip.touch_tip(speed=20, v_offset=-5, radius=0.9)
        pip.blow_out(deepwell.wells()[0].top())
        pip.drop_tip()
