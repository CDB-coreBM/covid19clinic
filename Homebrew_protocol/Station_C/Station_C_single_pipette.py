from opentrons import protocol_api
from opentrons.drivers.rpi_drivers import gpio
from opentrons.types import Point
import math
from timeit import default_timer as timer
import json
from datetime import datetime
import csv
import os
import numpy as np

# metadata
metadata = {
    'protocolName': 'S2 Station C ROCHE Master Mix Version 1',
    'author': 'Aitor & JL (jlvillanueva@clinic.cat)',
    'source': 'Custom Protocol',
    'apiLevel': '2.0'}

"""
REAGENT SETUP:
- slot 1 2ml screwcap in tuberack:
    - mastermix ROCHE: tube A1
"""

# Initial variables
NUM_SAMPLES = 16
run_id = 'R001'

# Tune variables
air_gap_vol = 5 # General air gap volume
volume_mmix = 15  # Volume of transfered master mix
height_mmix = -15  # Height to dispense mmix
MMIX_initial_volume = 300 #Initial volume of mmix screwcap

volume_sample = 5  # Volume of the sample

temperature = 25  # Temperature of temp module
diameter_screwcap = 8.25  # Diameter of the screwcap
volume_cone = 50  # Volume in ul that fit in the screwcap cone

# Calculated variables
area_section_screwcap = (math.pi * diameter_screwcap**2) / 4
h_cone = (volume_cone * 3 / area_section_screwcap)

def check_door():
    return gpio.read_window_switches()

def run(ctx: protocol_api.ProtocolContext):
    global volume_screw
    unused_volume_one = 0

    STEP = 0
    STEPS = {  # Dictionary with STEP activation, description, and times
        1: {'Execute': True, 'description': 'Transfer MMIX'},
        2: {'Execute': False, 'description': 'Transfer elution'}
    }
    for s in STEPS:  # Create an empty wait_time
        if 'wait_time' not in STEPS[s]:
            STEPS[s]['wait_time'] = 0

    #Folder and file_path for log time
    folder_path = '/var/lib/jupyter/notebooks/'+run_id
    if not ctx.is_simulating():
        if not os.path.isdir(folder_path):
            os.mkdir(folder_path)
        file_path = folder_path + '/StationC_homebrew_time_log.txt'
        file_path2 = folder_path + '/StationC_homebrew_tips_log.txt'

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
    MasterMix = Reagent(name = 'MasterMix',
                     flow_rate_aspirate = 1,
                     flow_rate_dispense = 1,
                     rinse = False,
                     reagent_reservoir_volume = MMIX_initial_volume,
                     delay=0,
                     num_wells = 1,  # num_Wells max is 4
                     h_cono = (volume_cone * 3 / area_section_screwcap),
                     v_fondo = 50
                     )

    Samples = Reagent(name = 'Samples',
                      flow_rate_aspirate = 1,
                      flow_rate_dispense = 1,
                      rinse = False,
                      reagent_reservoir_volume = 45*96,
                      delay=0,
                      num_wells = 96,
                      h_cono = 0,
                      v_fondo = 0
                      )

    MasterMix.vol_well = MasterMix.vol_well_original
    Samples.vol_well = 45

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

    # Check if door is opened
    if check_door() == True:
        # Set light color to purple
        gpio.set_button_light(0.5, 0, 0.5)
    else:
        # Set light color to red
        gpio.set_button_light(1, 0, 0)

    # Load labware
    source_plate = ctx.load_labware(
        'pcr_transparent_96_wellplate_200ul_alum_covid', '1',
        'chilled RNA elution plate from station B')

    tuberack = ctx.load_labware(
        'opentrons_24_aluminumblock_generic_2ml_screwcap', '2',
        'Bloque Aluminio opentrons 24 screwcaps 2000 µL ')
    tempdeck = ctx.load_module('tempdeck', '4')

    # Define temperature of module. Should be 4. 25 for testing purposes
    #tempdeck.set_temperature(temperature)

    pcr_plate = tempdeck.load_labware(
        'roche_96_wellplate_lightcycler_100ul_alum_opentrons', 'PCR plate')

    # Load Tipracks
    tips20 = [
        ctx.load_labware('opentrons_96_filtertiprack_20ul', slot)
        for slot in ['5']
    ]

    tips200 = [
        ctx.load_labware('opentrons_96_filtertiprack_200ul', slot)
        for slot in ['6']
    ]

    # waste_pool = ctx.load_labware('nalgene_1_reservoir_300000ul', '11',
    # 'waste reservoir nalgene')

    # pipettes
    p20 = ctx.load_instrument(
        'p20_single_gen2', mount='right', tip_racks=tips20)
    #p300 = ctx.load_instrument(
    #    'p300_single_gen2', mount='left', tip_racks=tips200)

    tip_track = {
        'counts': {p20: 0},
        'maxes': {p20: 10000}
    }
    # setup up sample sources and destinations
    elution_sources = source_plate.wells()[:NUM_SAMPLES]
    destinations = pcr_plate.wells()[:NUM_SAMPLES]
    MasterMix.reagent_reservoir = tuberack.wells()[0]

    # Set mmix source to first screwcap
    used_vol=[]

    ############################################################################
    # STEP 1: Add Master Mix
    ############################################################################
    STEP += 1
    if STEPS[STEP]['Execute'] == True:
        ctx.comment('Step ' + str(STEP) + ': ' + STEPS[STEP]['description'])
        ctx.comment('###############################################')

        # Transfer parameters
        start = datetime.now()
        if not p20.hw_pipette['has_tip']:
            pick_up(p20)
        for d in destinations:
            # Calculate pickup_height based on remaining volume and shape of container
            [pickup_height, change_col] = calc_height(MasterMix, area_section_screwcap, volume_mmix)
            move_vol_multichannel(p20, reagent = MasterMix, source = MasterMix.reagent_reservoir,
            dest = d, vol = volume_mmix, air_gap_vol = air_gap_vol, x_offset = [0,0],
                   pickup_height = pickup_height, disp_height = height_mmix, rinse = False,
                   blow_out=True, touch_tip=False)
            used_vol.append(volume_mmix)

        #Drop tip and update counter
        p20.drop_tip()
        tip_track['counts'][p20]+=1

        #Time statistics
        end = datetime.now()
        time_taken = (end - start)
        ctx.comment('Step ' + str(STEP) + ': ' + STEPS[STEP]['description'] +
        ' took ' + str(time_taken))
        STEPS[STEP]['Time:'] = str(time_taken)

    ############################################################################
    # STEP 2: Add Samples
    ############################################################################
    STEP += 1
    if STEPS[STEP]['Execute'] == True:
        ctx.comment('Step ' + str(STEP) + ': ' + STEPS[STEP]['description'])
        ctx.comment('###############################################')

        # Transfer parameters
        start = datetime.now()
        for s, d in zip(elution_sources, destinations):
            if not p20.hw_pipette['has_tip']:
                pick_up(p20)
            move_vol_multichannel(p20, reagent = Samples, source = s, dest = d,
            vol = volume_sample, air_gap_vol = air_gap_vol, x_offset = [0,0],
                   pickup_height = 1, disp_height = -5, rinse = False,
                   blow_out=True, touch_tip=False)

            custom_mix(p20, reagent = Samples, location = d, vol = volume_sample,
            rounds = 2, blow_out = True, mix_height = 10, x_offset=[0,0])
            p20.aspirate(5, d.top(2))
            #Drop tip and update counter
            p20.drop_tip()
            tip_track['counts'][p20]+=1

        #Time statistics
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
        with open(file_path2, 'w') as f2:
            f2.write('pipette\ttip_count\n')
            for key in tip_track['counts'].keys():
                row=str(key)
                f.write(str(key)+'\t'+format(tip_track['counts'][key]))
        f2.close()


    # Set light color to green
    gpio.set_button_light(0, 1, 0)
    os.system('mpg123 -f -20000 /var/lib/jupyter/notebooks/lionking.mp3 &')
    # Print the values of master mix used and remaining theoretical volume
    if STEPS[1]['Execute'] == True:
        total_used_vol = np.sum(used_vol)
        total_needed_volume = total_used_vol + unused_volume_one  * len(destinations)
        ctx.comment('Total used volume is: ' + str(total_used_vol) + '\u03BCl.')
        ctx.comment('Volume remaining in first tube is:' +
                    format(int(unused_volume_one)) + '\u03BCl.')
        ctx.comment('Needed volume is ' +
                    format(int(total_needed_volume)) + '\u03BCl')
        ctx.comment('Used volumes per run are: ' + str(used_vol) + '\u03BCl.')
