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
    'protocolName': 'S2 Station B Version 6',
    'author': 'Aitor Gastaminza & José Luis Villanueva (jlvillanueva@clinic.cat)',
    'source': 'Hospital Clínic Barcelona',
    'apiLevel': '2.0',
    'description': 'Protocol for RNA extraction using custom lab procotol (no kits)'
}

#Defined variables
##################
NUM_SAMPLES = 96
air_gap_vol = 15
run_id = 'R001'

# mag_height = 11 # Height needed for NUNC deepwell in magnetic deck
mag_height = 17  # Height needed for ABGENE deepwell in magnetic deck
temperature = 4
D_deepwell = 6.9  # Deepwell diameter (ABGENE deepwell)
# D_deepwell = 8.35 # Deepwell diameter (NUNC deepwell)
multi_well_rack_area = 8.2 * 71.2  # Cross section of the 12 well reservoir
x_offset_rs = 1 #Offset of the pickup when magnet is ON

#Calculated variables
deepwell_cross_section_area = math.pi * D_deepwell**2 / 4  # deepwell cilinder cross secion area
num_cols = math.ceil(NUM_SAMPLES / 8)  # Columns we are working on

def run(ctx: protocol_api.ProtocolContext):
    ctx.comment('Actual used columns: ' + str(num_cols))
    STEP = 0
    STEPS = {  # Dictionary with STEP activation, description, and times
        1: {'Execute': True, 'description': 'Mix beads'},
        2: {'Execute': True, 'description': 'Transfer beads'},
        3: {'Execute': True, 'description': 'Wait with magnet OFF after beads', 'wait_time': 120},  # 60
        4: {'Execute': True, 'description': 'Wait with magnet ON after beads', 'wait_time': 900},  # 900
        5: {'Execute': True, 'description': 'Remove supernatant'},
        6: {'Execute': True, 'description': 'Add Isopropanol and mix'},
        7: {'Execute': True, 'description': 'Wait for 30s after isopropanol'},
        8: {'Execute': True, 'description': 'Remove isopropanol'},
        9: {'Execute': True, 'description': 'Wash with ethanol and mix 1'},
        10: {'Execute': True, 'description': 'Wait for 30s after ethanol 1'},
        11: {'Execute': True, 'description': 'Remove supernatant'},
        12: {'Execute': True, 'description': 'Wash with ethanol and mix 2'},
        13: {'Execute': True, 'description': 'Wait 30s after ethanol 2'},
        14: {'Execute': True, 'description': 'Remove supernatant'},
        15: {'Execute': True, 'description': 'Allow to dry', 'wait_time': 300},
        16: {'Execute': True, 'description': 'Add water and LTA'},
        17: {'Execute': True, 'description': 'Wait with magnet OFF after water', 'wait_time': 60},  # 60
        18: {'Execute': True, 'description': 'Wait with magnet ON after water', 'wait_time': 120},  # 300
        19: {'Execute': True, 'description': 'Transfer to final elution plate'}
    }

    for s in STEPS:  # Create an empty wait_time
        if 'wait_time' not in STEPS[s]:
            STEPS[s]['wait_time'] = 0
    folder_path = '/var/lib/jupyter/notebooks/' + run_id

    if not ctx.is_simulating():
        if not os.path.isdir(folder_path):
            os.mkdir(folder_path)
        file_path = folder_path + '/StationB_homebrew_time_log.txt'
        file_path2 = folder_path + '/StationB_homebrew_tips_log.txt'

    # Define Reagents as objects with their properties
    class Reagent:
        def __init__(self, name, flow_rate_aspirate, flow_rate_dispense, rinse,
                     reagent_reservoir_volume, delay, num_wells, h_cono, v_fondo,
                      tip_recycling = 'none'):
            self.name = name
            self.flow_rate_aspirate = flow_rate_aspirate
            self.flow_rate_dispense = flow_rate_dispense
            self.rinse = bool(rinse)
            self.reagent_reservoir_volume = reagent_reservoir_volume
            self.delay = delay
            self.num_wells = num_wells
            self.col = 0
            self.vol_well = 0
            self.h_cono = h_cono
            self.v_cono = v_fondo
            self.unused=[]
            self.tip_recycling = tip_recycling
            self.vol_well_original = reagent_reservoir_volume / num_wells

    # Reagents and their characteristics
    Ethanol = Reagent(name='Ethanol',
                      flow_rate_aspirate=0.5,
                      flow_rate_dispense=1,
                      rinse=True,
                      reagent_reservoir_volume=38400,
                      delay=2,
                      num_wells=4,  # num_Wells max is 4
                      h_cono=1.95,
                      v_fondo=695,  # Prismatic
                      tip_recycling=['5','8'])

    Beads = Reagent(name='Magnetic beads',
                    flow_rate_aspirate=1,
                    flow_rate_dispense=1.5,
                    rinse=True,
                    reagent_reservoir_volume=29760,
                    delay=2,
                    num_wells=4,
                    h_cono=1.95,
                    v_fondo=695 ) # Prismatic)

    Isopropanol = Reagent(name='Isopropanol',
                          flow_rate_aspirate=1,
                          flow_rate_dispense=1,
                          rinse=True,
                          reagent_reservoir_volume=14400,
                          delay=2,
                          num_wells=2,  # num_Wells max is 2
                          h_cono=1.95,
                          v_fondo=695,  # Prismatic
                          tip_recycling=['10'])

    Water = Reagent(name='Water',
                    flow_rate_aspirate=3,
                    flow_rate_dispense=6,
                    rinse=False,
                    reagent_reservoir_volume=4800,
                    delay=0,
                    num_wells=1,  # num_Wells max is 1
                    h_cono=1.95,
                    v_fondo=695)  # Prismatic

    Elution = Reagent(name='Elution',
                      flow_rate_aspirate=0.5,
                      flow_rate_dispense=1,
                      rinse=False,
                      reagent_reservoir_volume=800,
                      delay=0,
                      num_wells=num_cols,  # num_cols comes from available columns
                      h_cono=4,
                      v_fondo=4 * math.pi * D_deepwell**2/4 /3)  # Sphere

    # Calculate the current volume in active well based on total volume and wells
    Ethanol.vol_well = Ethanol.vol_well_original
    Beads.vol_well = Beads.vol_well_original
    Isopropanol.vol_well = Isopropanol.vol_well_original
    Water.vol_well = Water.vol_well_original
    Elution.vol_well = 350

    ##################
    # Custom functions
    def move_vol_multichannel(pipet, reagent, source, dest, vol, air_gap_vol, x_offset,
                       pickup_height, rinse, disp_height, blow_out, touch_tip):
        '''
        x_offset: list with two values. x_offset in source and x_offset in destination i.e. [-1,1]
        pickup_height: height from bottom where volume
        rinse: if True it will do 2 rounds of aspirate and dispense before the tranfer
        disp_height: dispense height; by default it's close to the top (z=-2), but in case it is needed it can be lowered
        blow_out, touch_tip: if True they will be done after dispensing
        '''
        # Rinse before aspirating
        if rinse == True:
            custom_mix(pipet, reagent, location = source, vol = vol,
                       rounds = 2, blow_out = True, mix_height = 0,
                       x_offset = x_offset)
        # SOURCE
        s = source.bottom(pickup_height).move(Point(x = x_offset[0]))
        pipet.aspirate(vol, s)  # aspirate liquid
        if air_gap_vol != 0:  # If there is air_gap_vol, switch pipette to slow speed
            pipet.aspirate(air_gap_vol, source.top(z = -2),
                           rate = reagent.flow_rate_aspirate)  # air gap
        # GO TO DESTINATION
        drop = dest.top(z = disp_height).move(Point(x = x_offset[1]))
        pipet.dispense(vol + air_gap_vol, drop,
                       rate = reagent.flow_rate_dispense)  # dispense all
        ctx.delay(seconds = reagent.delay) # pause for x seconds depending on reagent
        if blow_out == True:
            pipet.blow_out(dest.top(z = -2))
        if touch_tip == True:
            pipet.touch_tip(speed = 20, v_offset = -5)

    def custom_mix(pipet, reagent, location, vol, rounds, blow_out, mix_height,
    x_offset, source_height = 3):
        '''
        Function for mixing a given [vol] in the same [location] a x number of [rounds].
        blow_out: Blow out optional [True,False]
        x_offset = [source, destination]
        source_height: height from bottom to aspirate
        mix_height: height from bottom to dispense
        '''
        if mix_height == 0:
            mix_height = 3
        pipet.aspirate(1, location=location.bottom(
            z=source_height).move(Point(x=x_offset[0])), rate=reagent.flow_rate_aspirate)
        for _ in range(rounds):
            pipet.aspirate(vol, location=location.bottom(
                z=source_height).move(Point(x=x_offset[0])), rate=reagent.flow_rate_aspirate)
            pipet.dispense(vol, location=location.bottom(
                z=mix_height).move(Point(x=x_offset[1])), rate=reagent.flow_rate_dispense)
        pipet.dispense(1, location=location.bottom(
            z=mix_height).move(Point(x=x_offset[1])), rate=reagent.flow_rate_dispense)
        if blow_out == True:
            pipet.blow_out(location.top(z=-2))  # Blow out

    def calc_height(reagent, cross_section_area, aspirate_volume, min_height=0.5):
        nonlocal ctx
        ctx.comment('Remaining volume ' + str(reagent.vol_well) +
                    '< needed volume ' + str(aspirate_volume) + '?')
        if reagent.vol_well < aspirate_volume:
            reagent.unused.append(reagent.vol_well)
            ctx.comment('Next column should be picked')
            ctx.comment('Previous to change: ' + str(reagent.col))
            # column selector position; intialize to required number
            reagent.col = reagent.col + 1
            ctx.comment(str('After change: ' + str(reagent.col)))
            reagent.vol_well = reagent.vol_well_original
            ctx.comment('New volume:' + str(reagent.vol_well))
            height = (reagent.vol_well - aspirate_volume - reagent.v_cono) / cross_section_area
                    #- reagent.h_cono
            reagent.vol_well = reagent.vol_well - aspirate_volume
            ctx.comment('Remaining volume:' + str(reagent.vol_well))
            if height < min_height:
                height = min_height
            col_change = True
        else:
            height = (reagent.vol_well - aspirate_volume - reagent.v_cono) / cross_section_area #- reagent.h_cono
            reagent.vol_well = reagent.vol_well - aspirate_volume
            ctx.comment('Calculated height is ' + str(height))
            if height < min_height:
                height = min_height
            ctx.comment('Used height is ' + str(height))
            col_change = False
        return height, col_change

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

    ##########
    def find_side(col):
        '''
        Detects if the current column has the magnet at its left or right side
        '''
        if col % 2 == 0:
            side = -1  # left
        else:
            side = 1
        return side

####################################
    # load labware and modules
    # 12 well rack
    reagent_res = ctx.load_labware(
        'nest_12_reservoir_15ml', '2', 'reagent deepwell plate 1')

############################################
    # tempdeck
    tempdeck = ctx.load_module('tempdeck', '3')
    #tempdeck.set_temperature(temperature)

##################################
    # Elution plate - final plate, goes to C
    elution_plate = tempdeck.load_labware(
        'pcr_transparent_96_wellplate_200ul_alum_covid',
        'cooled elution plate')

############################################
    # Elution plate - comes from A
    magdeck = ctx.load_module('magdeck', '6')
    deepwell_plate = magdeck.load_labware(
        'abgene_96_wellplate_800ul', 'ABGENE 96 Well Plate 800 µL')
    magdeck.disengage()

####################################
    # Waste reservoir
    waste_reservoir = ctx.load_labware(
        'nalgene_1_reservoir_300000ul', '9', 'waste reservoir')
    waste = waste_reservoir.wells()[0]  # referenced as reservoir

####################################
    # Load tip_racks
    tips300 = [ctx.load_labware('opentrons_96_tiprack_300ul', slot, '200µl filter tiprack')
               for slot in ['1', '4', '7', '11']]
    tips300r = [ctx.load_labware('opentrons_96_tiprack_300ul', slot, '200µl filter tiprack') for slot in Ethanol.tip_recycling]
    tips300ri = [ctx.load_labware('opentrons_96_tiprack_300ul', slot, '200µl filter tiprack') for slot in Isopropanol.tip_recycling]

    # tips1000 = [ctx.load_labware('opentrons_96_filtertiprack_1000ul', slot, '1000µl filter tiprack')
    #    for slot in ['10']]

################################################################################
    # Declare which reagents are in each reservoir as well as deepwell and elution plate
    Beads.reagent_reservoir = reagent_res.rows(
    )[0][:Beads.num_wells]  # 1 row, 4 columns (first ones)
    Isopropanol.reagent_reservoir = reagent_res.rows()[0][4:(
        4 + Isopropanol.num_wells)]  # 1 row, 2 columns (from 5 to 6)
    Ethanol.reagent_reservoir = reagent_res.rows()[0][6:(
        6 + Ethanol.num_wells)]  # 1 row, 2 columns (from 7 to 10)
    # 1 row, 1 column (last one) full of water
    Water.reagent_reservoir = reagent_res.rows()[0][-1]
    work_destinations = deepwell_plate.rows()[0][:Elution.num_wells]
    final_destinations = elution_plate.rows()[0][:Elution.num_wells]

    # pipettes. P1000 currently deactivated
    m300 = ctx.load_instrument(
        'p300_multi_gen2', 'right', tip_racks=tips300)  # Load multi pipette
    # p1000 = ctx.load_instrument('p1000_single_gen2', 'left', tip_racks=tips1000) # load P1000 pipette

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
                   rounds=10, blow_out=True, mix_height=0, x_offset = [0,0], source_height = 3)
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
                               vol=180, rounds=10, blow_out=True, mix_height=0, x_offset = [0,0])
                ctx.comment(
                    'Aspirate from reservoir column: ' + str(Beads.col))
                ctx.comment('Pickup height is ' + str(pickup_height))
                if j != 0:
                    rinse = False
                move_vol_multichannel(m300, reagent=Beads, source=Beads.reagent_reservoir[Beads.col],
                               dest=work_destinations[i], vol=transfer_vol, air_gap_vol=air_gap_vol,
                               x_offset=[0,0], pickup_height=pickup_height, rinse=rinse,
                               disp_height=-2, blow_out=True, touch_tip=False)
            ctx.comment('Mixing sample with beads ')
            custom_mix(m300, Beads, location=work_destinations[i], vol=180,
                       rounds=6, blow_out=True, mix_height=16, x_offset=[0,0])
            m300.touch_tip(speed = 20, v_offset = -5)
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
                  format(STEPS[STEP]['wait_time']) + ' seconds.')  # minutes=15

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

        for i in range(num_cols):
            x_offset = find_side(i) * x_offset_rs
            #if not m300.hw_pipette['has_tip']:
            pick_up(m300)
            for transfer_vol in supernatant_vol:
                # Pickup_height is fixed here
                pickup_height = 0.5
                ctx.comment('Aspirate from deep well column: ' + str(i + 1))
                ctx.comment('Pickup height is ' +
                            str(pickup_height) + ' (fixed)')
                move_vol_multichannel(m300, reagent=Elution, source=work_destinations[i],
                               dest=waste, vol=transfer_vol, air_gap_vol=air_gap_vol,
                               x_offset=[x_offset,0], pickup_height=pickup_height, rinse=False,
                               disp_height=-2, blow_out=True, touch_tip=True)

            m300.drop_tip(home_after=True)
            tip_track['counts'][m300] += 8
        end = datetime.now()
        time_taken = (end - start)
        ctx.comment('Step ' + str(STEP) + ': ' +
                    STEPS[STEP]['description'] + ' took ' + str(time_taken))
        STEPS[STEP]['Time:'] = str(time_taken)

    ############################################################################
    # STEP 6 Washing 1 Isopropanol (dispense first)
    ############################################################################
    STEP += 1
    if STEPS[STEP]['Execute'] == True:
        start = datetime.now()

        ctx.comment('Step ' + str(STEP) + ': ' + STEPS[STEP]['description'])
        ctx.comment('###############################################')

        isoprop_wash_vol = [150]
        x_offset = 0
        rinse = Isopropanol.rinse  # Only first time

        ########
        # isoprop washes
        for i in range(num_cols):
            #if not m300.hw_pipette['has_tip']:
            m300.pick_up_tip(tips300ri[0].rows()[0][i])
            for j, transfer_vol in enumerate(isoprop_wash_vol):
                # Calculate pickup_height based on remaining volume and shape of container
                [pickup_height, change_col] = calc_height(
                    Isopropanol, multi_well_rack_area, transfer_vol * 8)
                ctx.comment('Aspirate from Reservoir column: ' +
                            str(Isopropanol.col))
                ctx.comment('Pickup height is ' + str(pickup_height))
                if i != 0 and j!= 0:
                    rinse = False
                move_vol_multichannel(m300, reagent=Isopropanol, source=Isopropanol.reagent_reservoir[Isopropanol.col],
                               dest=work_destinations[i], vol=transfer_vol, air_gap_vol=air_gap_vol, x_offset=[0,x_offset],
                               pickup_height=pickup_height, rinse=rinse,
                               disp_height=-2, blow_out=True, touch_tip=False)
                custom_mix(m300, reagent=Isopropanol, location=work_destinations[i], vol=transfer_vol,
                           rounds=2, blow_out=True, mix_height=1, x_offset=[0,0])
                #m300.drop_tip(home_after=True)
                m300.touch_tip(speed = 20, v_offset = -5)
            m300.return_tip(tips300ri[0].rows()[0][i])

            #tip_track['counts'][m300] += 8
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
    # STEP 8 REMOVE ISOPROPANOL (supernatant removal)
    ####################################################################
    # remove supernatant -> height calculation can be omitted and referred to bottom!

    STEP += 1
    if STEPS[STEP]['Execute'] == True:
        start = datetime.now()
        ctx.comment('Step ' + str(STEP) + ': ' + STEPS[STEP]['description'])
        ctx.comment('###############################################')
        supernatant_vol = [160]

        for i in range(num_cols):
            x_offset = find_side(i) * x_offset_rs
            #if not m300.hw_pipette['has_tip']:
            m300.pick_up_tip(tips300ri[0].rows()[0][i])
            for transfer_vol in supernatant_vol:
                # Pickup_height is fixed here
                pickup_height = 0.1
                ctx.comment('Aspirate from deep well column: ' + str(i + 1))
                ctx.comment('Pickup height is ' +
                            str(pickup_height) + ' (fixed)')
                move_vol_multichannel(m300, reagent=Elution, source=work_destinations[i],
                               dest=waste, vol=transfer_vol, air_gap_vol=air_gap_vol, x_offset=[x_offset,0],
                               pickup_height=pickup_height, rinse=False,
                               disp_height=-2, blow_out=True, touch_tip=True)
            #m300.drop_tip()
            m300.return_tip(tips300ri[0].rows()[0][i])
            tip_track['counts'][m300] += 8
        end = datetime.now()
        time_taken = (end - start)
        ctx.comment('Step ' + str(STEP) + ': ' +
                    STEPS[STEP]['description'] + ' took ' + str(time_taken))
        STEPS[STEP]['Time:'] = str(time_taken)

    ############################################################################
    # STEP 9 Washing 1 ethanol (dispense and mix)
    ############################################################################

    STEP += 1
    if STEPS[STEP]['Execute'] == True:
        start = datetime.now()

        ctx.comment('Step ' + str(STEP) + ': ' + STEPS[STEP]['description'])
        ctx.comment('###############################################')

        ethanol_wash_vol = [100, 100]
        x_offset = 0
        rinse = Ethanol.rinse
        # WASH 2 TIMES
        ########
        # 70% EtOH washes
        #m300.pick_up_tip(tips300r.rows()[0][0])
        for i in range(num_cols):
            #if not m300.hw_pipette['has_tip']:
            #    pick_up(m300)
            m300.pick_up_tip(tips300r[0].rows()[0][i])
            for j, transfer_vol in enumerate(ethanol_wash_vol):
                # Calculate pickup_height based on remaining volume and shape of container
                [pickup_height, change_col] = calc_height(
                    Ethanol, multi_well_rack_area, transfer_vol * 8)
                ctx.comment('Aspirate from Reservoir column: ' +
                            str(Ethanol.col))
                ctx.comment('Pickup height is ' + str(pickup_height))
                if i != 0 and j!=0:
                    rinse = False
                move_vol_multichannel(m300, reagent=Ethanol, source=Ethanol.reagent_reservoir[Ethanol.col],
                               dest=work_destinations[i], vol=transfer_vol, air_gap_vol=air_gap_vol, x_offset=[0,x_offset],
                               pickup_height=pickup_height, rinse=rinse,
                               disp_height=-2, blow_out=True, touch_tip=False)

            custom_mix(m300, reagent=Ethanol, location=work_destinations[i], vol=transfer_vol,
                           rounds=2, blow_out=True, mix_height=1, x_offset=[0,0])
            m300.touch_tip(speed = 20, v_offset = -5)
            m300.return_tip(tips300r[0].rows()[0][i])
        #tip_track['counts'][m300] += 8
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

        for i in range(num_cols):
            x_offset = find_side(i) * x_offset_rs
            #if not m300.hw_pipette['has_tip']:
            m300.pick_up_tip(tips300r[0].rows()[0][i])
            for transfer_vol in supernatant_vol:
                # Pickup_height is fixed here
                pickup_height = 0.1
                ctx.comment('Aspirate from deep well column: ' + str(i + 1))
                ctx.comment('Pickup height is ' +
                            str(pickup_height) + ' (fixed)')
                move_vol_multichannel(m300, reagent=Elution, source=work_destinations[i],
                               dest=waste, vol=transfer_vol, air_gap_vol=air_gap_vol, x_offset=[x_offset,0],
                               pickup_height=pickup_height, rinse=False,
                               disp_height=-2, blow_out=True, touch_tip=True)
            #m300.drop_tip(home_after=True)
            m300.return_tip(tips300r[0].rows()[0][i])
            tip_track['counts'][m300] += 8
        end = datetime.now()
        time_taken = (end - start)
        ctx.comment('Step ' + str(STEP) + ': ' +
                    STEPS[STEP]['description'] + ' took ' + str(time_taken))
        STEPS[STEP]['Time:'] = str(time_taken)

    ############################################################################
    # STEP 12 Washing 2 ethanol (dispense and mix)
    ############################################################################

    STEP += 1
    if STEPS[STEP]['Execute'] == True:
        start = datetime.now()

        ctx.comment('Step ' + str(STEP) + ': ' + STEPS[STEP]['description'])
        ctx.comment('###############################################')

        ethanol_wash_vol = [100, 100]
        x_offset = 0
        rinse = Ethanol.rinse
        # WASH 2 TIMES
        ########
        # 70% EtOH washes
        for i in range(num_cols):
            #if not m300.hw_pipette['has_tip']:
            m300.pick_up_tip(tips300r[1].rows()[0][i])
            for j, transfer_vol in enumerate(ethanol_wash_vol):
                # Calculate pickup_height based on remaining volume and shape of container
                [pickup_height, change_col] = calc_height(
                    Ethanol, multi_well_rack_area, transfer_vol * 8)
                ctx.comment('Aspirate from Reservoir column: ' +
                            str(Ethanol.col))
                ctx.comment('Pickup height is ' + str(pickup_height))
                if i!=0 and j!=0:
                    rinse = False
                move_vol_multichannel(m300, reagent=Ethanol, source=Ethanol.reagent_reservoir[Ethanol.col],
                               dest=work_destinations[i], vol=transfer_vol,
                               air_gap_vol=air_gap_vol, x_offset=[0,x_offset],
                               pickup_height=pickup_height, rinse=rinse,
                               disp_height=-2, blow_out=True, touch_tip=False)

            custom_mix(m300, reagent=Ethanol, location=work_destinations[i], vol=transfer_vol,
                           rounds=2, blow_out=True, mix_height=1, x_offset=[0,0])
            m300.touch_tip(speed = 20, v_offset = -5)
            m300.return_tip(tips300r[1].rows()[0][i])
        #m300.drop_tip(home_after=True)
        #tip_track['counts'][m300] += 8
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

        for i in range(num_cols):
            x_offset = find_side(i) * x_offset_rs
            #if not m300.hw_pipette['has_tip']:
            m300.pick_up_tip(tips300r[1].rows()[0][i])
            for transfer_vol in supernatant_vol:
                # Pickup_height is fixed here
                pickup_height = 0.1
                ctx.comment('Aspirate from deep well column: ' + str(i + 1))
                ctx.comment('Pickup height is ' + str(pickup_height))
                move_vol_multichannel(m300, reagent=Elution, source=work_destinations[i],
                               dest=waste, vol=transfer_vol, air_gap_vol=air_gap_vol, x_offset=[x_offset,0],
                               pickup_height=pickup_height, rinse=False,
                               disp_height=-2, blow_out=True, touch_tip=True)
            #m300.drop_tip(home_after=True)
            m300.return_tip(tips300r[1].rows()[0][i])
            tip_track['counts'][m300] += 8
        end = datetime.now()
        time_taken = (end - start)
        ctx.comment('Step ' + str(STEP) + ': ' +
                    STEPS[STEP]['description'] + ' took ' + str(time_taken))
        STEPS[STEP]['Time:'] = str(time_taken)

    ####################################################################
    # STEP 15 DRY ( magnet == OFF)
    ############################################################################

    STEP += 1
    if STEPS[STEP]['Execute'] == True:
        #m300.reset_tipracks()
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
        x_offset_w = -1.1
        #magdeck.engage(height=17)
        ########
        # Water or elution buffer
        for i in range(num_cols):
            x_offset = find_side(i)*x_offset_w
            ctx.comment('Side is : '+ str(x_offset))
            #if not m300.hw_pipette['has_tip']:
            pick_up(m300)
            for transfer_vol in water_wash_vol:
                # Calculate pickup_height based on remaining volume and shape of container
                [pickup_height, change_col] = calc_height(
                    Water, multi_well_rack_area, transfer_vol * 8)
                ctx.comment(
                    'Aspirate from Reservoir column: ' + str(Water.col))
                ctx.comment('Pickup height is ' + str(pickup_height))
                move_vol_multichannel(m300, reagent=Water, source=Water.reagent_reservoir,
                               dest=work_destinations[i], vol=transfer_vol, air_gap_vol=air_gap_vol_water, x_offset=[0,x_offset],
                               pickup_height=pickup_height, rinse=False, disp_height=-18,
                               blow_out=True, touch_tip=False)

            ctx.comment('Mixing sample with Water and LTA')
            # Mixing
            custom_mix(m300, Elution, work_destinations[i], vol=40, rounds=20,
                       blow_out=True, mix_height=5,x_offset=[0,x_offset],source_height=0.6)
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
    # STEP 18 WAIT 2' WITH MAGNET
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
                move_vol_multichannel(m300, reagent=Elution, source=work_destinations[i],
                               dest=final_destinations[i], vol=transfer_vol, air_gap_vol=air_gap_vol, x_offset=[x_offset,0],
                               pickup_height=pickup_height, rinse=False,
                               disp_height=-3, blow_out=True, touch_tip=False)

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
                row = str(key)
                for key2 in STEPS[key].keys():
                    row += '\t' + format(STEPS[key][key2])
                f.write(row + '\n')
        f.close()
        with open(file_path2, 'w') as f2:
            f2.write('pipette\ttip_count\n')
            for key in tip_track['counts'].keys():
                row=str(key)
                f.write(str(key)+'\t'+format(tip_track['counts'][key]))
        f2.close()

    ############################################################################
    # Light flash end of program
    from opentrons.drivers.rpi_drivers import gpio
    #if not ctx.is_simulating():
        #os.system('mpg123 -f -10000 /var/lib/jupyter/notebooks/BH.mov &')
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
