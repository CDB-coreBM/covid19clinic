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
    'protocolName': 'Kingfisher Pathogen Station B1 v2',
    'author': 'Aitor Gastaminza,  José Luis Villanueva & Eva González (jlvillanueva@clinic.cat)',
    'source': 'Hospital Clínic Barcelona',
    'apiLevel': '2.0',
    'description': 'Protocol to fill KingFisher Deepwell plates with reagents - Pathogen Kit (ref 4462359)'
    'technician': 'jo',
    'data': '04/29/2020, 17:11:51'
}

#Defined variables
##################
NUM_SAMPLES = 96
air_gap_vol = 15

multi_well_rack_area = 8.2 * 71.2  # Cross section of the 12 well reservoir
num_cols = math.ceil(NUM_SAMPLES / 8)  # Columns we are working on


def run(ctx: protocol_api.ProtocolContext):
    ctx.comment('Actual used columns: ' + str(num_cols))
    # Define the STEPS of the protocol
    STEP = 0
    STEPS = {  # Dictionary with STEP activation, description, and times

        1: {'Execute': True, 'description': 'Add 300 ul Wash Buffer 1 - Round 1'},
        2: {'Execute': True, 'description': 'Add 300 ul Wash Buffer 1 - Round 2'},
        3: {'Execute': True, 'description': 'Add 500 ul Wash Buffer 2 - Round 1'},
        4: {'Execute': True, 'description': 'Add 450 ul Wash Buffer 2 - Round 2'},
        5: {'Execute': True, 'description': 'Add 50 ul Elution Buffer'},
    }

    for s in STEPS:  # Create an empty wait_time
        if 'wait_time' not in STEPS[s]:
            STEPS[s]['wait_time'] = 0
    folder_path = '/var/lib/jupyter/notebooks'
    if not ctx.is_simulating():
        if not os.path.isdir(folder_path):
            os.mkdir(folder_path)
        file_path = folder_path + '/KB_PlateFilling_pathogen_time_log.txt'

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
    WashBuffer1 = Reagent(name='Wash Buffer 1',
                          flow_rate_aspirate=0.75,
                          flow_rate_dispense=1,
                          rinse=True,
                          reagent_reservoir_volume=106000,
                          num_wells=1,  # num_Wells max is 4
                          h_cono=0,
                          v_fondo=0)  # Flat surface

    WashBuffer2 = Reagent(name='Wash Buffer 1',
                          flow_rate_aspirate=0.75,
                          flow_rate_dispense=1,
                          rinse=True,
                          reagent_reservoir_volume=106000,
                          num_wells=1,  # num_Wells max is 4
                          h_cono=0,
                          v_fondo=0)  # Flat surface

    ElutionBuffer = Reagent(name='Elution Buffer',
                            flow_rate_aspirate=1,
                            flow_rate_dispense=1,
                            rinse=False,
                            reagent_reservoir_volume=4800,
                            num_wells=1,  # num_Wells max is 1
                            h_cono=1.95,
                            v_fondo=695)  # Prismatic

    WashBuffer1.vol_well = WashBuffer1.vol_well_original
    WashBuffer2.vol_well = WashBuffer2.vol_well_original
    ElutionBuffer.vol_well = ElutionBuffer.vol_well_original
    #Ethanol.vol_well = Ethanol.vol_well_original
    #WashBuffer.vol_well = WashBuffer.vol_well_original

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
                      reagent.v_cono) / cross_section_area
            #- reagent.h_cono
            reagent.vol_well = reagent.vol_well - aspirate_volume
            ctx.comment('Remaining volume:' + str(reagent.vol_well))
            if height < 0.5:
                height = 0.5
            col_change = True
        else:
            height = (reagent.vol_well - aspirate_volume -
                      reagent.v_cono) / cross_section_area
            reagent.vol_well = reagent.vol_well - aspirate_volume
            ctx.comment('Calculated height is ' + str(height))
            if height < 0.5:
                height = 0.5
            ctx.comment('Used height is ' + str(height))
            col_change = False
        return height, col_change

    def move_vol_multi(pipet, reagent, source, dest, vol, air_gap_vol, x_offset,
                       pickup_height, rinse):
        # Rinse before aspirating
        if rinse == True:
            custom_mix(pipet, reagent, location=source, vol=vol,
                       rounds=2, blow_out=True, mix_height=0)
        # SOURCE
        s = source.bottom(pickup_height).move(Point(x=x_offset))
        pipet.aspirate(vol, s)  # aspirate liquid
        if air_gap_vol != 0:  # If there is air_gap_vol, switch pipette to slow speed
            pipet.aspirate(air_gap_vol, source.top(z=-2),
                           rate=reagent.flow_rate_aspirate)  # air gap
        # GO TO DESTINATION
        pipet.dispense(vol + air_gap_vol, dest.top(z=-2),
                       rate=reagent.flow_rate_dispense)  # dispense all
        pipet.blow_out(dest.top(z=-2))

        # only for multidispensing purposes
        # if air_gap_vol != 0:
        #    pipet.aspirate(air_gap_vol, dest.top(z=-2),
        #                   rate=reagent.flow_rate_aspirate)  # air gap

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
    ####################################
    reagent_res = ctx.load_labware(
        'nest_12_reservoir_15ml', '3', 'Reservoir 12 channel, column 1')

    # WashBuffer1 reservoir
    ####################################
    WashBuffer1_reservoir = ctx.load_labware(
        'nalgene_1_reservoir_300000ul', '2', 'Ethanol 80% reservoir')

    # WashBuffer2 reservoir
    ####################################
    WashBuffer2_reservoir = ctx.load_labware(
        'nalgene_1_reservoir_300000ul', '11', 'WashBuffer reservoir')

    # Wash Buffer 1 300ul Deepwell plate
    ############################################
    WashBuffer1_300ul_plate1 = ctx.load_labware(
        'kf_96_wellplate_2400ul', '1', 'Wash Buffer 1 Deepwell plate 1')

    # Wash Buffer 1 300ul Deepwell plate
    ############################################
    WashBuffer1_300ul_plate2 = ctx.load_labware(
        'kf_96_wellplate_2400ul', '4', 'Wash Buffer 1 Deepwell plate 2')

    # Wash Buffer 2 450ul Deepwell plate
    ############################################
    WashBuffer2_450ul_plate1 = ctx.load_labware(
        'kf_96_wellplate_2400ul', '7', 'Wash Buffer 2 Deepwell plate 1')

    # Wash Buffer 2 450ul Deepwell plate
    ############################################
    WashBuffer2_450ul_plate2 = ctx.load_labware(
        'kf_96_wellplate_2400ul', '10', 'Wash Buffer 2 Deepwell plate 2')

    # Elution Deepwell plate
    ############################################
    ElutionBuffer_50ul_plate = ctx.load_labware(
        'kf_96_wellplate_std_550ul', '6', 'Elution Buffer 50 ul STD plate')

    # Ethanol Deepwell 10000 ul deepwell plate
############################################
    # Ethanol_1000ul_plate = ctx.load_labware(
    # 'kf_96_wellplate_2400ul', '4', 'Ethanol 1000ul Deepwell plate')

    # Wash Buffer Deepwell plate
############################################
    # Ethanol_500ul_plate = ctx.load_labware(
    # 'kf_96_wellplate_2400ul', '7', 'Ethanol 500ul Deepwell plate')


####################################
    # Load tip_racks
    tips300 = [ctx.load_labware('opentrons_96_tiprack_300ul', slot, '200µl filter tiprack')
               for slot in ['8']]
    # tips1000 = [ctx.load_labware('opentrons_96_filtertiprack_1000ul', slot, '1000µl filter tiprack')
    #    for slot in ['10']]

################################################################################
    # Declare which reagents are in each reservoir as well as deepwell and elution plate
    WashBuffer1.reagent_reservoir = WashBuffer1_reservoir.wells()[0]
    WashBuffer2.reagent_reservoir = WashBuffer2_reservoir.wells()[0]
    ElutionBuffer.reagent_reservoir = reagent_res.rows()[0][0]
    #Ethanol.reagent_reservoir = Ethanol_reservoir.wells()[0]

    # columns in destination plates to be filled depending the number of samples
    wb1plate1_destination = WashBuffer1_300ul_plate1.rows()[0][:num_cols]
    wb1plate2_destination = WashBuffer1_300ul_plate2.rows()[0][:num_cols]
    wb2plate1_destination = WashBuffer2_450ul_plate1.rows()[0][:num_cols]
    wb2plate2_destination = WashBuffer2_450ul_plate2.rows()[0][:num_cols]
    elutionbuffer_destination = ElutionBuffer_50ul_plate.rows()[0][:num_cols]
    #washbuffer_destination = WashBuffer_1000ul_plate.rows()[0][:num_cols]

    # pipettes. P1000 currently deactivated
    m300 = ctx.load_instrument(
        'p300_multi_gen2', 'right', tip_racks=tips300)  # Load multi pipette

    # used tip counter and set maximum tips available
    tip_track = {
        'counts': {m300: 0},
        'maxes': {m300: 10000}
    }

    ############################################################################
    # STEP 1 Filling with WashBuffer1 plate 1
    ############################################################################
    STEP += 1
    if STEPS[STEP]['Execute'] == True:
        start = datetime.now()

        ctx.comment('Step ' + str(STEP) + ': ' + STEPS[STEP]['description'])
        ctx.comment('###############################################')

        wash_buffer_vol = [150, 150]
        x_offset = 0
        rinse = False  # Only first time

        ########
        # Wash buffer dispense
        for i in range(num_cols):
            if not m300.hw_pipette['has_tip']:
                pick_up(m300)
            for j, transfer_vol in enumerate(wash_buffer_vol):
                if (i == 0 and j == 0):
                    rinse = True
                else:
                    rinse = False
                move_vol_multi(m300, reagent=WashBuffer1, source=WashBuffer1.reagent_reservoir,
                               dest=wb1plate1_destination[i], vol=transfer_vol,
                               air_gap_vol=air_gap_vol, x_offset=x_offset,
                               pickup_height=1, rinse=rinse)
                ctx.delay(seconds=2)  # 5 sec to let the liquid download
                m300.touch_tip(radius=0.9, speed=20, v_offset=-5)
        m300.drop_tip(home_after=True)
        tip_track['counts'][m300] += 8
        end = datetime.now()
        time_taken = (end - start)
        ctx.comment('Step ' + str(STEP) + ': ' +
                    STEPS[STEP]['description'] + ' took ' + str(time_taken))
        STEPS[STEP]['Time:'] = str(time_taken)

    ############################################################################
    # STEP 2 Filling with WashBuffer1 plate 2
    ############################################################################
    STEP += 1
    if STEPS[STEP]['Execute'] == True:
        start = datetime.now()

        ctx.comment('Step ' + str(STEP) + ': ' + STEPS[STEP]['description'])
        ctx.comment('###############################################')

        wash_buffer_vol = [150, 150]
        x_offset = 0
        rinse = False  # Only first time

        ########
        # Wash buffer dispense
        for i in range(num_cols):
            if not m300.hw_pipette['has_tip']:
                pick_up(m300)
            for j, transfer_vol in enumerate(wash_buffer_vol):
                if (i == 0 and j == 0):
                    rinse = True
                else:
                    rinse = False
                move_vol_multi(m300, reagent=WashBuffer1, source=WashBuffer1.reagent_reservoir,
                               dest=wb1plate2_destination[i], vol=transfer_vol,
                               air_gap_vol=air_gap_vol, x_offset=x_offset,
                               pickup_height=1, rinse=rinse)
                ctx.delay(seconds=2)  # 5 sec to let the liquid download
                m300.touch_tip(radius=0.9, speed=20, v_offset=-5)
        m300.drop_tip(home_after=True)
        tip_track['counts'][m300] += 8
        end = datetime.now()
        time_taken = (end - start)
        ctx.comment('Step ' + str(STEP) + ': ' +
                    STEPS[STEP]['description'] + ' took ' + str(time_taken))
        STEPS[STEP]['Time:'] = str(time_taken)

    ############################################################################
    # STEP 3 Filling with WashBuffer2 plate 1
    ############################################################################
    STEP += 1
    if STEPS[STEP]['Execute'] == True:
        start = datetime.now()

        ctx.comment('Step ' + str(STEP) + ': ' + STEPS[STEP]['description'])
        ctx.comment('###############################################')

        wash_buffer_vol = [150, 150, 150]
        x_offset = 0
        rinse = False  # Only first time

        ########
        # Wash buffer dispense
        for i in range(num_cols):
            if not m300.hw_pipette['has_tip']:
                pick_up(m300)
            for j, transfer_vol in enumerate(wash_buffer_vol):
                if (i == 0 and j == 0):
                    rinse = True
                else:
                    rinse = False
                move_vol_multi(m300, reagent=WashBuffer2, source=WashBuffer2.reagent_reservoir,
                               dest=wb2plate1_destination[i], vol=transfer_vol,
                               air_gap_vol=air_gap_vol, x_offset=x_offset,
                               pickup_height=1, rinse=rinse)
                ctx.delay(seconds=2)  # 5 sec to let the liquid download
                m300.touch_tip(radius=0.9, speed=20, v_offset=-5)
        m300.drop_tip(home_after=True)
        tip_track['counts'][m300] += 8
        end = datetime.now()
        time_taken = (end - start)
        ctx.comment('Step ' + str(STEP) + ': ' +
                    STEPS[STEP]['description'] + ' took ' + str(time_taken))
        STEPS[STEP]['Time:'] = str(time_taken)

    ############################################################################
    # STEP 4 Filling with WashBuffer2 plate 2
    ############################################################################
    STEP += 1
    if STEPS[STEP]['Execute'] == True:
        start = datetime.now()

        ctx.comment('Step ' + str(STEP) + ': ' + STEPS[STEP]['description'])
        ctx.comment('###############################################')

        ethanol_vol = [150, 150, 150]
        x_offset = 0
        rinse = False  # Only first time

        ########
        # Ethanol dispense
        for i in range(num_cols):
            if not m300.hw_pipette['has_tip']:
                pick_up(m300)
            for j, transfer_vol in enumerate(ethanol_vol):
                if (i == 0 and j == 0):
                    rinse = True
                else:
                    rinse = False
                move_vol_multi(m300, reagent=WashBuffer2, source=WashBuffer2.reagent_reservoir,
                               dest=wb2plate2_destination[i], vol=transfer_vol,
                               air_gap_vol=air_gap_vol, x_offset=x_offset,
                               pickup_height=1, rinse=rinse)
                ctx.delay(seconds=2)  # 5 sec to let the liquid download
                m300.touch_tip(radius=0.9, speed=20, v_offset=-5)
        m300.drop_tip(home_after=True)
        tip_track['counts'][m300] += 8
        end = datetime.now()
        time_taken = (end - start)
        ctx.comment('Step ' + str(STEP) + ': ' +
                    STEPS[STEP]['description'] + ' took ' + str(time_taken))
        STEPS[STEP]['Time:'] = str(time_taken)

    ############################################################################
    # STEP 5 Transfer Elution buffer
    ############################################################################

    STEP += 1
    if STEPS[STEP]['Execute'] == True:
        start = datetime.now()
        ctx.comment('Step ' + str(STEP) + ': ' + STEPS[STEP]['description'])
        ctx.comment('###############################################')
        # Elution buffer
        ElutionBuffer_vol = [50]
        air_gap_vol_elutionbuffer = 10
        x_offset = 0

        ########
        # Water or elution buffer
        for i in range(num_cols):
            if not m300.hw_pipette['has_tip']:
                pick_up(m300)
            for transfer_vol in ElutionBuffer_vol:
                # Calculate pickup_height based on remaining volume and shape of container
                [pickup_height, change_col] = calc_height(
                    ElutionBuffer, multi_well_rack_area, transfer_vol * 8)
                ctx.comment(
                    'Aspirate from Reservoir column: ' + str(ElutionBuffer.col))
                ctx.comment('Pickup height is ' + str(pickup_height))
                move_vol_multi(m300, reagent=ElutionBuffer, source=ElutionBuffer.reagent_reservoir,
                               dest=elutionbuffer_destination[i], vol=transfer_vol,
                               air_gap_vol=air_gap_vol_elutionbuffer, x_offset=x_offset,
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
                row = str(key)
                for key2 in STEPS[key].keys():
                    row += '\t' + format(STEPS[key][key2])
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
        'Finished! \nMove deepwell plates to KingFisher extractor.')
    ctx.comment('Used tips in total: ' + str(tip_track['counts'][m300]))
    ctx.comment('Used racks in total: ' + str(tip_track['counts'][m300] / 96))
