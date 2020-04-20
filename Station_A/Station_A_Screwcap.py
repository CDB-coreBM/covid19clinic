from opentrons import protocol_api
import time
import math
#robot.head_speed(5000)

# metadata
metadata = {
    'protocolName': 'S2 Station A Version 1',
    'author': 'Aitor & JL <Hospital Clinic Barcelona>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.0'
}

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

# Distribute control liquid in deepwell
def distribute_custom(pipette, dispense_volume, source, size_transfer, destination, pickup_height, extra_dispensal):
    pipette.aspirate((size_transfer*dispense_volume)+extra_dispensal, source.bottom(pickup_height))
    pipette.touch_tip(speed = 20, v_offset = -3, radius = 1.05)
    pipette.dispense(dispense_volume, destination.bottom(2))
    pipette.move_to(destination.top(z=5))
    pipette.blow_out()
    pipette.touch_tip(speed=20,radius=1.05)

# Function to fill the 96 well rack in quadrants
def fill_96_rack(dests, src, pipette, bool, SAMPLE_VOLUME, CONTROL_VOLUME,
air_gap_volume):
    for s, d in zip(src, dests):
        pipette.pick_up_tip()
        pipette.aspirate(SAMPLE_VOLUME,s.bottom(1))
        pipette.default_speed=60
        pipette.touch_tip(speed=20,v_offset=-5)
        pipette.default_speed=20
        pipette.move_to(s.top(z=-5))
        pipette.flow_rate.aspirate=50
        pipette.aspirate(air_gap_volume)
        pipette.default_speed=400
        pipette.flow_rate.aspirate =500
        pipette.dispense(SAMPLE_VOLUME+air_gap_volume, d)
        pipette.default_speed=60
        if bool == True:
            pipette.mix(1, SAMPLE_VOLUME+CONTROL_VOLUME+50, d)
            pipette.move_to(d.top(z=-5))
            pipette.blow_out()
        pipette.default_speed=20
        pipette.move_to(d.top(z=-5))
        pipette.dispense(5)
        pipette.flow_rate.aspirate=50
        pipette.aspirate(air_gap_volume)
        #pipette.touch_tip(speed=20,v_offset=-5)
        pipette.default_speed=20
        pipette.move_to(d.top(z=10))
        pipette.default_speed=400
        pipette.flow_rate.aspirate =500
        pipette.drop_tip(home_after=False)

##########################################################################
NUM_SAMPLES = 3
SAMPLE_VOLUME = 300
CONTROL_VOLUME = 10
TRANSFER_SAMPLES_F = True
TRANSFER_CONTROL_F_custom = False
mix_bool = False
volume_epp = 1500
extra_dispensal = 0
size_transfer = 1
air_gap_volume = 15
cross_section_area = 63.61 # Ojo que es cónico en su parte final y haya que modificar esta función
##########################################################################

def run(ctx: protocol_api.ProtocolContext):
    global volume_epp
    from opentrons.drivers.rpi_drivers import gpio
    gpio.set_rail_lights(True) # set lights on
    gpio.set_button_light(1,0,0) # RGB [0:1]
    # load labware
    if NUM_SAMPLES<96:
        rack_num=math.ceil(NUM_SAMPLES/24)
        ctx.comment('Used source racks are '+str(rack_num))
        samples_last_rack=NUM_SAMPLES-rack_num*24

    source_racks = [ctx.load_labware(
            'opentrons_24_tuberack_generic_2ml_screwcap', slot,
            'source tuberack with screwcap' + str(i+1)) for i, slot in enumerate(['4','1','6','3'][:rack_num])
        ]
##########################################################################
    if TRANSFER_CONTROL_F_custom==True:
        tempdeck=ctx.load_module('tempdeck','7')
        tempdeck.set_temperature(4)
        control_src = tempdeck.load_labware(
            'bloquealuminio_24_eppendorf_wellplate_1500ul',
            'Bloque Aluminio 24 Well Plate 1500 µL')
        cntrl_src_well=control_src.wells()[0]
        p20 = ctx.load_instrument('p20_single_gen2', 'right', tip_racks=[tiprack])
##########################################################################
    dest_plate = ctx.load_labware(
        'abgenestorage_96_wellplate_1200ul', '5',
        'ABGENE STORAGE 96 Well Plate 1200 µL')

    # Load tipracks
    ##############
    tiprack = ctx.load_labware(
        'opentrons_96_filtertiprack_20ul', '11', '20µl tiprack')
    tips1000 = ctx.load_labware(
        'opentrons_96_filtertiprack_1000ul', '10', '1000µl tiprack')

    # Load pipettes
    ##############
    p1000 = ctx.load_instrument('p1000_single_gen2', 'left', tip_racks=[tips1000])

    # setup samples and destinations
    sources=generate_source_table(source_racks)
    sources=sources[:NUM_SAMPLES]
    destinations=[well for col in dest_plate.columns() for well in col][:NUM_SAMPLES]

    ##########################################################################
    #### NOW DISTRIBUTE THE CONTROL SRC #############
    # transfer with p20 from control source with the CUSTOM functions
    if TRANSFER_CONTROL_F_custom == True:
        pickup_height=(volume_epp/cross_section_area)
        for dest in destinations:
            p20.pick_up_tip()
            #    #Distribute the mmix in different wells
            distribute_custom(p20, CONTROL_VOLUME, cntrl_src_well, 1, dest, pickup_height-1, 0,mix_bool)
                #Update volume left in screwcap
            volume_epp=volume_epp-(CONTROL_VOLUME*size_transfer+extra_dispensal)
                #Update pickup_height according to volume left
            pickup_height=(volume_epp/cross_section_area)
            p20.drop_tip()

    ##########################################################################
    #### NOW MOVE THE SAMPLE TO DEEPEWELL RACK #############
    # Transfer with p1000 from source rack to each of the well quadrants
    if TRANSFER_SAMPLES_F == True:
        fill_96_rack(destinations,sources,p1000,mix_bool,SAMPLE_VOLUME,CONTROL_VOLUME,air_gap_volume)
##########################################################################

    for i in range(3):
        gpio.set_rail_lights(False)
        gpio.set_button_light(1,0,0)
        time.sleep(0.3)
        gpio.set_rail_lights(True)
        gpio.set_button_light(0,0,1)
        time.sleep(0.3)
    gpio.set_button_light(0,1,0)
    ctx.comment('Move deepwell plate (slot 5) to Station B for RNA \
extraction.')
