import math
from opentrons.types import Point
from opentrons import protocol_api

# metadata
metadata = {
    'protocolName': 'S2 Station B Version 1',
    'author': 'Nick <protocols@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.0'
}

"""
REAGENT SETUP:

- slot 2 12-channel reservoir:
    - viral DNA/RNA buffer: channels 1-3
    - magbeads: channel 4
    - wash 1: channels 5-8
    - wash 2: channels 9-12

- slot 5 12-channel reservoir:
    - EtOH: channels 1-8
    - water: channel 12

"""

NUM_SAMPLES = 30


def run(ctx: protocol_api.ProtocolContext):

    # load labware and modules
    tempdeck = ctx.load_module('tempdeck', '1')
    elution_plate = tempdeck.load_labware(
        'roche_96_wellplate_100ul',
        'tempered elution plate')
    reagent_res1 = ctx.load_labware(
        'nunc_96_wellplate_2000ul', '2', 'reagent reservoir 1')
    magdeck = ctx.load_module('magdeck', '4')
    magplate = magdeck.load_labware(
        'roche_96_deepwellplate_1000ul', '96-deepwell sample plate')
    reagent_res2 = ctx.load_labware(
        'nunc_96_wellplate_2000ul', '5', 'reagent reservoir 2')
    waste = ctx.load_labware(
        'nalgene_1_reservoir_300000ul', '7', 'waste reservoir').wells()[0].top()
    tips300 = [
        ctx.load_labware(
            'opentrons_96_filtertiprack_200ul', slot, '300µl tiprack')
        for slot in ['3', '6', '8', '9', '10', '11']
    ]

    # reagents and samples
    num_cols = math.ceil(NUM_SAMPLES/8)
    mag_samples_m = [
        well for well in
        magplate.rows()[0][0::2] + magplate.rows()[0][1::2]][:num_cols]
    elution_samples_m = [
        well for well in
        elution_plate.rows()[0][0::2] + magplate.rows()[0][1::2]][:num_cols]

    viral_dna_rna_buff = reagent_res1.wells()[:3]
    beads = reagent_res1.wells()[3]
    wash_1 = reagent_res1.wells()[4:8]
    wash_2 = reagent_res1.wells()[8:]
    etoh = reagent_res2.wells()[:8]
    water = reagent_res2.wells()[-1]

    # pipettes
    m300 = ctx.load_instrument('p300_multi_gen2', 'right', tip_racks=tips300)
    m300.flow_rate.aspirate = 150
    m300.flow_rate.dispense = 300

    tip_counts = {m300: 0}
    tip_maxes = {m300: len(tips300)*12}

    magdeck.engage(height=1)
    magdeck.disengage()
