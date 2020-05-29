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
    'protocolName': 'Kingfisher Pathogen Station B2 v2',
    'author': 'Eva Gonzalez, José Luis Villanueva (jlvillanueva@clinic.cat)',
    'source': 'Hospital Clínic Barcelona',
    'apiLevel': '2.0',
    'description': 'Protocol for RNA extraction preparation for ThermoFisher Pathogen kit (ref 4462359) \
    setup - sample + beads + buffer preparation'
}

'''
'technician': '$technician',
'date': '$date'
'''

#Defined variables
##################
NUM_SAMPLES = 16
air_gap_vol = 15
MS_vol = 5
air_gap_vol_MS = 2
height_MS = -35
temperature = 25

x_offset = [0, 0]

L_deepwell = 8  # Deepwell side length (KingFisher deepwell)
total_MS_volume = NUM_SAMPLES * 5 * 1.1  # Total volume of MS

# Screwcap variables
diameter_screwcap = 8.25  # Diameter of the screwcap
volume_cone = 50  # Volume in ul that fit in the screwcap cone

# Calculated variables
area_section_screwcap = (np.pi * diameter_screwcap**2) / 4
h_cone = (volume_cone * 3 / area_section_screwcap)
screwcap_cross_section_area = math.pi * \
    diameter_screwcap**2 / 4  # screwcap cross secion area
multi_well_rack_area = 8.2 * 71.2  # Cross section of the 12 well reservoir
deepwell_cross_section_area = L_deepwell**2  # deepwell cross secion area
num_cols = math.ceil(NUM_SAMPLES / 8)  # Columns we are working on


# 'kf_96_wellplate_2400ul'
def run(ctx: protocol_api.ProtocolContext):
    from opentrons.drivers.rpi_drivers import gpio
    ctx.comment('Actual used columns: ' + str(num_cols))

    # Define the STEPS of the protocol
    STEP = 0
    STEPS = {  # Dictionary with STEP activation, description, and times
        1: {'Execute': True, 'description': 'Add MS2'},
        2: {'Execute': True, 'description': 'Transfer beads'}
    }
    for s in STEPS:  # Create an empty wait_time
        if 'wait_time' not in STEPS[s]:
            STEPS[s]['wait_time'] = 0

    folder_path = '/var/lib/jupyter/notebooks'
    if not ctx.is_simulating():
        if not os.path.isdir(folder_path):
            os.mkdir(folder_path)
        file_path = folder_path + '/Station_KB_sample_prep_viral_path2_time_log.txt'

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
    Sample = Reagent(name='Sample',
                     flow_rate_aspirate=1,
                     flow_rate_dispense=1,
                     rinse=True,
                     delay=0,
                     reagent_reservoir_volume=460 * 96,
                     num_wells=96,
                     h_cono=1.95,
                     v_fondo=35)

    Beads = Reagent(name='Magnetic beads and binding solution',
                    flow_rate_aspirate=0.75,
                    flow_rate_dispense=0.75,
                    rinse=True,
                    num_wells=math.ceil(NUM_SAMPLES / 32),
                    delay=2,
                    reagent_reservoir_volume=550 * 8 * num_cols * 1.1,
                    h_cono=1.95,
                    v_fondo=695)  # Prismatic

    MS = Reagent(name='MS2',
                 flow_rate_aspirate=1,
                 flow_rate_dispense=1,
                 rinse=False,
                 reagent_reservoir_volume=total_MS_volume,
                 num_wells=8,
                 delay=0,
                 h_cono=h_cone,
                 v_fondo=volume_cone  # V cono
                 )  # Prismatic)

    Sample.vol_well = Sample.reagent_reservoir_volume
    Beads.vol_well = Beads.vol_well_original
    MS.vol_well = MS.reagent_reservoir_volume

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


    def divide_destinations(l, n):
        # Divide the list of destinations in size n lists.
        for i in range(0, len(l), n):
            yield l[i:i + n]

    ####################################
    # load labware and modules
    # 12 well rack
    reagent_res = ctx.load_labware(
        'perkinelmer_12_reservoir_21000ul', '2', 'Reagent deepwell plate')

    ##################################
    # Sample prep plate - final plate, goes to Kingfisher
    sample_plate = ctx.load_labware(
        'kf_96_wellplate_2400ul', '1',
        'KF 96 Well 2400ul elution plate')

    ############################################
    # tempdeck
    tempdeck = ctx.load_module('tempdeck', '4')
    tempdeck.set_temperature(temperature)

    ##################################
    # MS plate -  plate with a column containing the internal control MS
    ms_plate = tempdeck.load_labware(
        'vwr_96_wellplate_200ul_alum_opentrons',
        'pcr plate with MS control')

    ####################################
    # load labware and modules
    # 24 well rack aluminium opentrons
    #tuberack = ctx.load_labware(
    #    'opentrons_24_aluminumblock_generic_2ml_screwcap', '3',
    #    'Bloque Aluminio opentrons 24 Screwcaps')

    ##################################
    # Load Tipracks
    tips20 = [
        ctx.load_labware('opentrons_96_filtertiprack_20ul', slot)
        for slot in ['6']
    ]

    tips200 = [
        ctx.load_labware('opentrons_96_filtertiprack_200ul', slot)
        for slot in ['3']
    ]

    # pipettes. P1000 currently deactivated
    m300 = ctx.load_instrument(
        'p300_multi_gen2', 'right', tip_racks=tips200)  # Load multi pipette
    m20 = ctx.load_instrument(
        'p20_multi_gen2', 'left', tip_racks=tips20)

    #p20 = ctx.load_instrument(
    #    'p20_single_gen2', 'left', tip_racks=tips20)  # load P1000 pipette

    tip_track = {
        'counts': {m300: 0, m20: 0},
        'maxes': {m300: len(tips200) * 96, m20: len(tips20) * 96}
    }

    # Divide destination wells in small groups for P300 pipette
    # Declare which reagents are in each reservoir as well as deepwell and elution plate
    #destinations = list(divide_destinations(sample_plate.wells()[:NUM_SAMPLES], size_transfer))
    Beads.reagent_reservoir = reagent_res.rows()[0][:Beads.num_wells]  # 1 row, 4 columns (first ones)
    work_destinations = sample_plate.wells()[:NUM_SAMPLES]
    work_destinations_cols = sample_plate.rows()[0][:num_cols]
    ms_origins = ms_plate.rows()[0][0]  # 1 row, 1 columns

    ############################################################################
    # STEP 1: Transfer MS
    ############################################################################

    STEP += 1
    if STEPS[STEP]['Execute'] == True:
        start = datetime.now()
        ctx.comment('ms_wells')
        #Loop over defined wells
        for d in work_destinations_cols:
            m20.pick_up_tip()
            #Source samples
            move_vol_multichannel(m20, reagent = MS, source = ms_origins, dest = d,
            vol = MS_vol, air_gap_vol = air_gap_vol_MS, x_offset = x_offset,
                   pickup_height = 0.2, disp_height = -35, rinse = False,
                   blow_out=True, touch_tip=True)
            m20.drop_tip()
            tip_track['counts'][m20]+=8

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
    # STEP 2: TRANSFER BEADS
    ############################################################################
    STEP += 1
    if STEPS[STEP]['Execute'] == True:
        # Transfer parameters
        start = datetime.now()
        ctx.comment('Step ' + str(STEP) + ': ' + STEPS[STEP]['description'])
        ctx.comment('###############################################')
        beads_transfer_vol = [150, 150, 150, 100]  # 4 rounds of different volumes
        rinse = True
        for i in range(num_cols):
            if not m300.hw_pipette['has_tip']:
                m300.pick_up_tip()
            for j, transfer_vol in enumerate(beads_transfer_vol):
                # Calculate pickup_height based on remaining volume and shape of container
                [pickup_height, change_col] = calc_height(
                    Beads, multi_well_rack_area, transfer_vol * 8, min_height = 1)
                if change_col == True:  # If we switch column because there is not enough volume left in current reservoir column we mix new column
                    ctx.comment(
                        'Mixing new reservoir column: ' + str(Beads.col))
                    custom_mix(m300, Beads, Beads.reagent_reservoir[Beads.col],
                               vol=170, rounds=10, blow_out=False, mix_height=0,
                               x_offset = x_offset)
                ctx.comment(
                    'Aspirate from reservoir column: ' + str(Beads.col))
                ctx.comment('Pickup height is ' + str(pickup_height))
                if j != 0:
                    rinse = False
                move_vol_multichannel(m300, reagent=Beads, source=Beads.reagent_reservoir[Beads.col],
                                      dest=work_destinations_cols[i], vol=transfer_vol,
                                      air_gap_vol=air_gap_vol, x_offset=x_offset,
                                      pickup_height=pickup_height, disp_height = -2,
                                      rinse=rinse, blow_out = False, touch_tip=False)

        m300.drop_tip(home_after=False)
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
    gpio.set_rail_lights(False)
    time.sleep(2)
    #os.system('mpg123 -f -8000 /var/lib/jupyter/notebooks/toreador.mp3 &')
    for i in range(3):
        gpio.set_rail_lights(False)
        gpio.set_button_light(1, 0, 0)
        time.sleep(0.3)
        gpio.set_rail_lights(True)
        gpio.set_button_light(0, 0, 1)
        time.sleep(0.3)
    gpio.set_button_light(0, 1, 0)
    ctx.comment('Finished! \nMove plate to KingFisher')
