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
    'protocolName': 'S2 Station A Version 2',
    'author': 'Aitor Gastaminza & José Luis Villanueva (jlvillanueva@clinic.cat)',
    'source': 'Hospital Clínic Barcelona',
    'apiLevel': '2.0',
    'description': 'Protocol for sample setup (A)',
    'technician': $tecnico,
    'data': $data
}

#Defined variables
##################
NUM_SAMPLES = $num_samples
air_gap_vol_ci = 2
air_gap_vol_sample = 5

volume_control = 10
volume_sample = 300
height_protk = 10
height_control = 20
temperature = 25

#Screwcap variables
diameter_sample = 8.25  # Diameter of the screwcap
diameter_screwcap = 8.25  # Diameter of the screwcap
volume_cone = 50  # Volume in ul that fit in the screwcap cone

# Calculated variables
area_section_screwcap = (math.pi * diameter_screwcap**2) / 4
area_section_sample = (math.pi * diameter_sample**2) / 4
h_cone = (volume_cone * 3 / area_section_screwcap)
screwcap_cross_section_area = math.pi * diameter_screwcap**2 / 4  # screwcap cross secion area, cross_section_area = 63.61

def run(ctx: protocol_api.ProtocolContext):
    STEP = 0
    STEPS = {  # Dictionary with STEP activation, description, and times
        1: {'Execute': True, 'description': 'Add samples (300ul)'},
        2: {'Execute': True, 'description': 'Add internal control (10ul)'}
    }
    for s in STEPS:  # Create an empty wait_time
        if 'wait_time' not in STEPS[s]:
            STEPS[s]['wait_time'] = 0

    #Fo     lder and file_path for log time
    if not ctx.is_simulating():
        folder_path = '/dvar/lib/jupyter/notebooks'
        if not os.path.isdir(folder_path):
            os.mkdir(folder_path)
        file_path = folder_path + '/StationA_time_log.txt'

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
    Control_I = Reagent(name = 'Internal Control',
                     flow_rate_aspirate = 1,
                     flow_rate_dispense = 1,
                     rinse = True,
                     reagent_reservoir_volume = 200,
                     num_wells = 1,  # num_Wells max is 4
                     h_cono = (volume_cone * 3 / area_section_screwcap),
                     v_fondo = 50
                     )

    Samples = Reagent(name = 'Samples',
                      flow_rate_aspirate = 1,
                      flow_rate_dispense = 1,
                      rinse = False,
                      reagent_reservoir_volume = 700*24,
                      num_wells = 24,  # num_cols comes from available columns
                      h_cono = 4,
                      v_fondo = 4 * area_section_sample / 3
                      )  # Sphere

    Control_I.vol_well = Control_I.vol_well_original
    Samples.vol_well = 700

    ##################
    # Custom functions
    def generate_source_table(source):
        '''
        Concatenate the wells frome the different origin racks
        '''
        for rack_number in range(len(source)):
            if rack_number == 0:
                s = source[rack_number].wells()
            else:
                s = s + source[rack_number].wells()
        return s

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
            height = (reagent.vol_well - aspirate_volume - reagent.v_cono) / cross_section_area
                    #- reagent.h_cono
            reagent.vol_well = reagent.vol_well - aspirate_volume
            ctx.comment('Remaining volume:' + str(reagent.vol_well))
            if height < 0.5:
                height = 0.5
            col_change = True
        else:
            height = (reagent.vol_well - aspirate_volume - reagent.v_cono) / cross_section_area #- reagent.h_cono
            reagent.vol_well = reagent.vol_well - aspirate_volume
            ctx.comment('Calculated height is ' + str(height))
            if height < 0.5:
                height = 0.5
            ctx.comment('Used height is ' + str(height))
            col_change = False
        return height, col_change

    def move_vol_multi(pipet, reagent, source, dest, vol, air_gap_vol, x_offset,
                       pickup_height, drop_height, rinse):
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
        if drop_height!=0:
            drop = dest.bottom(z = drop_height)
        else:
            drop = dest.top(z = -2)
        pipet.dispense(vol + air_gap_vol, drop,
                       rate = reagent.flow_rate_dispense)  # dispense all
        pipet.blow_out(dest.top(z = -2))
        #if air_gap_vol != 0: #Air gap for multidispense
        #    pipet.aspirate(air_gap_vol, dest.top(z = -2),
        #                   rate = reagent.flow_rate_aspirate)  # air gap

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
        'abgenestorage_96_wellplate_1200ul', '5',
        'ABGENE STORAGE 96 Well Plate 1200 µL')


    ############################################
    # tempdeck
    #tempdeck = ctx.load_module('tempdeck', '1')
    #tempdeck.set_temperature(temperature)

    ##################################
    # Cooled reagents in tempdeck
    #reagents = tempdeck.load_labware(
        #'bloquealuminio_24_screwcap_wellplate_1500ul',
        #'cooled reagent tubes')
    reagents = ctx.load_labware(
        'bloquealuminio_24_screwcap_wellplate_1500ul','7',
        'cooled reagent tubes')

    ####################################
    # Load tip_racks
    tips20 = [ctx.load_labware('opentrons_96_filtertiprack_20ul', slot, '20µl filter tiprack')
               for slot in ['11']]
    tips1000 = [ctx.load_labware('opentrons_96_filtertiprack_1000ul', slot, '1000µl filter tiprack')
        for slot in ['10']]


    ################################################################################
    # Declare which reagents are in each reservoir as well as deepwell and elution plate
    Control_I.reagent_reservoir = reagents.wells()[0]

    # setup samples and destinations
    sample_sources_full = generate_source_table(source_racks)
    sample_sources = sample_sources_full[:NUM_SAMPLES]
    destinations = dest_plate.wells()[:NUM_SAMPLES]

    p20 = ctx.load_instrument(
        'p20_single_gen2', mount='right', tip_racks=tips20)
    p1000 = ctx.load_instrument('p1000_single_gen2', 'left', tip_racks=tips1000) # load P1000 pipette

    # used tip counter and set maximum tips available
    tip_track = {
        'counts': {p20: 0, p1000: 0},
        'maxes': {p20: len(tips20)*96, p1000: len(tips1000)*96}
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
            #Mix the sample before dispensing
            custom_mix(p1000, reagent = Samples, location = s, vol = volume_sample, rounds = 2, blow_out = True, mix_height = 15)
            move_vol_multi(p1000, reagent = Samples, source = s, dest = d,
            vol = volume_sample, air_gap_vol = air_gap_vol_sample, x_offset = 0,
                   pickup_height = 1, drop_height = 0, rinse = False)
            custom_mix(p1000, reagent = Samples, location = d, vol = volume_sample, rounds = 2, blow_out = True, mix_height = 15)
            p1000.touch_tip(speed=20, v_offset=-5)
            #Drop tip and update counter
            p1000.drop_tip()
            tip_track['counts'][p1000]+=1

        #Time statistics
        end = datetime.now()
        time_taken = (end - start)
        ctx.comment('Step ' + str(STEP) + ': ' + STEPS[STEP]['description'] +
        ' took ' + str(time_taken))
        STEPS[STEP]['Time:'] = str(time_taken)

    ############################################################################
    # STEP 2: Add Internal Control
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
            [pickup_height, change_col] = calc_height(Control_I, screwcap_cross_section_area, volume_control)
            move_vol_multi(p20, reagent = Control_I, source = Control_I.reagent_reservoir,
            dest = d, vol = volume_control, air_gap_vol = air_gap_vol_ci, x_offset = 0,
                   pickup_height = pickup_height, drop_height = height_control, rinse = False)
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

    ############################################################################
    # Light flash end of program
    from opentrons.drivers.rpi_drivers import gpio
    if not ctx.is_simulating():
        os.system('mpg123 -f -14000 /var/lib/jupyter/notebooks/lionking.mp3')
    for i in range(3):
        gpio.set_rail_lights(False)
        gpio.set_button_light(1, 0, 0)
        time.sleep(0.3)
        gpio.set_rail_lights(True)
        gpio.set_button_light(0, 0, 1)
        time.sleep(0.3)
    gpio.set_button_light(0, 1, 0)
    ctx.comment(
        'Finished! \nMove deepwell plate (slot 5) to Station B for extraction protocol')
    ctx.comment('Used p1000 tips in total: ' + str(tip_track['counts'][p1000]))
    ctx.comment('Used p1000 racks in total: ' + str(tip_track['counts'][p1000] / 96))
    ctx.comment('Used p20 tips in total: ' + str(tip_track['counts'][p20]))
    ctx.comment('Used p20 racks in total: ' + str(tip_track['counts'][p20] / 96))
