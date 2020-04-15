import math
from opentrons.types import Point
from opentrons import protocol_api
import time
import numpy as np
from timeit import default_timer as timer

# metadata
metadata = {
    'protocolName': 'S2 Station B Version 3',
    'author': 'Aitor Gastaminza & José Luis Villanueva (jlvillanueva@clinic.cat)',
    'source': 'Hospital Clínic Barcelona',
    'apiLevel': '2.0',
    'description': 'Protocol for RNA extraction using custom lab procotol (no kits)'
}


mag_height = 12 # Height needed for NUNC deepwell in magnetic deck
NUM_SAMPLES = 16
temperature = 25
D_deepwell = 6.9 # Deepwell diameter
multi_well_rack_area = 7*71 #Cross section of the 12 well reservoir
deepwell_cross_section_area = math.pi*D_deepwell**2/4 # deepwell cilinder cross secion area

num_cols = math.ceil(NUM_SAMPLES/8) # Columns we are working on

def run(ctx: protocol_api.ProtocolContext):
    ctx.comment('Actual used columns: '+str(num_cols))

    #Define Reagents as objects with their properties
    class Reagent:
        def __init__(self, name, flow_rate_aspirate, flow_rate_dispense, rinse,
        reagent_reservoir, num_wells, h_cono, v_fondo, tip_recycling = 'none'):
            self.name = name
            self.flow_rate_aspirate = flow_rate_aspirate
            self.flow_rate_dispense = flow_rate_dispense
            self.rinse = bool(rinse)
            self.reagent_reservoir = reagent_reservoir
            self.num_wells = num_wells
            self.col = 0
            self.vol_well = 0
            self.h_cono = h_cono
            self.v_cono = v_fondo
            self.tip_recycling = tip_recycling
        def vol_well_original(self):
            return self.reagent_reservoir/self.num_wells

    #Reagents and their characteristics
    Ethanol = Reagent(name = 'Ethanol',
                    flow_rate_aspirate = 0.5,
                    flow_rate_dispense = 1,
                    rinse = True,
                    reagent_reservoir = 12000,
                    num_wells = 4, #num_Wells max is 4
                    h_cono = 1.95,
                    v_fondo = 1.95*7*71/2, #Prismatic
                    tip_recycling = 'A1')

    Beads = Reagent(name = 'Magnetic beads',
                    flow_rate_aspirate = 0.5,
                    flow_rate_dispense = 1,
                    rinse = True,
                    reagent_reservoir = 12000,
                    num_wells = 4,
                    h_cono = 1.95,
                    v_fondo = 1.95*7*71/2, #Prismatic
                    tip_recycling = 'A2')

    Isopropanol = Reagent(name = 'Isopropanol',
                    flow_rate_aspirate = 0.5,
                    flow_rate_dispense = 1,
                    rinse = True,
                    reagent_reservoir = 5000,
                    num_wells = 2, #num_Wells max is 2
                    h_cono = 1.95,
                    v_fondo = 1.95*7*71/2, #Prismatic
                    tip_recycling = 'A3')

    Water = Reagent(name = 'Water',
                    flow_rate_aspirate = 1,
                    flow_rate_dispense = 1,
                    rinse = False,
                    reagent_reservoir = 6000,
                    num_wells = 1, #num_Wells max is 1
                    h_cono = 1.95,
                    v_fondo = 1.95*7*71/2) #Prismatic

    Elution = Reagent(name = 'Elution',
                    flow_rate_aspirate = 0.25,
                    flow_rate_dispense = 1,
                    rinse = False,
                    reagent_reservoir = 800,
                    num_wells = num_cols, #num_cols comes from available columns
                    h_cono = 4,
                    v_fondo = 4*math.pi*4**3/3) #Sphere
    ###################
    #Custom functions
    def custom_mix(pipet, reagent, location, vol, rounds, blow_out):
        '''
        Function for mix in the same location a certain number of rounds. Blow out optional
        '''
        for _ in range(rounds):
            pipet.aspirate(vol, location, rate = reagent.flow_rate_aspirate)
            pipet.dispense(vol, location, rate = reagent.flow_rate_dispense)
        if blow_out == True:
            pipet.blow_out(location.top(z = -2)) # Blow out

    def calc_height(reagent, cross_section_area, aspirate_volume):
        if reagent.vol_well < aspirate_volume:
            reagent.vol_well = reagent.vol_well_original - aspirate_volume
            height = (reagent.vol_well - reagent.v_cono)/cross_section_area - reagent.h_cono
            reagent.col = reagent.col + 1 # column selector position; intialize to required number
            if height < 0:
                height = 0.1
        else:
            height=(reagent.vol_well - reagent.v_cono)/cross_section_area - reagent.h_cono
            reagent.col = 0 + reagent.col
            reagent.vol_well = reagent.vol_well - aspirate_volume
            if height < 0:
                height = 0.1
        return height

    def move_vol_multi(pipet, reagent, source, dest, vol, air_gap_vol, x_offset,
    pickup_height, rinse):
        # Rinse before aspirating
        if rinse == True:
            [custom_mix(pipet, reagent, source, dest, vol) for _ in range(2)]
        # SOURCE
        s = source.bottom(pickup_height).move(Point(x = x_offset))
        pipet.move_to(s) # go to source
        pipet.aspirate(vol, s) # aspirate liquid
        if air_gap_vol !=0: #If there is air_gap_vol, switch pipette to slow speed
            pipet.move_to(source.top(z = -2), speed = 20)
            pipet.aspirate(air_gap_vol, source.top(z = -2), rate = reagent.flow_rate_aspirate) #air gap
        # GO TO DESTINATION
        pipet.move_to(dest.top())
        pipet.dispense(vol + air_gap_vol + 20, dest.top(z = -1), rate = reagent.flow_rate_dispense) #dispense all
        pipet.blow_out(dest.top(z = -1)) # Blow out
        if air_gap_vol != 0:
            pipet.move_to(dest.top(z = -2), speed = 20)
            pipet.aspirate(air_gap_vol,dest.top(z = -2),rate = reagent.flow_rate_aspirate) #air gap

    ##########
    # pick up tip and if there is none left, prompt user for a new rack
    def pick_up(pip):
        nonlocal tip_track
        if tip_track['counts'][pip] == tip_track['maxes'][pip]:
            ctx.pause('Replace ' + str(pip.max_volume) + 'µl tipracks before \
            resuming.')
            pip.reset_tipracks()
            tip_track['counts'][pip] = 0
        tip_track['counts'][pip] += 1
        pip.pick_up_tip()
    ##########
    def find_side(col):
        if col%2==0:
            side=-1 # left
        else:
            side=1
        return side

####################################
    # load labware and modules
    ######## 12 well rack
    reagent_res = ctx.load_labware('nest_12_reservoir_15ml', '2','reagent deepwell plate 1')

############################################
    ########## tempdeck
    tempdeck = ctx.load_module('tempdeck', '3')
    # tempdeck.set_temperature(temperature)

##################################
    ####### Elution plate - final plate, goes to C
    elution_plate = tempdeck.load_labware(
        'transparent_96_wellplate_250ul',
        'cooled elution plate')

############################################
    ######## Elution plate - comes from A
    magdeck = ctx.load_module('magdeck', '6')
    deepwell_plate = magdeck.load_labware('nunc_96_wellplate_2000ul', '96-deepwell sample plate')
    magdeck.disengage()

####################################
    ######## Waste reservoir
    waste_reservoir = ctx.load_labware('nalgene_1_reservoir_300000ul', '9', 'waste reservoir')
    waste=waste_reservoir.wells()[0] # referenced as reservoir

####################################
    ######### Load tip_racks
    tips300 = [ctx.load_labware('opentrons_96_tiprack_300ul', slot, '200µl filter tiprack')
        for slot in ['5', '8', '11','1','4','7']]
    tips1000 = [ctx.load_labware('opentrons_96_filtertiprack_1000ul', slot, '1000µl filter tiprack')
        for slot in ['10']]

###############################################################################
    #Declare which reagents are in each reservoir as well as deepwell and elution plate
    Beads.reagent_reservoir = reagent_res.rows()[0][:Beads.num_wells] # 1 row, 4 columns (first ones)
    Isopropanol.reagent_reservoir = reagent_res.rows()[0][4:(4 + Isopropanol.num_wells)] # 1 row, 2 columns (from 5 to 6)
    Ethanol.reagent_reservoir = reagent_res.rows()[0][6:Ethanol.num_wells] # 1 row, 2 columns (from 7 to 10)
    Water.reagent_reservoir = reagent_res.rows()[0][-1] # 1 row, 1 column (last one) full of water
    work_destinations = deepwell_plate.rows()[0][:Elution.num_wells]
    final_destinations = elution_plate.rows()[0][:Elution.num_wells]

    # pipettes. P1000 currently deactivated
    m300 = ctx.load_instrument('p300_multi_gen2', 'right', tip_racks=tips300) # Load multi pipette
    #p1000 = ctx.load_instrument('p1000_single_gen2', 'left', tip_racks=tips1000) # load P1000 pipette

    #### used tip counter and set maximum tips available
    tip_track = {
        'counts': {m300: 0},
        #, p1000: 0},
        'maxes': {m300: len(tips300)*12}#, p1000: len(tips1000)*96}
    }

###############################################################################
### PREMIX BEADS
    if not m300.hw_pipette['has_tip']:
        pick_up(m300)
        ctx.comment(' ')
        ctx.comment('Tip picked up')
    ctx.comment(' ')
    ctx.comment('Mixing '+Beads.name)
    ctx.comment(' ')
    #Mixing
    custom_mix(m300, Beads, Beads.reagent_reservoir[Beads.col], vol = 180, rounds = 20, blow_out = True)
    ctx.comment('Finished premixing!')
    ctx.comment('Now, reagents will be transferred to deepwell plate.')
    ctx.comment(' ')

#Transfer parameters
    beads_transfer_vol=[155, 155] #Two rounds of 155
    x_offset = 0
    air_gap_vol = 10
    for i in range(num_cols):
        x_offset = find_side(i) * x_offset
        for transfer_vol in beads_transfer_vol:
            #Calculate pickup_height based on remaining volume and shape of container
            [pickup_height, change_col] = calc_height(Beads, multi_well_rack_area, transfer_vol)
            if change_col == True: #If we switch column because there is not enough volume left in current reservoir column we mix new column
                ctx.comment('Mixing new reservoir column: '+str(Beads.col))
                custom_mix(m300, Beads, Beads.reagent_reservoir[Beads.col], vol = 180, rounds = 20, blow_out = True)
            ctx.comment('Aspirate from reservoir column: '+str(Beads.col))
            ctx.comment('Pickup height is '+str(pickup_height))
            ctx.pause()

            move_vol_multi(m300, reagent = Beads, source = Beads.reagent_reservoir[Beads.col],
            dest = work_destinations[i], vol = transfer_vol, air_gap_vol = air_gap_vol, x_offset = x_offset,
            pickup_height = pickup_height, rinse = True)

    
