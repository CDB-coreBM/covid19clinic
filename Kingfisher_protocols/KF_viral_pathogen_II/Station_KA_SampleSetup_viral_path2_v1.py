import math
from opentrons.types import Point
from opentrons import protocol_api
import time
import os
from timeit import default_timer as timer
import json
from datetime import datetime
import csv

# metadata
metadata = {
    'protocolName': 'S2 Station A Kingfisher Version 2',
    'author': 'Eva González & José Luis Villanueva (jlvillanueva@clinic.cat)',
    'source': 'Hospital Clínic Barcelona',
    'apiLevel': '2.0',
    'description': 'Protocol for Kingfisher sample setup (A) - Viral/Pathogen II Kit (ref A48383)'
}

'''
'technician': '$technician',
'date': '$date'
'''

#Defined variables
##################
NUM_SAMPLES = 16
air_gap_vol = 15

volume_sample = 400
x_offset = [0,0]

# Screwcap variables
diameter_screwcap = 8.25  # Diameter of the screwcap
volume_cone = 50  # Volume in ul that fit in the screwcap cone

# Calculated variables
area_section_screwcap = (math.pi * diameter_screwcap**2) / 4
h_cone = (volume_cone * 3 / area_section_screwcap)
screwcap_cross_section_area = math.pi * \
    diameter_screwcap**2 / 4  # screwcap cross section area


def run(ctx: protocol_api.ProtocolContext):

    # Define the STEPS of the protocol
    STEP = 0
    STEPS = {  # Dictionary with STEP activation, description, and times
        1: {'Execute': True, 'description': 'Add samples (400ul)'},
    }
    for s in STEPS:  # Create an empty wait_time
        if 'wait_time' not in STEPS[s]:
            STEPS[s]['wait_time'] = 0

    if not ctx.is_simulating():
        # Folder and file_path for log time
        folder_path = '/var/lib/jupyter/notebooks'
        if not os.path.isdir(folder_path):
            os.mkdir(folder_path)
        file_path = folder_path + '/KA_SampleSetup_pathogen_time_log.txt'
        file_path = folder_path + '/KA_SampleSetup_viral_path2_time_log.txt'

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

    Samples = Reagent(name = 'Samples',
                      flow_rate_aspirate = 1,
                      flow_rate_dispense = 1,
                      rinse = False,
                      delay = 0,
                      reagent_reservoir_volume = 700 * 24,
                      num_wells = 24,  # num_cols comes from available columns
                      h_cono = 4,
                      v_fondo = 4 * math.pi * 4**3 / 3
                      )  # Sphere

    Samples.vol_well = 700

    ##################
    # Custom functions
    def generate_source_table(source):
        '''
        Concatenate the wells from the different origin racks
        '''
        for rack_number in range(len(source)):
            if rack_number == 0:
                s = source[rack_number].wells()
            else:
                s = s + source[rack_number].wells()
        return s

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
        pipet.aspirate(vol, s, rate = reagent.flow_rate_aspirate)  # aspirate liquid
        if air_gap_vol != 0:  # If there is air_gap_vol, switch pipette to slow speed
            pipet.aspirate(air_gap_vol, source.top(z = -2),
                           rate = reagent.flow_rate_aspirate)  # air gap
        # GO TO DESTINATION
        drop = dest.top(z = disp_height).move(Point(x = x_offset[1]))
        pipet.dispense(vol + air_gap_vol, drop,
                       rate = reagent.flow_rate_dispense)  # dispense all
        ctx.delay(seconds = reagent.delay) # pause for x seconds depending on reagent
        if blow_out == True:
            pipet.blow_out(dest.top(z = -5))
        if touch_tip == True:
            pipet.touch_tip(radius = 0.9, speed = 20, v_offset = -5)


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

    def calc_height(reagent, cross_section_area, aspirate_volume, min_height = 0.5, extra_volume = 50):
        nonlocal ctx
        ctx.comment('Remaining volume ' + str(reagent.vol_well) +
                    '< needed volume ' + str(aspirate_volume) + '?')
        if reagent.vol_well < aspirate_volume + extra_volume:
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

    ####################################
    # load labware and modules

    ####################################
    # Load Sample racks
    if NUM_SAMPLES < 96:
        rack_num = math.ceil(NUM_SAMPLES / 24)
        ctx.comment('Used source racks are ' + str(rack_num))
        samples_last_rack = NUM_SAMPLES - rack_num * 24
    else:
        rack_num = 4
    source_racks = [ctx.load_labware(
        'opentrons_24_tuberack_generic_2ml_screwcap', slot,
        'source tuberack with screwcap' + str(i + 1)) for i, slot in enumerate(['4', '1', '6', '3'][:rack_num])
    ]

    ##################################
    # Destination plate
    dest_plate = ctx.load_labware(
        'kf_96_wellplate_2400ul', '5', 'KF 96well destination plate')

    ####################################
    # Load tip_racks
    # tips20 = [ctx.load_labware('opentrons_96_filtertiprack_20ul', slot, '20µl filter tiprack')
    # for slot in ['2', '8']]
    tips1000 = [ctx.load_labware('opentrons_96_filtertiprack_1000ul', slot, '1000µl filter tiprack')
                for slot in ['7', '10']]

    ################################################################################
    # Declare which reagents are in each reservoir as well as deepwell and elution plate

    # setup samples and destinations
    sample_sources_full = generate_source_table(source_racks)
    sample_sources = sample_sources_full[:NUM_SAMPLES]
    destinations = dest_plate.wells()[:NUM_SAMPLES]

    # p20 = ctx.load_instrument(
    # 'p20_single_gen2', mount='right', tip_racks=tips20)
    p1000 = ctx.load_instrument(
        'p1000_single_gen2', 'left', tip_racks=tips1000)  # load P1000 pipette

    # used tip counter and set maximum tips available
    tip_track = {
        'counts': {p1000: 0},  # p1000: 0},
        'maxes': {p1000: len(tips1000) * 96}  # ,p20: len(tips20)*96,
    }

    ############################################################################
    # STEP 1: Add Samples
    ############################################################################
    STEP += 1
    if STEPS[STEP]['Execute'] == True:
        ctx.comment('Step ' + str(STEP) + ': ' + STEPS[STEP]['description'])
        ctx.comment('###############################################')

        # Transfer parameters
        start = datetime.now()
        for s, d in zip(sample_sources, destinations):
            if not p1000.hw_pipette['has_tip']:
                pick_up(p1000)
            # Mix the sample BEFORE dispensing
            #custom_mix(p1000, reagent = Samples, location = s, vol = volume_sample, rounds = 2, blow_out = True, mix_height = 15)
            move_vol_multichannel(p1000, reagent = Samples, source = s, dest = d,
            vol=volume_sample, air_gap_vol = air_gap_vol, x_offset = x_offset,
                               pickup_height = 1, rinse = Samples.rinse, disp_height = -10,
                               blow_out = True, touch_tip = True)
            # Mix the sample AFTER dispensing
            #custom_mix(p1000, reagent = Samples, location = d, vol = volume_sample, rounds = 2, blow_out = True, mix_height = 15)
            # Drop tip and update counter
            p1000.drop_tip()
            tip_track['counts'][p1000] += 1

        # Time statistics
        end = datetime.now()
        time_taken = (end - start)
        ctx.comment('Step ' + str(STEP) + ': ' + STEPS[STEP]['description'] +
                    ' took ' + str(time_taken))
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
        'Finished! \nMove deepwell plate (slot 5) to Station C for MMIX addition and qPCR preparation.')
    ctx.comment('Used p1000 tips in total: ' + str(tip_track['counts'][p1000]))
    ctx.comment('Used p1000 racks in total: ' +
                str(tip_track['counts'][p1000] / 96))
    #ctx.comment('Used p20 tips in total: ' + str(tip_track['counts'][p20]))
    #ctx.comment('Used p20 racks in total: ' + str(tip_track['counts'][p20] / 96))
