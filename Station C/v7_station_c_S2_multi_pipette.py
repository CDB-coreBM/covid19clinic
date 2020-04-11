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
- slot 2 2ml screwcap in tuberack:
    - mastermix: tube A1
    - mastermix: tube A2
"""

NUM_SAMPLES = 96
TRANSFER_MMIX = True
TRANSFER_SAMPLES = False
size_transfer=7
volume_mmix=24.6
volume_sample=5.4
volume_screw=1500
extra_dispensal=5

def divide_destinations(l, n):
    # looping till length l
    for i in range(0, len(l), n):
        yield l[i:i + n]

def distribute_mmix(pipette, volume_mmix, mmix, size_transfer, dest, waste_pool, pickup_height, extra_dispensal):
    pipette.aspirate((size_transfer*volume_mmix)+extra_dispensal, mmix.bottom(pickup_height))
    pipette.touch_tip(speed=20, v_offset=-5)
    pipette.move_to(mmix.top(z=5))
    pipette.aspirate(5)
    for d in dest:
        pipette.dispense(5, d.top())
        pipette.dispense(volume_mmix, d)
        pipette.move_to(d.top(z=5))
        pipette.aspirate(5)
    pipette.dispense(5)
    pipette.blow_out(waste_pool.wells()[0].bottom(5))

def run(ctx: protocol_api.ProtocolContext):
    #Set light color to red
    gpio.set_button_light(1,0,0)
    global volume_screw

    #Load labware
    source_plate = ctx.load_labware(
       'roche_96_wellplate_100ul', '1',
        'chilled RNA elution plate from station B')

    tuberack = ctx.load_labware(
        'bloquealuminio_24_screwcap_wellplate_1500ul', '2',
        'Bloque Aluminio 24 Eppendorf Well Plate 1500 µL')

    tempdeck = ctx.load_module('tempdeck', '4')

    #Define temperature of module. Should be 4. 25 for testing purposes
    tempdeck.set_temperature(25)

    pcr_plate = tempdeck.load_labware('transparent_96_wellplate_250ul'
         , 'PCR plate')

    #Load Tipracks
    tips20 = [
        ctx.load_labware('opentrons_96_filtertiprack_20ul', slot)
        for slot in ['5']
    ]

    tips200 = [
        ctx.load_labware('opentrons_96_filtertiprack_200ul', slot)
        for slot in ['6']
    ]

    waste_pool = ctx.load_labware('nalgene_1_reservoir_300000ul', '11',
        'waste reservoir nalgene')

    # pipettes
    p20 = ctx.load_instrument('p20_single_gen2', mount='right', tip_racks=tips20)
    p300 = ctx.load_instrument('p300_single_gen2', mount='left', tip_racks=tips200)


    # setup up sample sources and destinations
    samples = source_plate.wells()[:NUM_SAMPLES]
    pcr_wells = pcr_plate.wells()[:NUM_SAMPLES]

    #Divide destination wells in small groups for P300 pipette
    dests = list(divide_destinations(pcr_wells, size_transfer))

    #Set mmix source to first screwcap
    mmix = tuberack.wells()[0]

    # transfer mastermix with P300
    if TRANSFER_MMIX == True:
        p300.pick_up_tip()
        pickup_height=(volume_screw/53.45)
        for dest in dests:
            #We make sure there is enough volume in screwcap one or we switch
            if volume_screw < (volume_mmix*len(dest)+extra_dispensal+35):
                mmix = tuberack.wells()[4]
                volume_screw=1500 #New tube is full now
                pickup_height=(volume_screw/53.45)
            #Distribute the mmix in different wells
            distribute_mmix(p300, volume_mmix, mmix, size_transfer, dest, waste_pool, pickup_height, extra_dispensal)
            #Update volume left in screwcap
            volume_screw=volume_screw-(volume_mmix*len(dest)+extra_dispensal)
            #Update pickup_height according to volume left
            pickup_height=(volume_screw/53.45)
        p300.drop_tip()

    # transfer samples to corresponding locations with p20
    if TRANSFER_SAMPLES == True:
        for s, d in zip(samples, pcr_wells):
            p20.pick_up_tip()
            p20.transfer(volume_sample, s, d, new_tip='never')
            p20.mix(1, 10, d)
            p20.aspirate(5, d.top(2))
            p20.drop_tip(ctx.fixed_trash)

    #Set light color to green
    gpio.set_button_light(0,1,0)
