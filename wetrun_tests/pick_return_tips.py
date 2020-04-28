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
    'protocolName': 'Test pick up tips, return tips',
    'author': 'Aitor Gastaminza & José Luis Villanueva (jlvillanueva@clinic.cat)',
    'source': 'Hospital Clínic Barcelona',
    'apiLevel': '2.0',
    'description': 'Protocol for RNA extraction using custom lab procotol (no kits)'
}

#Defined variables
##################
NUM_SAMPLES = 96
air_gap_vol = 15

# mag_height = 11 # Height needed for NUNC deepwell in magnetic deck
mag_height = 17  # Height needed for ABGENE deepwell in magnetic deck
temperature = 4
D_deepwell = 6.9  # Deepwell diameter (ABGENE deepwell)
# D_deepwell = 8.35 # Deepwell diameter (NUNC deepwell)
multi_well_rack_area = 8 * 71  # Cross section of the 12 well reservoir
x_offset_rs = 1 #Offset of the pickup when magnet is ON

#Calculated variables
deepwell_cross_section_area = math.pi * D_deepwell**2 / 4  # deepwell cilinder cross secion area
num_cols = math.ceil(NUM_SAMPLES / 8)  # Columns we are working on

def run(ctx: protocol_api.ProtocolContext):
    ctx.comment('Actual used columns: ' + str(num_cols))
    STEP = 0
    STEPS = {  # Dictionary with STEP activation, description, and times
        1: {'Execute': True, 'description': 'Test return tips'}
    }
    for s in STEPS:  # Create an empty wait_time
        if 'wait_time' not in STEPS[s]:
            STEPS[s]['wait_time'] = 0
    folder_path = '/data/log_times/'
    if not ctx.is_simulating():
        if not os.path.isdir(folder_path):
            os.mkdir(folder_path)
        file_path = folder_path + '/time_log.txt'

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
    Ethanol = Reagent(name='Ethanol',
                      flow_rate_aspirate=0.5,
                      flow_rate_dispense=1,
                      rinse=True,
                      reagent_reservoir_volume=38400,
                      num_wells=4,  # num_Wells max is 4
                      h_cono=1.95,
                      v_fondo=1.95 * multi_well_rack_area / 2,  # Prismatic
                      tip_recycling='A1')

    Beads = Reagent(name='Magnetic beads',
                    flow_rate_aspirate=1,
                    flow_rate_dispense=1.5,
                    rinse=True,
                    reagent_reservoir_volume=29760,
                    num_wells=4,
                    h_cono=1.95,
                    v_fondo=1.95 * multi_well_rack_area / 2,  # Prismatic
                    tip_recycling='A2')

    Isopropanol = Reagent(name='Isopropanol',
                          flow_rate_aspirate=1,
                          flow_rate_dispense=1,
                          rinse=True,
                          reagent_reservoir_volume=14400,
                          num_wells=2,  # num_Wells max is 2
                          h_cono=1.95,
                          v_fondo=1.95 * multi_well_rack_area / 2,  # Prismatic
                          tip_recycling='A3')

    Water = Reagent(name='Water',
                    flow_rate_aspirate=1,
                    flow_rate_dispense=1,
                    rinse=False,
                    reagent_reservoir_volume=4800,
                    num_wells=1,  # num_Wells max is 1
                    h_cono=1.95,
                    v_fondo=1.95 * multi_well_rack_area / 2)  # Prismatic

    Elution = Reagent(name='Elution',
                      flow_rate_aspirate=0.5,
                      flow_rate_dispense=1,
                      rinse=False,
                      reagent_reservoir_volume=800,
                      num_wells=num_cols,  # num_cols comes from available columns
                      h_cono=4,
                      v_fondo=4 * math.pi * 4**3 / 3)  # Sphere

    Ethanol.vol_well = Ethanol.vol_well_original
    Beads.vol_well = Beads.vol_well_original
    Isopropanol.vol_well = Isopropanol.vol_well_original
    Water.vol_well = Water.vol_well_original
    Elution.vol_well = 350

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
        if air_gap_vol != 0:
            pipet.aspirate(air_gap_vol, dest.top(z=-2),
                           rate=reagent.flow_rate_aspirate)  # air gap

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
    # Waste reservoir
    waste_reservoir = ctx.load_labware(
        'nalgene_1_reservoir_300000ul', '9', 'waste reservoir')
    waste = waste_reservoir.wells()[0]  # referenced as reservoir

####################################
    # Load tip_racks
    tips300 = [ctx.load_labware('opentrons_96_tiprack_300ul', slot, '200µl filter tiprack')
               for slot in ['8', '11', '1', '4', '7', '10']]
    tips300r = [ctx.load_labware('opentrons_96_tiprack_300ul', slot, '200µl filter tiprack')
                  for slot in ['5']]
    # tips1000 = [ctx.load_labware('opentrons_96_filtertiprack_1000ul', slot, '1000µl filter tiprack')
    #    for slot in ['10']]
    print(tips300r[0].rows()[0][:12])
    #for i, (a, b) in enumerate(zip(alist, blist)):
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
                m300.pick_up_tip(tips300r[0].rows()[0][i])
            for j, transfer_vol in enumerate(beads_transfer_vol):
                m300.move_to(waste.top())
                m300.aspirate(100)
                m300.move_to(waste.bottom(5))
                m300.dispense(100)
            m300.return_tip(tips300r[0].rows()[0][i])
            # m300.return_tip()
            tip_track['counts'][m300] += 8
        end = datetime.now()
        time_taken = (end - start)
        ctx.comment('Step ' + str(STEP) + ': ' +
                    STEPS[STEP]['description'] + ' took ' + str(time_taken))
        STEPS[STEP]['Time:'] = str(time_taken)

        ctx.comment('Now incubation will start ')

    # Export the time log to a tsv file

    ############################################################################
    # Light flash end of program
    from opentrons.drivers.rpi_drivers import gpio
    if not ctx.is_simulating():
        os.system('mpg123 -f -14000 lionking.mp3')
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
