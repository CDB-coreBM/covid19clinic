import math
from opentrons.types import Point
from opentrons import protocol_api

# metadata
metadata = {
    'protocolName': 'Pipette testing',
    'author': 'JL Villanueva (jlvillanueva@clinic.cat)',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.0'
}

"""
REAGENT SETUP:

- slot 2 12-channel reservoir:
    - Water_ channel 1
    - Isopropanol: channel 4
    - 70% ethanol: channel 6
    - Beads: channel 7

"""

NUM_SAMPLES = 24
transfer_volume = 195
air_gap = 5
pipette = 'p300_multi_gen2'
position = 'right' # 'left'
tip_model = 'biotix_96_tiprack_300ul_flat'
num_cols = math.ceil(NUM_SAMPLES/8)

def run(ctx: protocol_api.ProtocolContext):

    # load labware and modules
    reagent_res = ctx.load_labware('nest_12_reservoir_15ml', '2',
                                       'reagent deepwell plate 1')

    deepwell=ctx.load_labware('kf_96_wellplate_2400ul','3','96-deepwell sample plate')

    # Load tip_racks
    tips = [
        ctx.load_labware(
            tip_model, slot, 'tiprack')
        for slot in [ '1']
    ]
    # Load pipette
    pip = ctx.load_instrument(pipette, position, tip_racks=tips) # Load multi pipette

    water = reagent_res.wells('A1')
    isopropanol = reagent_res.wells('A4')
    ethanol = reagent_res.wells('A6')
    beads = reagent_res.wells('A7')
    destinations = deepwell.wells()[:NUM_SAMPLES]
    destinations_multi = deepwell.rows()[0][:num_cols]

    if 'multi' in pipette:
        dests=destinations_multi
    else:
        dests=destinations
    for dest in dests:
        pip.pick_up_tip()
        pip.transfer(transfer_volume, water, dest.top(), new_tip='never', air_gap = air_gap)
        pip.touch_tip(speed=20, v_offset=-5, radius=0.9)
        pip.blow_out()
        pip.drop_tip()
