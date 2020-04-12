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

mag_height=13 # Height needed for NUNC deepwell in magnetic deck
NUM_SAMPLES = 30

# Prompt user to change the tiprack

def run(ctx: protocol_api.ProtocolContext):

    # load labware and modules
    reagent_res = ctx.load_labware('nest_12_reservoir_15ml', '2',
                                       'reagent deepwell plate 1')

    tempdeck = ctx.load_module('tempdeck', '3')

    elution_plate = tempdeck.load_labware(
        'transparent_96_wellplate_250ul',
        'cooled elution plate')

    magdeck = ctx.load_module('magdeck', '6')
    magplate = magdeck.load_labware(
        'nunc_96_wellplate_2000ul', '96-deepwell sample plate')

    waste = ctx.load_labware(
        'nalgene_1_reservoir_300000ul', '9', 'waste reservoir').wells()[0].top()

    # Load tip_racks
    tips300 = [
        ctx.load_labware(
            'opentrons_96_tiprack_300ul', slot, '200µl filter tiprack')
        for slot in [ '5', '8', '11']
    ]
    tips1000 = [
        ctx.load_labware(
            'opentrons_96_filtertiprack_1000ul', slot, '1000µl filter tiprack')
        for slot in ['1','4','7', '10']
    ]

    def pick_up(pip):
        nonlocal tip_track
        if tip_track['counts'][pip] == tip_track['maxes'][pip]:
            ctx.pause('Replace ' + str(pip.max_volume) + 'µl tipracks before \
            resuming.')
            pip.reset_tipracks()
            tip_track['counts'][pip] = 0
        tip_track['counts'][pip] += 1
        pip.pick_up_tip()

    def remove_supernatant(pip, vol):
        if pip == p1000:
            for i, s in enumerate(mag_samples_s):
                side = -1 if i < 48 == 0 else 1
                loc = s.bottom(0.5).move(Point(x=side*2))
                pick_up(p1000)
                p1000.move_to(s.center())
                p1000.transfer(vol, loc, waste, new_tip='never', air_gap=100)
                p1000.blow_out(waste)
                p1000.drop_tip()

        else:
            m300.flow_rate.aspirate = 30
            for i, m in enumerate(mag_samples_m):
                side = -1 if i < 6 == 0 else 1
                loc = m.bottom(0.5).move(Point(x=side*2))
                if not m300.hw_pipette['has_tip']:
                    pick_up(m300)
                m300.move_to(m.center())
                m300.transfer(vol, loc, waste, new_tip='never', air_gap=20)
                m300.blow_out(waste)
                m300.drop_tip()
            m300.flow_rate.aspirate = 150

    # reagents and samples
    num_cols = math.ceil(NUM_SAMPLES/8) # Columnas de trabajo
    mag_samples_m = [
        well for well in
        magplate.rows()[0][0::2] + magplate.rows()[0][1::2]][:num_cols]
    mag_samples_s = [
        well for col in [
            c for set in [magplate.columns()[i::2] for i in range(2)]
            for c in set]
        for well in col][:NUM_SAMPLES]
    elution_samples_m = [
        well for well in
        elution_plate.rows()[0][0::2] + magplate.rows()[0][1::2]][:num_cols]

    beads = reagent_res.rows()[0][:2] # 1 row, 2 columns (first ones)
    etoh = reagent_res.rows()[0][3:5] # 1 row, 2 columns (from 3 to 5); there's a space
    water = reagent_res.rows()[0][-1] # 1 row, 1 column (last ones) full of water

    # pipettes
    m300 = ctx.load_instrument('p300_multi_gen2', 'right', tip_racks=tips300) # Load multi pipette
    p1000 = ctx.load_instrument('p1000_single_gen2', 'left', tip_racks=tips1000) # load P1000 pipette

    ##### FLOW RATES #######
    m300.flow_rate.aspirate = 150
    m300.flow_rate.dispense = 300
    m300.flow_rate.blow_out = 300
    p1000.flow_rate.aspirate = 100
    p1000.flow_rate.dispense = 1000

    #### used tip counter and set maximum tips available
    tip_track = {
        'counts': {m300: 0, p1000: 0},
        'maxes': {m300: len(tips300)*12, p1000: len(tips1000)*96}
    }

###############################################################################
    # premix, transfer, and mix magnetic beads with sample
    for i, m in enumerate(mag_samples_m):
        # STEP 1 MIX BEADS WITH ISOPROPANOL
        ########
        pick_up(m300)
        if i == 0 or i == 6:

            for _ in range(20):
                m300.aspirate(200, beads[i//6].bottom(3))
                m300.dispense(200, beads[i//6].bottom(20))
        # STEP 2 TRANSFER BEADS AND ISOPROPANOL TO DEEPWELL PLATE
        ########
        for _ in range(2):
            m300.transfer(310/2, beads[i//8], m.top(), new_tip='never')
        m300.mix(10, 200, m)
        m300.blow_out(m.top(-2))
        m300.aspirate(20, m.top(-2))
        m300.drop_tip()

###############################################################################
# STEP 3 INCUBATE WITHOUT MAGNET
########
    # incubate off and on magnet
    ctx.delay(minutes=5, msg='Incubating off magnet for 5 minutes.')
###############################################################################

# STEP 4 INCUBATE WITH MAGNET
########
    magdeck.engage(height=mag_height)
    ctx.delay(minutes=5, msg='Incubating on magnet for 5 minutes.')
###############################################################################

# STEP 5 REMOVE SUPERNATANT
########
    # remove supernatant
    remove_supernatant(p1000, 620)
###############################################################################

    # WASH 2 TIMES
########
    # 70% EtOH washes
    for wash in range(2):
        # transfer EtOH
        # STEP 6  ADD AND CLEAN WITH ETOH [STEP 9]
        ########
        for m in mag_samples_m:
            side = -1 if i < 48 == 0 else 1
            loc = m.bottom(0.5).move(Point(x=side*2))
            pick_up(m300)
            m300.aspirate(200, etoh[wash])
            m300.aspirate(30, etoh[wash].top())
            m300.move_to(m.center())
            m300.dispense(30, m.center())
            m300.dispense(200, loc)
            m300.drop_tip()

        ####################################################################
        # STEP 7 WAIT FOR 30s-1' [STEP 10]
        ########
        ctx.delay(seconds=30, msg='Incubating for 30 seconds.')
        ####################################################################

        # STEP 8 REMOVE SUPERNATANT [STEP 11]
        ########
        remove_supernatant(m300, 210)
        ####################################################################


# STEP 12 DRY
########
    ctx.delay(minutes=5, msg='Airdrying beads for 5 minutes.')
###############################################################################
    magdeck.disengage()

# STEP 13 ADD LTA & WATER
########
    # transfer and mix water
    for m in mag_samples_m:
        pick_up(m300)
        side = 1 if i < 6 == 0 else -1
        loc = m.bottom(0.5).move(Point(x=side*2))
        m300.transfer(50, water, m.center(), new_tip='never')
        m300.mix(10, 30, loc)
        m300.blow_out(m.top(-2))
        m300.drop_tip()
###############################################################################

# STEP 14 WAIT 1-2' WITHOUT MAGNET
########
    ctx.delay(minutes=2, msg='Incubating on magnet for 2 minutes.')
###############################################################################

# STEP 15 WAIT 5' WITH MAGNET
########
    magdeck.engage(height=mag_height)
    ctx.delay(minutes=5, msg='Incubating on magnet for 5 minutes.')
###############################################################################

# STEP 16 TRANSFER TO ELUTION PLATE
########
    # transfer elution to clean plate
    m300.flow_rate.aspirate = 30
    for s, d in zip(mag_samples_m, elution_samples_m):
        pick_up(m300)
        side = -1 if i < 6 == 0 else 1
        loc = s.bottom(0.5).move(Point(x=side*2))
        m300.transfer(45, loc, d, new_tip='never')
        m300.blow_out(d.top(-2))
        m300.drop_tip()
    m300.flow_rate.aspirate = 150
###############################################################################
