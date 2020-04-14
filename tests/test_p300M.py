import math
from opentrons.types import Point
from opentrons import protocol_api

# metadata
metadata = {
    'protocolName': 'S2 Station B Version 2',
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

#NUM_SAMPLES = 16
transfer_volume = 310

def run(ctx: protocol_api.ProtocolContext):

    # load labware and modules
    reagent_res = ctx.load_labware('nest_12_reservoir_15ml', '2',
                                       'reagent deepwell plate 1')

    deepwell = ctx.load_labware('nunc_96_wellplate_2000ul', '3','96-deepwell sample plate')

    # Load tip_racks
    tips300 = [
        ctx.load_labware(
            'opentrons_96_tiprack_300ul', slot, '200µl filter tiprack')
        for slot in [ '1']
    ]
    # Load pipette
    m300 = ctx.load_instrument('p300_multi_gen2', 'right', tip_racks=tips300) # Load multi pipette

    water = reagent_res.wells('A1')
    isopropanol = reagent_res.wells('A4')
    ethanol = reagent_res.wells('A6')
    beads = reagent_res.wells('A7')

    m300.pick_up_tip()
    m300.transfer(transfer_volume, beads, deepwell.wells()[0].top(), new_tip='never', air_gap=10)
    m300.touch_tip(speed=20, v_offset=-5,radius=1.05)
    m300.blow_out(deepwell.wells()[0].top())
    m300.transfer(transfer_volume, beads, deepwell.wells()[8].top(), new_tip='never', air_gap=10)
    m300.touch_tip(speed=20, v_offset=-5,radius=1.05)
    m300.blow_out(deepwell.wells()[8].top())
    m300.drop_tip()
