from opentrons import protocol_api
import time
import math

#Statements


# metadata
metadata = {
    'protocolName': 'S2 Station A Version 1',
    'author': 'Aitor & JL <Hospital Clinic Barcelona>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.0'
}

"""
REAGENT SETUP:

- slot 2 12-channel reservoir:
    - viral DNA/RNA buffer: channels 1-3
    - magbeads: channel 4
    - wash 1: channels 5-8
    - wash 2: channels 9-12

- slot 5 12-channel reservoir:
    - EtOH: channels 1-8
    - water: channel 12

"""
def generate_source_table(source):
    for rack_number in range(len(source)):
        if rack_number==0:
            s=source[rack_number].wells()
        else:
            s=s+source[rack_number].wells()
    return s

# generate quadrants for 96 deep well plate with cols=dest_plate.cols()
def quadrants(r):
    for col in range(0,6):
        if col==0:
            quadrant1=r[col][:4]
        else:
            quadrant1=quadrant1+r[col][:4]
    for col in range(6,12):
        if col==6:
            quadrant2=r[col][:4]
        else:
            quadrant2=quadrant2+r[col][:4]
    for col in range(6,12):
        if col==6:
            quadrant3=r[col][4:]
        else:
            quadrant3=quadrant3+r[col][4:]
    for col in range(0,6):
        if col==0:
            quadrant4=r[col][4:]
        else:
            quadrant4=quadrant4+r[col][4:]
    return [quadrant1,quadrant2,quadrant3,quadrant4]

# Distribute control liquid in deepwell
def distribute_custom(pipette, dispense_volume, source, size_transfer, destination, pickup_height, extra_dispensal):
    pipette.aspirate((size_transfer*dispense_volume)+extra_dispensal, source.bottom(pickup_height))
    #pipette.move_to(source.top(z=0))
    pipette.touch_tip(speed=20, v_offset=-3,radius=1.05)
    #pipette.aspirate(5) # aspirate some air
    pipette.dispense(dispense_volume, destination.bottom(2))
    ### AÑADIR MIX!

    pipette.move_to(destination.top(z=5))
    pipette.blow_out()
    #pipette.move_to(destination.top(z=-8))
    pipette.touch_tip(speed=20,radius=1.05)

# Function to fill the 96 well rack in quadrants
def fill_96_rack(dests, src,pipette,bool,SAMPLE_VOLUME,CONTROL_VOLUME):
    for s, d in zip(src, dests):
        pipette.pick_up_tip()
        pipette.aspirate(SAMPLE_VOLUME,s.bottom(1) )
        pipette.touch_tip(speed=20, v_offset=-5)
        pipette.move_to(s.top(z=5))
        pipette.aspirate(5)
        pipette.dispense(SAMPLE_VOLUME+5, d)
        if bool == True:
            pipette.mix(1, SAMPLE_VOLUME+CONTROL_VOLUME+10, d)
            pipette.move_to(d.top(z=-5))
            pipette.blow_out()

        pipette.move_to(d.top(z=-5))
        pipette.dispense(5)
        pipette.aspirate(10)
        pipette.touch_tip(speed=20, v_offset=-5)

        #pipette.transfer(SAMPLE_VOLUME, s.bottom(1), d.bottom(1), new_tip='never',air_gap=5,touch_tip=True)
        pipette.drop_tip(home_after=False)


##########################################################################
NUM_SAMPLES = 5
SAMPLE_VOLUME = 300
CONTROL_VOLUME = 10
TRANSFER_SAMPLES_F = True
# TRANSFER_CONTROL_F = False # deactivated
TRANSFER_CONTROL_F_custom = False
mix_bool=False
volume_epp = 1500
extra_dispensal = 0
size_transfer = 1
cross_section_area = 63.61 ## Ojo que es cónico en su parte final y haya que modificar esta función
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
            'source tuberack with screwcap' + str(i+1)) for i, slot in enumerate(['4','6','3','1'][:rack_num])
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
        'nunc_96_wellplate_2000ul', '5',
        'NUNC STORAGE 96 Well Plate 2000 µL')

# Load tipracks
##############
    tiprack = ctx.load_labware(
        'opentrons_96_filtertiprack_20ul', '11', '20µl tiprack')
    tips1000 = ctx.load_labware(
        'opentrons_96_filtertiprack_1000ul', '10', '1000µl tiprack')

    # Load pipettes

    p1000 = ctx.load_instrument('p1000_single_gen2', 'left', tip_racks=[tips1000])

    # setup samples and destinations
    #sources = [well for rack in source_racks for well in rack.wells()][:NUM_SAMPLES]
    #dests = [well for col in dest_plate.columns()[0::2] for well in col] + [well for col in dest_plate.columns()[1::2] for well in col]
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
    # transfer with p20 from control source
    #for s, d in zip(sources, dests):
    #    p1000.pick_up_tip()
    #    p1000.transfer(
    #        SAMPLE_VOLUME, s.bottom(5), d.bottom(5), new_tip='never')
    #    p1000.aspirate(100, d.top())
    #    p1000.drop_tip()

#### NOW MOVE THE SAMPLE TO DEEPEWELL RACK #############
    # Transfer with p1000 from source rack to each of the well quadrants
    if TRANSFER_SAMPLES_F == True:
        #for source in sources:
        fill_96_rack(destinations,sources,p1000,mix_bool,SAMPLE_VOLUME,CONTROL_VOLUME)
##########################################################################

    #### NOW INTRODUCE THE CONTROL SRC ############## deprecated
    # transfer with p20 from control source with the original function from opentrons

    #if TRANSFER_CONTROL_F == True:
    #    for d in dests:
    #        p20.pick_up_tip()
    #        p20.transfer(
    #            CONTROL_VOLUME, cntrl_src_well.bottom(5), d.bottom(5), new_tip='never')
    #        p20.aspirate(10, d.top())
    #        p20.drop_tip()


##########################################################################

    for i in range(8):
        gpio.set_rail_lights(False)
        gpio.set_button_light(1,0,0)
        time.sleep(0.3)
        gpio.set_rail_lights(True)
        gpio.set_button_light(0,0,1)
        time.sleep(0.3)
    ctx.comment('Move deepwell plate (slot 5) to Station B for RNA \
extraction.')
