import math
from opentrons.types import Point
from opentrons import protocol_api
import time
import os
import numpy as np
from timeit import default_timer as timer
import json
from datetime import datetime
import csv

# metadata
metadata = {
    'protocolName': 'S2 Station Kingfisher Version 1',
    'author': 'Aitor Gastaminza & José Luis Villanueva (jlvillanueva@clinic.cat)',
    'source': 'Hospital Clínic Barcelona',
    'apiLevel': '2.0',
    'description': 'Protocol for Kingfisher sample setup (A)'
}

#Defined variables
##################
NUM_SAMPLES = 96
air_gap_vol = 15

temperature = 25
D_deepwell = 6.9  # Deepwell diameter (ABGENE deepwell)
# D_deepwell = 8.35 # Deepwell diameter (NUNC deepwell)
multi_well_rack_area = 8 * 71  # Cross section of the 12 well reservoir

#Calculated variables
deepwell_cross_section_area = math.pi * D_deepwell**2 / 4  # deepwell cilinder cross secion area
num_cols = math.ceil(NUM_SAMPLES / 8)  # Columns we are working on

def run(ctx: protocol_api.ProtocolContext):
    ctx.comment('Actual used columns: ' + str(num_cols))
    STEP = 0
    STEPS = {  # Dictionary with STEP activation, description, and times
        1: {'Execute': True, 'description': '1: Add proteinase K (10ul)'},
        2: {'Execute': True, 'description': '2: Add internal control (10ul)'},
        3: {'Execute': True, 'description': '3: Add samples (300ul)'},
        4: {'Execute': True, 'description': '4: Add binding buffer (550ul)'}
    }

    for s in STEPS:  # Create an empty wait_time
        if 'wait_time' not in STEPS[s]:
            STEPS[s]['wait_time'] = 0

    #Folder and file_path for log time
    folder_path = '/data/log_times/'
    if not os.path.isdir(folder_path):
        os.mkdir(folder_path)
    file_path = folder_path + '/time_log.json'

    # Define Reagents as objects with their properties
    class Reagent:
        def __init__(self, name, flow_rate_aspirate, flow_rate_dispense, rinse,
                     reagent_reservoir_volume, num_wells, h_cono, v_fondo, tip_recycling='none'):
            self.name = name
            self.flow_rate_aspirate = flow_rate_aspirate
            self.flow_rate_dispense = flow_rate_dispense
            self.rinse = bool(rinse)
            self.reagent_reservoir_volume = reagent_reservoir_volume
            self.num_wells = num_wells
            self.col = 0
            self.vol_well = 0
            self.h_cono = h_cono
            self.v_cono = v_fondo
            self.tip_recycling = tip_recycling
            self.vol_well_original = reagent_reservoir_volume / num_wells

    # Reagents and their characteristics
    Buffer = Reagent(name = 'Buffer',
                      flow_rate_aspirate = 0.5,
                      flow_rate_dispense = 1,
                      rinse = True,
                      reagent_reservoir_volume = 38400,
                      num_wells = 1,  # num_Wells max is 4
                      h_cono = 1.95,
                      v_fondo = 1.95 * multi_well_rack_area / 2,  # Prismatic
                      tip_recycling = 'A1')

    ProtK = Reagent(name = 'Proteinase K',
                       flow_rate_aspirate = 0.5,
                       flow_rate_dispense = 1,
                       rinse = True,
                       reagent_reservoir_volume = 38400,
                       num_wells = 2,  # num_Wells max is 4
                       h_cono = 1.95,
                       v_fondo = 1.95 * multi_well_rack_area / 2,  # Prismatic
                       tip_recycling = 'A1')

    Control_I = Reagent(name = 'Internal Control',
                     flow_rate_aspirate = 0.5,
                     flow_rate_dispense = 1,
                     rinse = True,
                     reagent_reservoir_volume = 38400,
                     num_wells = 2,  # num_Wells max is 4
                     h_cono = 1.95,
                     v_fondo = 1.95 * multi_well_rack_area / 2,  # Prismatic
                     tip_recycling = 'A1')

    Samples = Reagent(name = 'Samples',
                      flow_rate_aspirate = 0.5,
                      flow_rate_dispense = 1,
                      rinse = False,
                      reagent_reservoir_volume = 800,
                      num_wells = 24,  # num_cols comes from available columns
                      h_cono = 4,
                      v_fondo = 4 * math.pi * 4**3 / 3)  # Sphere

    Buffer.vol_well = Buffer.vol_well_original
    ProtK.vol_well = ProtK.vol_well_original
    Control_I.vol_well = Control_I.vol_well_original
    Samples.vol_well = 700

    ##################
    # Custom functions
    def custom_mix(pipet, reagent, location, vol, rounds, blow_out, mix_height):
        '''
        Function for mix in the same location a certain number of rounds. Blow out optional
        '''
        if mix_height == 0:
            mix_height = 3
        pipet.aspirate(1, location=location.bottom(
            z=3), rate=reagent.flow_rate_aspirate)
        for _ in range(rounds):
            pipet.aspirate(vol, location=location.bottom(
                z=3), rate=reagent.flow_rate_aspirate)
            pipet.dispense(vol, location=location.bottom(
                z=mix_height), rate=reagent.flow_rate_dispense)
        pipet.dispense(1, location=location.bottom(
            z=mix_height), rate=reagent.flow_rate_dispense)
        if blow_out == True:
            pipet.blow_out(location.top(z=-2))  # Blow out

    def calc_height(reagent, cross_section_area, aspirate_volume):
        nonlocal ctx
        ctx.comment('Remaining volume ' + str(reagent.vol_well) +
                    '< needed volume ' + str(aspirate_volume) + '?')
        if reagent.vol_well < aspirate_volume:
            ctx.comment('Next column should be picked')
            ctx.comment('Previous to change: ' + str(reagent.col))
            # column selector position; intialize to required number
            reagent.col = reagent.col + 1
            ctx.comment(str('After change: ' + str(reagent.col)))
            reagent.vol_well = reagent.vol_well_original
            ctx.comment('New volume:' + str(reagent.vol_well))
            height = (reagent.vol_well - aspirate_volume -
                      reagent.v_cono) / cross_section_area - reagent.h_cono
            reagent.vol_well = reagent.vol_well - aspirate_volume
            ctx.comment('Remaining volume:' + str(reagent.vol_well))
            if height < 0:
                height = 0.5
            col_change = True
        else:
            height = (reagent.vol_well - aspirate_volume -
                      reagent.v_cono) / cross_section_area - reagent.h_cono
            reagent.vol_well = reagent.vol_well - aspirate_volume
            ctx.comment('Calculated height is ' + str(height))
            if height < 0:
                height = 0.5
            ctx.comment('Used height is ' + str(height))
            col_change = False
        return height, col_change

    def move_vol_multi(pipet, reagent, source, dest, vol, air_gap_vol, x_offset,
                       pickup_height, rinse):
        # Rinse before aspirating
        if rinse == True:
            custom_mix(pipet, reagent, location = source, vol = vol,
                       rounds = 2, blow_out = True, mix_height = 0)
        # SOURCE
        s = source.bottom(pickup_height).move(Point(x = x_offset))
        pipet.aspirate(vol, s)  # aspirate liquid
        if air_gap_vol != 0:  # If there is air_gap_vol, switch pipette to slow speed
            pipet.aspirate(air_gap_vol, source.top(z = -2),
                           rate = reagent.flow_rate_aspirate)  # air gap
        # GO TO DESTINATION
        pipet.dispense(vol + air_gap_vol, dest.top(z = -2),
                       rate = reagent.flow_rate_dispense)  # dispense all
        pipet.blow_out(dest.top(z = -2))
        if air_gap_vol != 0:
            pipet.aspirate(air_gap_vol, dest.top(z = -2),
                           rate = reagent.flow_rate_aspirate)  # air gap

    ##########
    # pick up tip and if there is none left, prompt user for a new rack
    def pick_up(pip):
        nonlocal tip_track
        if not ctx.is_simulating():
            if tip_track['counts'][pip] == tip_track['maxes'][pip]:
                ctx.pause('Replace ' + str(pip.max_volume) + 'µl tipracks before \
                resuming.')
                pip.reset_tipracks()
                tip_track['counts'][pip] = 0
        pip.pick_up_tip()

    ####################################
    # load labware and modules

    ####################################
    # Load Sample racks
    if NUM_SAMPLES<96:
        rack_num=math.ceil(NUM_SAMPLES/24)
        ctx.comment('Used source racks are '+str(rack_num))
        samples_last_rack=NUM_SAMPLES-rack_num*24

    source_racks = [ctx.load_labware(
            'opentrons_24_tuberack_generic_2ml_screwcap', slot,
            'source tuberack with screwcap' + str(i+1)) for i, slot in enumerate(['4','1','6','3'][:rack_num])
        ]

    ##################################
    # Destination plate
    dest_plate = ctx.load_labware(
        'abgenestorage_96_wellplate_1200ul', '5', '96well destination plate')

    ############################################
    # tempdeck
    tempdeck = ctx.load_module('tempdeck', '7')
    #tempdeck.set_temperature(temperature)

    ##################################
    # Cooled reagents in tempdeck
    reagents = tempdeck.load_labware(
        'bloquealuminio_24_screwcap_wellplate_1500ul',
        'cooled reagent tubes')

    ############################################
    # Buffer reservoir
    buffer_res = ctx.load_labware(
        'nalgene_1_reservoir_300000ul', '9', 'buffer reservoir')


    ####################################
    # Load tip_racks
    tips20 = [ctx.load_labware('opentrons_96_filtertiprack_20ul', slot, '20µl filter tiprack')
               for slot in ['2', '8']]
    tips1000 = [ctx.load_labware('opentrons_96_filtertiprack_1000ul', slot, '1000µl filter tiprack')
        for slot in ['10','11']]


    ################################################################################
    # Declare which reagents are in each reservoir as well as deepwell and elution plate
    Beads.reagent_reservoir = reagent_res.rows(
    )[0][:Beads.num_wells]  # 1 row, 4 columns (first ones)
    Isopropanol.reagent_reservoir = reagent_res.rows()[0][4:(
        4 + Isopropanol.num_wells)]  # 1 row, 2 columns (from 5 to 6)
    Ethanol.reagent_reservoir = reagent_res.rows()[0][6:(
        6 + Ethanol.num_wells)]  # 1 row, 2 columns (from 7 to 10)
    # 1 row, 1 column (last one) full of water
    Buffer.reagent_reservoir = buffer_res.rows()[0]
    work_destinations = deepwell_plate.rows()[0][:Elution.num_wells]
    final_destinations = elution_plate.rows()[0][:Elution.num_wells]

    p20 = ctx.load_instrument(
        'p20_single_gen2', mount='right', tip_racks=tips20)
    p1000 = ctx.load_instrument('p1000_single_gen2', 'left', tip_racks=tips1000) # load P1000 pipette

    # used tip counter and set maximum tips available
    tip_track = {
        'counts': {m300: 0},
        'maxes': {m300: 10000}
    }
    # , p1000: len(tips1000)*96}

    ############################################################################
    # STEP 1: PREMIX BEADS
    ############################################################################
    STEP += 1
    if STEPS[STEP]['Execute'] == True:

        start = datetime.now()
        ctx.comment('Step ' + str(STEP) + ': ' + STEPS[STEP]['description'])
        ctx.comment('###############################################')
        if not m300.hw_pipette['has_tip']:
            pick_up(m300)  # These tips are reused in the first transfer of beads
            ctx.comment('Tip picked up')
        ctx.comment('Mixing ' + Beads.name)

        # Mixing
        custom_mix(m300, Beads, Beads.reagent_reservoir[Beads.col], vol=180,
                   rounds=10, blow_out=True, mix_height=0)
        ctx.comment('Finished premixing!')
        ctx.comment('Now, reagents will be transferred to deepwell plate.')

        end = datetime.now()
        time_taken = (end - start)
        ctx.comment('Step ' + str(STEP) + ': ' +
                    STEPS[STEP]['description'] + ' took ' + str(time_taken))
        STEPS[STEP]['Time:'] = str(time_taken)

    ############################################################################
    # STEP 2: TRANSFER BEADS
    ############################################################################
    STEP += 1
    if STEPS[STEP]['Execute'] == True:
        # Transfer parameters
        start = datetime.now()
        ctx.comment('Step ' + str(STEP) + ': ' + STEPS[STEP]['description'])
        ctx.comment('###############################################')
        beads_transfer_vol = [155, 155]  # Two rounds of 155
        x_offset = 0
        rinse = True
        for i in range(num_cols):
            if not m300.hw_pipette['has_tip']:
                pick_up(m300)
            for j, transfer_vol in enumerate(beads_transfer_vol):
                # Calculate pickup_height based on remaining volume and shape of container
                [pickup_height, change_col] = calc_height(
                    Beads, multi_well_rack_area, transfer_vol * 8)
                if change_col == True:  # If we switch column because there is not enough volume left in current reservoir column we mix new column
                    ctx.comment(
                        'Mixing new reservoir column: ' + str(Beads.col))
                    custom_mix(m300, Beads, Beads.reagent_reservoir[Beads.col],
                               vol=180, rounds=10, blow_out=True, mix_height=0)
                ctx.comment(
                    'Aspirate from reservoir column: ' + str(Beads.col))
                ctx.comment('Pickup height is ' + str(pickup_height))
                if j != 0:
                    rinse = False
                move_vol_multi(m300, reagent=Beads, source=Beads.reagent_reservoir[Beads.col],
                               dest=work_destinations[i], vol=transfer_vol, air_gap_vol=air_gap_vol, x_offset=x_offset,
                               pickup_height=pickup_height, rinse=rinse)

            ctx.comment('Mixing sample with beads ')
            custom_mix(m300, Beads, location=work_destinations[i], vol=180,
                       rounds=4, blow_out=True, mix_height=16)
            m300.drop_tip(home_after=False)
            # m300.return_tip()
            tip_track['counts'][m300] += 8
        end = datetime.now()
        time_taken = (end - start)
        ctx.comment('Step ' + str(STEP) + ': ' +
                    STEPS[STEP]['description'] + ' took ' + str(time_taken))
        STEPS[STEP]['Time:'] = str(time_taken)

        ctx.comment('Now incubation will start ')

    ############################################################################
    # STEP 3 INCUBATE WITHOUT MAGNET
    ############################################################################

    STEP += 1
    if STEPS[STEP]['Execute'] == True:
        start = datetime.now()
        ctx.comment('Step ' + str(STEP) + ': ' + STEPS[STEP]['description'])
        ctx.comment('###############################################')
        # incubate off and on magnet
        magdeck.disengage()
        ctx.delay(seconds=STEPS[STEP]['wait_time'], msg='Incubating OFF magnet for ' +
                  format(STEPS[STEP]['wait_time']) + ' seconds.')  # minutes=2
        end = datetime.now()
        time_taken = (end - start)
        ctx.comment('Step ' + str(STEP) + ': ' +
                    STEPS[STEP]['description'] + ' took ' + str(time_taken))
        STEPS[STEP]['Time:'] = str(time_taken)

    ############################################################################
    # STEP 4 INCUBATE WITH MAGNET
    ############################################################################

    STEP += 1
    if STEPS[STEP]['Execute'] == True:
        start = datetime.now()
        ctx.comment('Step ' + str(STEP) + ': ' + STEPS[STEP]['description'])
        ctx.comment('###############################################')
        magdeck.engage(height=mag_height)
        ctx.delay(seconds=STEPS[STEP]['wait_time'], msg='Incubating ON magnet for ' +
                  format(STEPS[STEP]['wait_time']) + ' seconds.')  # minutes=2

        end = datetime.now()
        time_taken = (end - start)
        ctx.comment('Step ' + str(STEP) + ': ' +
                    STEPS[STEP]['description'] + ' took ' + str(time_taken))
        STEPS[STEP]['Time:'] = str(time_taken)

    ############################################################################
    # STEP 5 REMOVE SUPERNATANT
    ############################################################################

    STEP += 1
    if STEPS[STEP]['Execute'] == True:
        start = datetime.now()

        ctx.comment('Step ' + str(STEP) + ': ' + STEPS[STEP]['description'])
        ctx.comment('###############################################')

        # remove supernatant -> height calculation can be omitted and referred to bottom!
        supernatant_vol = [160, 160, 160, 160]
        x_offset_rs = 2

        for i in range(num_cols):
            x_offset = find_side(i) * x_offset_rs
            if not m300.hw_pipette['has_tip']:
                pick_up(m300)
            for transfer_vol in supernatant_vol:
                # Pickup_height is fixed here
                pickup_height = 0.5
                ctx.comment('Aspirate from deep well column: ' + str(i + 1))
                ctx.comment('Pickup height is ' +
                            str(pickup_height) + ' (fixed)')
                move_vol_multi(m300, reagent=Elution, source=work_destinations[i],
                               dest=waste, vol=transfer_vol, air_gap_vol=air_gap_vol, x_offset=x_offset,
                               pickup_height=pickup_height, rinse=False)
            m300.drop_tip(home_after=True)
            tip_track['counts'][m300] += 8
        end = datetime.now()
        time_taken = (end - start)
        ctx.comment('Step ' + str(STEP) + ': ' +
                    STEPS[STEP]['description'] + ' took ' + str(time_taken))
        STEPS[STEP]['Time:'] = str(time_taken)

    ############################################################################
    # STEP 6 Washing 1 Isopropanol
    ############################################################################
    STEP += 1
    if STEPS[STEP]['Execute'] == True:
        start = datetime.now()

        ctx.comment('Step ' + str(STEP) + ': ' + STEPS[STEP]['description'])
        ctx.comment('###############################################')

        isoprop_wash_vol = [150]
        x_offset = 0
        rinse = True  # Only first time

        ########
        # isoprop washes
        for i in range(num_cols):
            if not m300.hw_pipette['has_tip']:
                pick_up(m300)
            for transfer_vol in isoprop_wash_vol:
                # Calculate pickup_height based on remaining volume and shape of container
                [pickup_height, change_col] = calc_height(
                    Isopropanol, multi_well_rack_area, transfer_vol * 8)
                ctx.comment('Aspirate from Reservoir column: ' +
                            str(Isopropanol.col))
                ctx.comment('Pickup height is ' + str(pickup_height))
                if i != 0:
                    rinse = False
                move_vol_multi(m300, reagent=Isopropanol, source=Isopropanol.reagent_reservoir[Isopropanol.col],
                               dest=work_destinations[i], vol=transfer_vol, air_gap_vol=air_gap_vol, x_offset=x_offset,
                               pickup_height=pickup_height, rinse=rinse)
        m300.drop_tip(home_after=True)
        tip_track['counts'][m300] += 8
        end = datetime.now()
        time_taken = (end - start)
        ctx.comment('Step ' + str(STEP) + ': ' +
                    STEPS[STEP]['description'] + ' took ' + str(time_taken))
        STEPS[STEP]['Time:'] = str(time_taken)

    ############################################################################
    # STEP 7 WAIT FOR 30s-1'
    ############################################################################

    STEP += 1
    if STEPS[STEP]['Execute'] == True:
        start = datetime.now()
        ctx.comment('Step ' + str(STEP) + ': ' + STEPS[STEP]['description'])
        ctx.comment('###############################################')
        ctx.delay(seconds=30, msg='Wait for 30 seconds.')
        end = datetime.now()
        time_taken = (end - start)
        ctx.comment('Step ' + str(STEP) + ': ' +
                    STEPS[STEP]['description'] + ' took ' + str(time_taken))
        STEPS[STEP]['Time:'] = str(time_taken)

    ####################################################################
    # STEP 8 REMOVE ISOPROPANOL (supernatant)
    # remove supernatant -> height calculation can be omitted and referred to bottom!

    STEP += 1
    if STEPS[STEP]['Execute'] == True:
        start = datetime.now()
        ctx.comment('Step ' + str(STEP) + ': ' + STEPS[STEP]['description'])
        ctx.comment('###############################################')
        supernatant_vol = [150]
        x_offset_rs = 2

        for i in range(num_cols):
            x_offset = find_side(i) * x_offset_rs
            if not m300.hw_pipette['has_tip']:
                pick_up(m300)
            for transfer_vol in supernatant_vol:
                # Pickup_height is fixed here
                pickup_height = 0.1
                ctx.comment('Aspirate from deep well column: ' + str(i + 1))
                ctx.comment('Pickup height is ' +
                            str(pickup_height) + ' (fixed)')
                move_vol_multi(m300, reagent=Elution, source=work_destinations[i],
                               dest=waste, vol=transfer_vol, air_gap_vol=air_gap_vol, x_offset=x_offset,
                               pickup_height=pickup_height, rinse=False)
            m300.drop_tip(home_after=True)
            tip_track['counts'][m300] += 8
        end = datetime.now()
        time_taken = (end - start)
        ctx.comment('Step ' + str(STEP) + ': ' +
                    STEPS[STEP]['description'] + ' took ' + str(time_taken))
        STEPS[STEP]['Time:'] = str(time_taken)

    ############################################################################
    # STEP 9 Washing 1 ethanol
    ############################################################################

    STEP += 1
    if STEPS[STEP]['Execute'] == True:
        start = datetime.now()

        ctx.comment('Step ' + str(STEP) + ': ' + STEPS[STEP]['description'])
        ctx.comment('###############################################')

        ethanol_wash_vol = [100, 100]
        x_offset = 0
        # WASH 2 TIMES
        ########
        # 70% EtOH washes
        for i in range(num_cols):
            if not m300.hw_pipette['has_tip']:
                pick_up(m300)
            for transfer_vol in ethanol_wash_vol:
                # Calculate pickup_height based on remaining volume and shape of container
                [pickup_height, change_col] = calc_height(
                    Ethanol, multi_well_rack_area, transfer_vol * 8)
                ctx.comment('Aspirate from Reservoir column: ' +
                            str(Ethanol.col))
                ctx.comment('Pickup height is ' + str(pickup_height))
                if i != 0:
                    rinse = False
                move_vol_multi(m300, reagent=Ethanol, source=Ethanol.reagent_reservoir[Ethanol.col],
                               dest=work_destinations[i], vol=transfer_vol, air_gap_vol=air_gap_vol, x_offset=x_offset,
                               pickup_height=pickup_height, rinse=rinse)
        m300.drop_tip(home_after=True)
        tip_track['counts'][m300] += 8
        end = datetime.now()
        time_taken = (end - start)
        ctx.comment('Step ' + str(STEP) + ': ' +
                    STEPS[STEP]['description'] + ' took ' + str(time_taken))
        STEPS[STEP]['Time:'] = str(time_taken)
    ############################################################################
    # STEP 10 WAIT FOR 30s-1'
    ############################################################################

    STEP += 1
    if STEPS[STEP]['Execute'] == True:
        start = datetime.now()

        ctx.comment('Step ' + str(STEP) + ': ' + STEPS[STEP]['description'])
        ctx.comment('###############################################')

        ctx.delay(seconds=30, msg='Wait for 30 seconds.')

        end = datetime.now()
        time_taken = (end - start)
        ctx.comment('Step ' + str(STEP) + ': ' +
                    STEPS[STEP]['description'] + ' took ' + str(time_taken))
        STEPS[STEP]['Time:'] = str(time_taken)

    ####################################################################
    # STEP 11 REMOVE SUPERNATANT
    # remove supernatant -> height calculation can be omitted and referred to bottom!

    STEP += 1
    if STEPS[STEP]['Execute'] == True:
        start = datetime.now()

        ctx.comment('Step ' + str(STEP) + ': ' + STEPS[STEP]['description'])
        ctx.comment('###############################################')

        supernatant_vol = [100, 100]
        x_offset_rs = 2

        for i in range(num_cols):
            x_offset = find_side(i) * x_offset_rs
            if not m300.hw_pipette['has_tip']:
                pick_up(m300)
            for transfer_vol in supernatant_vol:
                # Pickup_height is fixed here
                pickup_height = 0.1
                ctx.comment('Aspirate from deep well column: ' + str(i + 1))
                ctx.comment('Pickup height is ' +
                            str(pickup_height) + ' (fixed)')
                move_vol_multi(m300, reagent=Elution, source=work_destinations[i],
                               dest=waste, vol=transfer_vol, air_gap_vol=air_gap_vol, x_offset=x_offset,
                               pickup_height=pickup_height, rinse=False)
            m300.drop_tip(home_after=True)
            tip_track['counts'][m300] += 8
        end = datetime.now()
        time_taken = (end - start)
        ctx.comment('Step ' + str(STEP) + ': ' +
                    STEPS[STEP]['description'] + ' took ' + str(time_taken))
        STEPS[STEP]['Time:'] = str(time_taken)

    ############################################################################
    # STEP 12 Washing 2
    ############################################################################

    STEP += 1
    if STEPS[STEP]['Execute'] == True:
        start = datetime.now()

        ctx.comment('Step ' + str(STEP) + ': ' + STEPS[STEP]['description'])
        ctx.comment('###############################################')

        ethanol_wash_vol = [100, 100]
        x_offset = 0
        # WASH 2 TIMES
        ########
        # 70% EtOH washes
        for i in range(num_cols):
            if not m300.hw_pipette['has_tip']:
                pick_up(m300)
            for j, transfer_vol in enumerate(ethanol_wash_vol):
                # Calculate pickup_height based on remaining volume and shape of container
                [pickup_height, change_col] = calc_height(
                    Ethanol, multi_well_rack_area, transfer_vol * 8)
                ctx.comment('Aspirate from Reservoir column: ' +
                            str(Ethanol.col))
                ctx.comment('Pickup height is ' + str(pickup_height))
                if j != 0:
                    rinse = False
                move_vol_multi(m300, reagent=Ethanol, source=Ethanol.reagent_reservoir[Ethanol.col],
                               dest=work_destinations[i], vol=transfer_vol, air_gap_vol=air_gap_vol, x_offset=x_offset,
                               pickup_height=pickup_height, rinse=rinse)
        m300.drop_tip(home_after=True)
        tip_track['counts'][m300] += 8
        end = datetime.now()
        time_taken = (end - start)
        ctx.comment('Step ' + str(STEP) + ': ' +
                    STEPS[STEP]['description'] + ' took ' + str(time_taken))
        STEPS[STEP]['Time:'] = str(time_taken)

    ############################################################################
    # STEP 13 WAIT FOR 30s-1'
    ############################################################################
    STEP += 1
    if STEPS[STEP]['Execute'] == True:
        start = datetime.now()

        ctx.comment('Step ' + str(STEP) + ': ' + STEPS[STEP]['description'])
        ctx.comment('###############################################')

        ctx.delay(seconds=30, msg='Incubating for 30 seconds.')

        start_timer = timer()
        end = datetime.now()
        time_taken = (end - start)
        ctx.comment('Step ' + str(STEP) + ': ' +
                    STEPS[STEP]['description'] + ' took ' + str(time_taken))
        STEPS[STEP]['Time:'] = str(time_taken)

    ####################################################################
    # STEP 14 REMOVE SUPERNATANT AGAIN
    # remove supernatant -> height calculation can be omitted and referred to bottom!

    STEP += 1
    if STEPS[STEP]['Execute'] == True:
        start = datetime.now()

        ctx.comment('Step ' + str(STEP) + ': ' + STEPS[STEP]['description'])
        ctx.comment('###############################################')

        supernatant_vol = [100, 100, 40]
        x_offset_rs = 2

        for i in range(num_cols):
            x_offset = find_side(i) * x_offset_rs
            if not m300.hw_pipette['has_tip']:
                pick_up(m300)
            for transfer_vol in supernatant_vol:
                # Pickup_height is fixed here
                pickup_height = 0.1
                ctx.comment('Aspirate from deep well column: ' + str(i + 1))
                ctx.comment('Pickup height is ' + str(pickup_height))
                move_vol_multi(m300, reagent=Elution, source=work_destinations[i],
                               dest=waste, vol=transfer_vol, air_gap_vol=air_gap_vol, x_offset=x_offset,
                               pickup_height=pickup_height, rinse=False)
            m300.drop_tip(home_after=True)
            tip_track['counts'][m300] += 8
        end = datetime.now()
        time_taken = (end - start)
        ctx.comment('Step ' + str(STEP) + ': ' +
                    STEPS[STEP]['description'] + ' took ' + str(time_taken))
        STEPS[STEP]['Time:'] = str(time_taken)

    ####################################################################
    # STEP 15 DRY
    ############################################################################

    STEP += 1
    if STEPS[STEP]['Execute'] == True:
        m300.reset_tipracks()
        ctx.comment('CAMBIAR TIPRACKS!')
        start = datetime.now()
        ctx.comment('Step ' + str(STEP) + ': ' + STEPS[STEP]['description'])
        ctx.comment('###############################################')
        ctx.delay(seconds=STEPS[STEP]['wait_time'], msg='Airdrying beads')
        magdeck.disengage()
        end = datetime.now()
        time_taken = (end - start)
        ctx.comment('Step ' + str(STEP) + ': ' +
                    STEPS[STEP]['description'] + ' took ' + str(time_taken))
        STEPS[STEP]['Time:'] = str(time_taken)

    ############################################################################
    # STEP 16 Transfer water
    ############################################################################

    STEP += 1
    if STEPS[STEP]['Execute'] == True:
        start = datetime.now()
        ctx.comment('Step ' + str(STEP) + ': ' + STEPS[STEP]['description'])
        ctx.comment('###############################################')
        # Water elution
        water_wash_vol = [50]
        air_gap_vol_water = 10
        x_offset = 0

        ########
        # Water or elution buffer
        for i in range(num_cols):
            if not m300.hw_pipette['has_tip']:
                pick_up(m300)
            for transfer_vol in water_wash_vol:
                # Calculate pickup_height based on remaining volume and shape of container
                [pickup_height, change_col] = calc_height(
                    Water, multi_well_rack_area, transfer_vol * 8)
                ctx.comment(
                    'Aspirate from Reservoir column: ' + str(Water.col))
                ctx.comment('Pickup height is ' + str(pickup_height))
                move_vol_multi(m300, reagent=Water, source=Water.reagent_reservoir,
                               dest=work_destinations[i], vol=transfer_vol, air_gap_vol=air_gap_vol_water, x_offset=x_offset,
                               pickup_height=pickup_height, rinse=False)

            ctx.comment('Mixing sample with Water and LTA')
            # Mixing
            custom_mix(m300, Elution, work_destinations[i], vol=40, rounds=4,
                       blow_out=True, mix_height=0)
            m300.drop_tip(home_after=True)
            tip_track['counts'][m300] += 8
        end = datetime.now()
        time_taken = (end - start)
        ctx.comment('Step ' + str(STEP) + ': ' +
                    STEPS[STEP]['description'] + ' took ' + str(time_taken))
        STEPS[STEP]['Time:'] = str(time_taken)

    ############################################################################
    # STEP 17 WAIT 1-2' WITHOUT MAGNET
    ############################################################################

    STEP += 1
    if STEPS[STEP]['Execute'] == True:
        start = datetime.now()

        ctx.comment('Step ' + str(STEP) + ': ' + STEPS[STEP]['description'])
        ctx.comment('###############################################')

        ctx.delay(seconds=STEPS[STEP]['wait_time'], msg='Incubating OFF magnet for ' +
                  format(STEPS[STEP]['wait_time']) + ' seconds.')  # minutes=2

        end = datetime.now()
        time_taken = (end - start)
        ctx.comment('Step ' + str(STEP) + ': ' +
                    STEPS[STEP]['description'] + ' took ' + str(time_taken))
        STEPS[STEP]['Time:'] = str(time_taken)

    ############################################################################
    # STEP 18 WAIT 5' WITH MAGNET
    ############################################################################

    STEP += 1
    if STEPS[STEP]['Execute'] == True:
        start = datetime.now()

        ctx.comment('Step ' + str(STEP) + ': ' + STEPS[STEP]['description'])
        ctx.comment('###############################################')
        magdeck.engage(height=mag_height)
        ctx.delay(seconds=STEPS[STEP]['wait_time'], msg='Incubating ON magnet for ' +
                  format(STEPS[STEP]['wait_time']) + ' seconds.')  # minutes=2

        end = datetime.now()
        time_taken = (end - start)
        ctx.comment('Step ' + str(STEP) + ': ' +
                    STEPS[STEP]['description'] + ' took ' + str(time_taken))
        STEPS[STEP]['Time:'] = str(time_taken)

    ############################################################################
    # STEP 19 TRANSFER TO ELUTION PLATE
    ############################################################################

    STEP += 1
    if STEPS[STEP]['Execute'] == True:
        start = datetime.now()

        ctx.comment('Step ' + str(STEP) + ': ' + STEPS[STEP]['description'])
        ctx.comment('###############################################')

        elution_vol = [45]
        x_offset_rs = 2
        for i in range(num_cols):
            x_offset = find_side(i) * x_offset_rs
            if not m300.hw_pipette['has_tip']:
                pick_up(m300)
            for transfer_vol in elution_vol:
                # Pickup_height is fixed here
                pickup_height = 0.2
                ctx.comment('Aspirate from deep well column: ' + str(i + 1))
                ctx.comment('Pickup height is ' +
                            str(pickup_height) + ' (fixed)')
                move_vol_multi(m300, reagent=Elution, source=work_destinations[i],
                               dest=final_destinations[i], vol=transfer_vol, air_gap_vol=air_gap_vol, x_offset=x_offset,
                               pickup_height=pickup_height, rinse=False)
            m300.drop_tip(home_after=True)
            tip_track['counts'][m300] += 8
        end = datetime.now()
        time_taken = (end - start)
        ctx.comment('Step ' + str(STEP) + ': ' +
                    STEPS[STEP]['description'] + ' took ' + str(time_taken))
        STEPS[STEP]['Time:'] = str(time_taken)

    # Export the time log to a tsv file
    if not ctx.is_simulating():
        with open(file_path, 'w') as f:
            f.write('STEP\texecution\tdescription\twait_time\texecution_time\n')
            for key in STEPS.keys():
                row = str(key) + '\t'
                for key2 in STEPS[key].keys():
                    row += format(STEPS[key][key2]) + '\t'
                f.write(row + '\n')
        f.close()

    ############################################################################
    # Light flash end of program
    from opentrons.drivers.rpi_drivers import gpio
    for i in range(3):
        gpio.set_rail_lights(False)
        gpio.set_button_light(1, 0, 0)
        time.sleep(0.3)
        gpio.set_rail_lights(True)
        gpio.set_button_light(0, 0, 1)
        time.sleep(0.3)
    gpio.set_button_light(0, 1, 0)
    ctx.comment(
        'Finished! \nMove deepwell plate (slot 5) to Station C for MMIX addition and qPCR preparation.')
    ctx.comment('Used tips in total: ' + str(tip_track['counts'][m300]))
    ctx.comment('Used racks in total: ' + str(tip_track['counts'][m300] / 96))