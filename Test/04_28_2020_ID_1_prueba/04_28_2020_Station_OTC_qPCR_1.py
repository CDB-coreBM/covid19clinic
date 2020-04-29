from opentrons import protocol_api
from opentrons.drivers.rpi_drivers import gpio
import numpy as np
from timeit import default_timer as timer
import json
from datetime import datetime
import csv
import os

# metadata
metadata = {
    'protocolName': 'S2 Station C Version 7',
    'author': 'Aitor & JL (jlvillanueva@clinic.cat)',
    'source': 'Custom Protocol',
    'apiLevel': '2.0',
    'technician': 'hola',
    'data': '04/28/2020, 19:15:11'
}

"""
REAGENT SETUP:
- slot 2 2ml screwcap in tuberack:
    - mastermix: tube A1
    - mastermix: tube A2
"""

# Initial variables
NUM_SAMPLES = 18

# Tune variables
size_transfer = 12  # Number of wells the distribute function will fill

#ROCHE MMIX
volume_mmix = 15 #24.6  # Volume of transfered master mix
volume_sample = 5 #5.4  # Volume of the sample

#SUPERSCRIPT MMIX
#volume_mmix = 24.6  # Volume of transfered master mix
#volume_sample = 5.4  # Volume of the sample

volume_screw_one = 285  # Total volume of first screwcap
volume_screw_two = 0  # Total volume of second screwcap
extra_dispensal = 5  # Extra volume for master mix in each distribute transfer
diameter_screwcap = 8.25  # Diameter of the screwcap
temperature = 4  # Temperature of temp module
volume_cone = 50  # Volume in ul that fit in the screwcap cone

# Calculated variables
area_section_screwcap = (np.pi * diameter_screwcap**2) / 4
h_cone = (volume_cone * 3 / area_section_screwcap)


def divide_destinations(l, n):
    # Divide the list of destinations in size n lists.
    for i in range(0, len(l), n):
        yield l[i:i + n]


def check_door():
    return gpio.read_window_switches()


def distribute_custom(pipette, volume_mmix, mmix, dest, waste_pool, pickup_height, extra_dispensal):
    # Custom distribute function that allows for blow_out in different location and adjustement of touch_tip
    pipette.aspirate((len(dest) * volume_mmix) +
                     extra_dispensal, mmix.bottom(pickup_height))
    pipette.touch_tip(speed=20, v_offset=-5)
    pipette.move_to(mmix.top(z=5))
    pipette.aspirate(5)  # air gap
    for d in dest:
        pipette.dispense(5, d.top())
        pipette.dispense(volume_mmix, d)
        pipette.move_to(d.top(z=5))
        pipette.aspirate(5)  # air gap
    try:
        pipette.blow_out(waste_pool.wells()[0].bottom(pickup_height + 3))
    except:
        pipette.blow_out(waste_pool.bottom(pickup_height + 3))
    return (len(dest) * volume_mmix)


def run(ctx: protocol_api.ProtocolContext):
    global volume_screw_one
    global volume_screw_two
    global volume_screw
    volume_screw = volume_screw_one
    unused_volume_one = 0
    unused_volume_two = 0

    STEP = 0
    STEPS = {  # Dictionary with STEP activation, description, and times
        1: {'Execute': True, 'description': 'Transfer MMIX'},
        2: {'Execute': True, 'description': 'Transfer elution'}
    }

    for s in STEPS:  # Create an empty wait_time
        if 'wait_time' not in STEPS[s]:
            STEPS[s]['wait_time'] = 0

    #Folder and file_path for log time
    folder_path = '/var/lib/jupyter/notebooks'
    if not ctx.is_simulating():
        if not os.path.isdir(folder_path):
            os.mkdir(folder_path)
        file_path = folder_path + '/StationC_time_log.txt'

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
        'bloquealuminio_24_screwcap_wellplate_1500ul', '2',
        'Bloque Aluminio 24 Eppendorf Well Plate 1500 µL')

    tempdeck = ctx.load_module('tempdeck', '4')

    # Define temperature of module. Should be 4. 25 for testing purposes
    tempdeck.set_temperature(temperature)

    pcr_plate = tempdeck.load_labware(
        'roche_96_wellplate_100ul_alum_covid', 'PCR plate')

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
    p300 = ctx.load_instrument(
        'p300_single_gen2', mount='left', tip_racks=tips200)

    # setup up sample sources and destinations
    samples = source_plate.wells()[:NUM_SAMPLES]
    pcr_wells = pcr_plate.wells()[:NUM_SAMPLES]

    # Divide destination wells in small groups for P300 pipette
    dests = list(divide_destinations(pcr_wells, size_transfer))

    # Set mmix source to first screwcap
    mmix = tuberack.wells()[0]

    # transfer mastermix with P300
    STEP += 1
    if STEPS[STEP]['Execute'] == True:
        start = datetime.now()
        p300.pick_up_tip()
        pickup_height = ((volume_screw - volume_cone) /
                         area_section_screwcap - h_cone)
        used_vol = []
        volume_screw = volume_screw_one
        for dest in dests:
            # We make sure there is enough volume in screwcap one or we switch
            ctx.comment('Needed volume is: '+str(volume_mmix * len(dest) + extra_dispensal + 35)
                +'\u03BCl., available is '+str(volume_screw)+'\u03BCl.')
            if volume_screw < (volume_mmix * len(dest) + extra_dispensal + 35):
                unused_volume_one = volume_screw
                mmix = tuberack.wells()[4]
                volume_screw = volume_screw_two  # New tube is full now
                pickup_height = ((volume_screw - volume_cone) /
                                 area_section_screwcap - h_cone)
            if pickup_height<=0:
                pickup_height=0.5
            # Distribute the mmix in different wells
            ctx.comment('height is '+str(pickup_height))
            used_vol_temp = distribute_custom(
                p300, volume_mmix, mmix, dest, mmix, pickup_height, extra_dispensal)
            used_vol.append(used_vol_temp)
            # Update volume left in screwcap
            volume_screw = volume_screw - \
                (volume_mmix * len(dest) + extra_dispensal)

            # Update pickup_height according to volume left
            pickup_height = ((volume_screw - volume_cone) /
                             area_section_screwcap - h_cone)

        p300.drop_tip()
        end = datetime.now()
        time_taken = (end - start)
        ctx.comment('Step ' + str(STEP) + ': ' +
                    STEPS[STEP]['description'] + ' took ' + str(time_taken))
        STEPS[STEP]['Time:'] = str(time_taken)

    # transfer samples to corresponding locations with p20
    STEP += 1
    if STEPS[STEP]['Execute'] == True:
        # Transfer parameters
        start = datetime.now()
        for s, d in zip(samples, pcr_wells):
            p20.pick_up_tip()
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
                row = str(key)
                for key2 in STEPS[key].keys():
                    row += '\t' + format(STEPS[key][key2])
                f.write(row + '\n')
        f.close()

    # Set light color to green
    gpio.set_button_light(0, 1, 0)
    os.system('mpg123 -f -20000 /var/lib/jupyter/notebooks/lionking.mp3 &')
    # Print the values of master mix used and remaining theoretical volume
    if STEPS[1]['Execute'] == True:
        total_used_vol = np.sum(used_vol)
        total_needed_volume = total_used_vol + unused_volume_one + \
            unused_volume_two + extra_dispensal * len(dests)
        ctx.comment('Total used volume is: ' + str(total_used_vol) + '\u03BCl.')
        ctx.comment('Volume remaining in first tube is:' +
                    format(int(unused_volume_one)) + '\u03BCl.')
        ctx.comment('Volume remaining in second tube is:' +
                    format(int(unused_volume_two)) + '\u03BCl.')
        ctx.comment('Needed volume is ' +
                    format(int(total_needed_volume)) + '\u03BCl')
        ctx.comment('Used volumes per run are: ' + str(used_vol) + '\u03BCl.')
