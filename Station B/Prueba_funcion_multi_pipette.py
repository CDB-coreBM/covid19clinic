import math
from opentrons.types import Point
from opentrons import protocol_api
import time
from opentrons.drivers.rpi_drivers import gpio
# metadata
metadata = {
    'protocolName': 'S2 Station B Version 2',
    'author': 'Nick <protocols@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.0'
}

mag_height=13 # Height needed for NUNC deepwell in magnetic deck
NUM_SAMPLES = 16
temperature = 25
D_deepwell=6.9
multi_well_rack_area=4*80
deepwell_cross_section_area=math.pi*D_deepwell**2/4

def run(ctx: protocol_api.ProtocolContext):

    # load labware and modules

####################################

    ######## 12 well rack
    reagent_res = ctx.load_labware('nest_12_reservoir_15ml', '2',
                                       'reagent deepwell plate 1')

############################################
    ########## tempdeck
    tempdeck = ctx.load_module('tempdeck', '3')
    tempdeck.set_temperature(temperature)

##################################

    ####### Elution plate - final plate, goes to C
    elution_plate = tempdeck.load_labware(
        'transparent_96_wellplate_250ul',
        'cooled elution plate')

############################################

    ######## Elution plate - comes from A
    magdeck = ctx.load_module('magdeck', '6')
    deepwell_plate = magdeck.load_labware(
        'nunc_96_wellplate_2000ul', '96-deepwell sample plate')

####################################

    ######## Waste reservoir
    waste = ctx.load_labware(
        'nalgene_1_reservoir_300000ul', '9', 'waste reservoir').wells()[0].top()

####################################


    ######### Load tip_racks
    tips300 = [
        ctx.load_labware(
            'opentrons_96_tiprack_300ul', slot, '200µl filter tiprack')
        for slot in [ '5', '8', '11']
    ]
                                    ####
    tips1000 = [
        ctx.load_labware(
            'opentrons_96_filtertiprack_1000ul', slot, '1000µl filter tiprack')
        for slot in ['1','4','7', '10']
    ]
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

    old_bool=0 # column selector position; intialize to required number

    def calc_height(vol_ini, cross_section_area,sample_vol,n_tips,extra_vol,vol_next,old_bool):
        if vol_ini<(sample_vol*n_tips+extra_vol):
            vol_f=(vol_next-sample_vol*n_tips+extra_vol)
            height=vol_f/cross_section_area
            bool=1+old_bool
        else:
            height=(vol_ini-sample_vol*n_tips+extra_vol)/cross_section_area
            bool=0+old_bool
            vol_f=vol_ini-sample_vol*n_tips+extra_vol
        return bool,height,vol_f

    def move_vol_multi(pipet,flow_rate_aspirate,flow_rate_dispense,
    air_gap_vol, vol, x_offset, z_offset, source,column,dest,
    aspiration_height,blow_height,drop,home,protocol):
#        if not pipet.hw_pipette['has_tip']:
#            pick_up(pipet)
        pipet.default_speed=400
        s=source.bottom(z_offset).move(Point(x=x_offset*find_side(column)))
        pipet.move_to(s)
        pipet.flow_rate.aspirate=flow_rate_aspirate
        pipet.aspirate(vol,s)
        if air_gap_vol !=0:
            pipet.default_speed=20
            pipet.move_to(source.top(z=aspiration_height))
            pipet.flow_rate.aspirate=50
            pipet.aspirate(air_gap_vol,source.top(z=aspiration_height))
        pipet.default_speed=400
        pipet.flow_rate.dispense=flow_rate_dispense
        pipet.dispense(vol+air_gap_vol, dest)
        pipet.move_to(dest.top(z=blow_height))
        pipet.dispense(5) # Blow out
        if air_gap_vol != 0:
            pipet.flow_rate.aspirate=50
            pipet.move_to(dest.top(z=aspiration_height))
            pipet.aspirate(air_gap_vol,dest.top(z=aspiration_height))
        #pipette.touch_tip(speed=20,v_offset=-5)
        pipet.default_speed=400
        pipet.flow_rate.aspirate =500
        #pipette.transfer(SAMPLE_VOLUME, s.bottom(1), d.bottom(1), new_tip='never',air_gap=5,touch_tip=True)
        if (drop ==True):
            if home == False:
                pipet.drop_tip(home_after=False)
                pick_up(pipet)
            else:
                pipet.drop_tip()
                pick_up(pipet)

###############################################################################
    # reagents and samples
    num_cols = math.ceil(NUM_SAMPLES/8) # Columnas de trabajo
    work_destinations=deepwell_plate.rows()[0][:num_cols]
    final_destinations=elution_plate.rows()[0][:num_cols]

    beads = reagent_res.rows()[0][:3] # 1 row, 2 columns (first ones)
    etoh = reagent_res.rows()[0][3:6] # 1 row, 2 columns (from 3 to 5); there's a space
    water = reagent_res.rows()[0][-1] # 1 row, 1 column (last ones) full of water

    # pipettes
    m300 = ctx.load_instrument('p300_multi_gen2', 'right', tip_racks=tips300) # Load multi pipette
    p1000 = ctx.load_instrument('p1000_single_gen2', 'left', tip_racks=tips1000) # load P1000 pipette

    ##### FLOW RATES #######
    m300.flow_rate.aspirate = 150
    m300.flow_rate.dispense = 300
    m300.flow_rate.blow_out = 300
    p1000.flow_rate.aspirate = 100
    p1000.flow_rate.dispense = 1000

    #### used tip counter and set maximum tips available
    tip_track = {
        'counts': {m300: 0, p1000: 0},
        'maxes': {m300: len(tips300)*12, p1000: len(tips1000)*96}
    }

###############################################################################
        # premix, transfer, and mix magnetic beads with sample
    #PREMIX parameters
    flow_rate_aspirate=150
    flow_rate_dispense=300
    mix_vol=180
    mix_number=2
    old_bool=0
    vol_ini=15000 # volume of magnetic beads
    air_gap_vol=0
    x_offset=0
    z_offset=4
    column=0
    aspiration_height=0
    blow_height=20
    drop=False
    home=False
    extra_vol=0

### PREMIX
    if not m300.hw_pipette['has_tip']:
        pick_up(m300)
    for i in range(mix_number):
        move_vol_multi(m300,flow_rate_aspirate,flow_rate_dispense,
        air_gap_vol, mix_vol, x_offset, z_offset, beads[0],column,beads[0],
        aspiration_height,blow_height,False,False,ctx)




    ctx.comment('Finished!')
    ctx.comment('Transfer stuff to deewell plate.')
#Transfer parameters
    beads_transfer_vol=[150,150]
    vol_ini=15000 # volume of magnetic beads
    air_gap_vol_t=10
    aspiration_height_t=-5
    drop_t=True
    n_tips=8
    vol_next=vol_ini

    for i in range(num_cols):
        for transfer_vol in beads_transfer_vol:
            [change_col,pickup_height,vol_final]=calc_height(vol_ini, multi_well_rack_area,
            transfer_vol,n_tips,extra_vol,vol_next,old_bool)

            if change_col!=old_bool: #if beads column changes, remix
                for i in range(mix_number):
                    move_vol_multi(m300,flow_rate_aspirate,flow_rate_dispense,
                    air_gap_vol, mix_vol, x_offset, z_offset, beads[change_col],0,beads[change_col],
                    aspiration_height,blow_height,False,False,ctx)

            move_vol_multi(m300,flow_rate_aspirate,flow_rate_dispense,
            air_gap_vol_t, transfer_vol, x_offset, pickup_height,
            beads[change_col],i,work_destinations[i],
            aspiration_height_t,blow_height,False,False,ctx)

            vol_ini=vol_final
            vol_next=vol_ini
            old_bool=change_col
        m300.drop_tip(home_after=False)
        pick_up(m300)
###############################################################################
    for i in range(3):
        gpio.set_rail_lights(False)
        gpio.set_button_light(1,0,0)
        time.sleep(0.3)
        gpio.set_rail_lights(True)
        gpio.set_button_light(0,0,1)
        time.sleep(0.3)
    gpio.set_button_light(0,1,0)
    ctx.comment('Finished! \nMove deepwell plate (slot 5) to Station B for RNA \
extraction.')
