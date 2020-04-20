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
    'description': 'Protocol for Kingfisher sample setup (C)'
}

#Defined variables
##################
NUM_SAMPLES = 96
air_gap_vol = 15

# Tune variables
size_transfer = 7  # Number of wells the distribute function will fill
volume_mmix = 20  # Volume of transfered master mix
volume_sample = 5  # Volume of the sample
volume_screw_one = 1200  # Total volume of first screwcap
volume_screw_two = 1100  # Total volume of second screwcap
extra_dispensal = 5  # Extra volume for master mix in each distribute transfer
diameter_screwcap = 8.25  # Diameter of the screwcap
temperature = 25  # Temperature of temp module
volume_cone = 50  # Volume in ul that fit in the screwcap cone
x_offset=0

# Calculated variables
area_section_screwcap = (np.pi * diameter_screwcap**2) / 4
h_cone = (volume_cone * 3 / area_section_screwcap)
num_cols = math.ceil(NUM_SAMPLES / 8)  # Columns we are working on


def run(ctx: protocol_api.ProtocolContext):
    ctx.comment('Actual used columns: ' + str(num_cols))
    STEP = 0
    STEPS = {  # Dictionary with STEP activation, description, and times
        1: {'Execute': True, 'description': 'Transfer MMIX'},
        2: {'Execute': True, 'description': 'Transfer elution'}
    }
    for s in STEPS:  # Create an empty wait_time
        if 'wait_time' not in STEPS[s]:
            STEPS[s]['wait_time'] = 0

    #Folder and file_path for log time
    folder_path = '/data/log_times/'
    if not ctx.is_simulating():
        if not os.path.isdir(folder_path):
            os.mkdir(folder_path)
        file_path = folder_path + '/time_log.json'

    # Define Reagents as objects with their properties
    class Reagent:
        def __init__(self, name, rinse,h_cono, v_fondo,
                     reagent_reservoir_volume_1,reagent_reservoir_volume_2,
                      num_wells= 1, tip_recycling=None):
            self.name = name
            self.rinse = bool(rinse)
            self.flow_rate_aspirate = 1
            self.flow_rate_dispense = 1
            self.reagent_reservoir_volume_1 = reagent_reservoir_volume_1
            self.reagent_reservoir_volume_2 = reagent_reservoir_volume_2
            self.col = 0
            self.vol_well = self.reagent_reservoir_volume_1
            self.h_cono = h_cono
            self.v_cono = v_fondo
            self.tip_recycling = tip_recycling
            self.unused_one=0
            self.unused_two=0

    # Reagents and their characteristics
    MMIX = Reagent(name='Master Mix',
                      rinse=False,
                      reagent_reservoir_volume_1=volume_screw_one,
                      reagent_reservoir_volume_2=volume_screw_two,
                      h_cono=h_cone,
                      v_fondo=volume_cone  # V cono
                      )

    Elution = Reagent(name='Elution',
                      rinse=False,
                      reagent_reservoir_volume_1=50,
                      reagent_reservoir_volume_2=0,
                      num_wells=num_cols,  # num_cols comes from available columns
                      h_cono=0,
                      v_fondo=0
                      )


    ##################
    # Custom functions

    def calc_height(reagent, cross_section_area, aspirate_volume):
        nonlocal ctx
        ctx.comment('Remaining volume ' + str(reagent.vol_well) +
                    '< needed volume ' + str(aspirate_volume) + ', is that okay?')
        if reagent.vol_well < aspirate_volume:
            reagent.unused_one=reagent.vol_well
            ctx.comment('Next column should be picked')
            ctx.comment('Previous to change: ' + str(reagent.col))
            # column selector position; intialize to required number
            reagent.col = reagent.col + 1
            ctx.comment(str('After change: ' + str(reagent.col)))

            reagent.vol_well = reagent.reagent_reservoir_volume_2

            ctx.comment('New volume:' + str(reagent.vol_well))
            height = (reagent.vol_well - aspirate_volume -
                      reagent.v_cono) / cross_section_area - reagent.h_cono
            reagent.vol_well = reagent.vol_well - aspirate_volume
            ctx.comment('Remaining volume:' + str(reagent.vol_well))
            ctx.comment('Calculated height is ' + str(height))
            if height <= 0:
                height = 0.2
            col_change = True
        else:
            height = (reagent.vol_well - aspirate_volume -
                      reagent.v_cono) / cross_section_area - reagent.h_cono
            reagent.vol_well = reagent.vol_well - aspirate_volume
            ctx.comment('Calculated height is ' + str(height))
            if height <= 0:
                height = 0.2
            ctx.comment('Used height is ' + str(height))
            col_change = False
        return height, col_change

    def divide_destinations(l, n):
        # Divide the list of destinations in size n lists.
        for i in range(0, len(l), n):
            yield l[i:i + n]

    def distribute_custom(pipette, volume, src, dest, waste_pool, pickup_height, extra_dispensal):
        # Custom distribute function that allows for blow_out in different location and adjustement of touch_tip
        pipette.aspirate((len(dest) * volume) +
                         extra_dispensal, src.bottom(pickup_height))
        pipette.touch_tip(speed=20, v_offset=-5)
        pipette.move_to(src.top(z=5))
        pipette.aspirate(5)  # air gap
        for d in dest:
            pipette.dispense(5, d.top())
            pipette.dispense(volume, d)
            pipette.move_to(d.top(z=5))
            pipette.aspirate(5)  # air gap
        try:
            pipette.blow_out(waste_pool.wells()[0].bottom(pickup_height + 3))
        except:
            pipette.blow_out(waste_pool.bottom(pickup_height + 3))
        return (len(dest) * volume)

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
            pipet.aspirate(air_gap_vol, source.top(z=-2))  # air gap
        # GO TO DESTINATION
        pipet.dispense(vol + air_gap_vol, dest.top(z=-2))
        pipet.blow_out(dest.top(z=-2))
        if air_gap_vol != 0:
            pipet.aspirate(air_gap_vol, dest.top(z=-2))  # air gap

####################################
    # load labware and modules
    # 12 well rack
    tuberack = ctx.load_labware(
        'bloquealuminio_24_screwcap_wellplate_1500ul', '2',
        'Bloque Aluminio 24 Screwcap Well Plate 1500 µL ')

############################################
    # tempdeck
    tempdeck = ctx.load_module('tempdeck', '3')
    # tempdeck.set_temperature(temperature)

##################################
    # Elution plate - final plate, goes to PCR
    elution_plate = tempdeck.load_labware(
        'roche_96_wellplate_100ul',
        'chilled RNA elution plate from station B ')

##################################
    # Sample plate - comes from B
    source_plate = ctx.load_labware(
        'roche_96_wellplate_100ul', '1',
        'Chilled RNA elution plate for PCR ')
    samples = source_plate.wells()[:NUM_SAMPLES]

##################################
    # Load Tipracks
    tips20 = [
        ctx.load_labware('opentrons_96_filtertiprack_20ul', slot)
        for slot in ['5']
    ]

    tips200 = [
        ctx.load_labware('opentrons_96_filtertiprack_200ul', slot)
        for slot in ['6']
    ]

################################################################################
    # Declare which reagents are in each reservoir as well as deepwell and elution plate
    MMIX_reservoir = [tuberack.rows()[0][0], tuberack.rows()[0][1]] # 1 row, 2 columns (first ones)
    # setup up sample sources and destinations
    samples = source_plate.wells()[:NUM_SAMPLES]
    pcr_wells = elution_plate.wells()[:NUM_SAMPLES]

    # Divide destination wells in small groups for P300 pipette
    dests = list(divide_destinations(pcr_wells, size_transfer))


    # pipettes
    p20 = ctx.load_instrument(
        'p20_single_gen2', mount='right', tip_racks=tips20)
    p300 = ctx.load_instrument(
        'p300_single_gen2', mount='left', tip_racks=tips200)

    # used tip counter and set maximum tips available
    tip_track = {
        'counts': {p300: 0,p20: 0}
    }
    # , p1000: len(tips1000)*96}

    ############################################################################
    # STEP 1: Transfer Master MIX
    ############################################################################
    STEP += 1
    if STEPS[STEP]['Execute'] == True:
        start = datetime.now()
        p300.pick_up_tip()
        tip_track['counts'][p300]+=1
        used_vol=[]
        for dest in dests:

            aspirate_volume=volume_mmix * len(dest) + extra_dispensal + 35
            [pickup_height,col_change]=calc_height(MMIX, area_section_screwcap, aspirate_volume)

            # source MMIX_reservoir[col_change]
            used_vol_temp = distribute_custom(
                p300, volume_mmix, MMIX_reservoir[col_change], dest,
                MMIX_reservoir[col_change], pickup_height, extra_dispensal)

            used_vol.append(used_vol_temp)

        p300.drop_tip()
        MMIX.unused_two = MMIX.vol_well

        end = datetime.now()
        time_taken = (end - start)
        ctx.comment('Step ' + str(STEP) + ': ' +
                    STEPS[STEP]['description'] + ' took ' + str(time_taken))
        STEPS[STEP]['Time:'] = str(time_taken)

    ############################################################################
    # STEP 2: TRANSFER Samples
    ############################################################################
    STEP += 1
    if STEPS[STEP]['Execute'] == True:
        # Transfer parameters
        start = datetime.now()
        for s, d in zip(pcr_wells, samples):
            p20.pick_up_tip()
            tip_track['counts'][p20]+=1
            p20.transfer(volume_sample, s, d, new_tip='never')
            p20.mix(1, 10, d)
            p20.aspirate(5, d.top(2))
            p20.drop_tip()
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
    gpio.set_rail_lights(False)
    time.sleep(1)
    gpio.set_rail_lights(True)
    os.system('mpg123 -f 14000 /var/lib/jupyter/notebooks/lionking.mp3')
    for i in range(3):
        gpio.set_rail_lights(False)
        gpio.set_button_light(1, 0, 0)
        time.sleep(0.3)
        gpio.set_rail_lights(True)
        gpio.set_button_light(0, 0, 1)
        time.sleep(0.3)
    gpio.set_button_light(0, 1, 0)
    ctx.comment(
        'Finished! \nMove plate to PCR')
    total_used_vol = np.sum(used_vol)
    total_needed_volume = total_used_vol + MMIX.unused_one + \
        MMIX.unused_two + extra_dispensal * len(dests)
    ctx.comment('Total Master Mix used volume is: ' + str(total_used_vol) + '\u03BCl.')
    ctx.comment('Needed Master Mix volume is ' +
                format(int(total_needed_volume)) + '\u03BCl')
    ctx.comment('Used Master Mix volumes per run are: ' + str(used_vol) + '\u03BCl.')
    ctx.comment('200 ul Used tips in total: ' + str(tip_track['counts'][p300]))
    ctx.comment('200 ul Used racks in total: ' + str(tip_track['counts'][p300] / 96))
    ctx.comment('20 ul Used tips in total: ' + str(tip_track['counts'][p20]))
    ctx.comment('20 ul Used racks in total: ' + str(tip_track['counts'][p20] / 96))
    ctx.comment('Master Mix Volume remaining in first tube is:' +
                format(int(MMIX.unused_one)) + '\u03BCl.')
    ctx.comment('Master Mix Volume remaining in second tube is:' +
                format(int(MMIX.unused_two)) + '\u03BCl.')
