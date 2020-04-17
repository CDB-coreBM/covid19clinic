from opentrons import protocol_api

from opentrons.drivers.rpi_drivers import gpio
# metadata
metadata = {
    'protocolName': 'S2 Station C Version 2',
    'author': 'Aitor & JL',
    'source': 'Custom Protocol',
    'apiLevel': '2.0'
}

"""
REAGENT SETUP:
- slot 2 2ml tuberack:
    - mastermixes: tube A1
"""

NUM_SAMPLES = 96
CLEAN_QPCR_PLATE = False
TRANSFER_INK = False
TRANSFER_WATER = True

#Tune variables
size_transfer=1 #Number of wells the distribute function will fill
volume_ink=300 #Volume of transfered master mix
volume_sample=150 #Volume of the sample
volume_screw=30000 #Total volume of screwcap
extra_dispensal=0 #Extra volume for master mix in each distribute transfer

def divide_destinations(l, n):
    # Divide the list of destinations in size n lists.
    for i in range(0, len(l), n):
        yield l[i:i + n]

def distribute_custom(pipette, volume_mmix, mmix, size_transfer, d, waste_pool, pickup_height, extra_dispensal):
    #Custom distribute function that allows for blow_out in different location and adjustement of touch_ti
    pipette.aspirate((size_transfer*volume_mmix)+extra_dispensal, mmix.bottom(0.2))
    #pipette.touch_tip(speed=20, v_offset=-5)
    pipette.move_to(mmix.top(z=-1))
    pipette.aspirate(5) #air gap
    pipette.dispense(5, d.top())
    pipette.dispense(volume_mmix, d)
    pipette.move_to(d.top(z=5))
    #pipette.aspirate(5) #air gap
    pipette.dispense(5)

def check_door():
    return gpio.read_window_switches()

def run(ctx: protocol_api.ProtocolContext):


    if check_door() == True:
        gpio.set_button_light(0.5,0,0.5)
    else:
        gpio.set_button_light(1,0,0)
    #Load labware
    deepwell_plate = ctx.load_labware('abgenestorage_96_wellplate_1200ul','5', 'ABGENE 1200ul 96 well sample plate')


    water_reservoir = ctx.load_labware(
    'nalgene_1_reservoir_300000ul', '2', 'waste reservoir')

    water=water_reservoir.wells()[0] # referenced as reservoir

    tips200 = [
        ctx.load_labware('opentrons_96_filtertiprack_200ul', slot)
        for slot in ['6']
    ]


    # pipettes
    p300 = ctx.load_instrument('p300_multi_gen2', mount='right', tip_racks=tips200)

    # setup up sample sources and destinations
    dests = deepwell_plate.rows()[0][:]


    #transfer water "sample" with P300
    if TRANSFER_WATER == True:
        p300.pick_up_tip()
        for dest in dests:
            #Distribute the mmix in different wells
            for _ in range(2):
                distribute_custom(p300, volume_sample, water, size_transfer, dest, water, 1, extra_dispensal)
    gpio.set_button_light(0,1,0)
