from opentrons import protocol_api


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
size_transfer=5 #Number of wells the distribute function will fill
volume_ink=20 #Volume of transfered master mix
volume_sample=20 #Volume of the sample
volume_screw=1500 #Total volume of screwcap
extra_dispensal=5 #Extra volume for master mix in each distribute transfer

def divide_destinations(l, n):
    # Divide the list of destinations in size n lists.
    for i in range(0, len(l), n):
        yield l[i:i + n]

def distribute_custom(pipette, volume_mmix, mmix, size_transfer, dest, waste_pool, pickup_height, extra_dispensal):
    #Custom distribute function that allows for blow_out in different location and adjustement of touch_tip
    pipette.aspirate((size_transfer*volume_mmix)+extra_dispensal, mmix.wells()[0].bottom(1))
    #pipette.touch_tip(speed=20, v_offset=-5)
    pipette.move_to(mmix.wells()[0].top(z=5))
    pipette.aspirate(5) #air gap
    for d in dest:
        pipette.dispense(5, d.top())
        pipette.dispense(volume_mmix, d)
        pipette.move_to(d.top(z=5))
        pipette.aspirate(5) #air gap
    pipette.dispense(5)
    pipette.blow_out(waste_pool.wells()[0].bottom(5))

def check_door():
    return gpio.read_window_switches()

def run(ctx: protocol_api.ProtocolContext):
    from opentrons.drivers.rpi_drivers import gpio

    if check_door() == True:
        gpio.set_button_light(0.5,0,0.5)
    else:
        gpio.set_button_light(1,0,0)
    #Load labware
    pcr_plate = ctx.load_labware(
       'roche_96_wellplate_100ul', '1',
        'chilled RNA elution plate from station B')

    water = ctx.load_labware(
        'bloquealuminio_24_screwcap_wellplate_1500ul', '2',
        'Bloque Aluminio 24 Eppendorf Well Plate 1500 µL')


    ink_reservoir = ctx.load_labware(
    'nalgene_1_reservoir_300000ul', '3', 'waste reservoir')

    tips20 = [
        ctx.load_labware('opentrons_96_filtertiprack_20ul', slot)
        for slot in ['5']
    ]
    tips200 = [
        ctx.load_labware('opentrons_96_filtertiprack_200ul', slot)
        for slot in ['6']
    ]


    # pipettes
    p300 = ctx.load_instrument('p300_single_gen2', mount='left', tip_racks=tips200)

    # setup up sample sources and destinations
    pcr_wells = pcr_plate.wells()[:NUM_SAMPLES]
    ink_remaining=ink_reservoir.wells()[0].top(-5)
    ink=ink_reservoir.wells()[0].bottom(1)
    water1 = water.wells()[0].bottom(1)
    water2 = water.wells()[4].bottom(1)

    #Divide destination wells in small groups for P300 pipette
    dests = list(divide_destinations(pcr_wells, size_transfer))

    # Clean well with P300
    if CLEAN_QPCR_PLATE == True:
        p300.pick_up_tip()
        water_src=water1
        i=0
        for d in pcr_wells:
            if i==48:
                water_src=water2
            p300.transfer(volume_ink*1.5, water_src, d, mix_after=(3,volume_ink), air_gap=5, new_tip='never')
            #pipette.aspirate(5) #air gap
            p300.transfer(volume_ink*1.6, d, ink, new_tip='never')
            p300.blow_out(ink_remaining)
            i+=1
        p300.drop_tip()


    #transfer ink "sample" with P300
    if TRANSFER_INK == True:
        p300.pick_up_tip()
        for dest in dests:
            #Distribute the mmix in different wells
            distribute_custom(p300, volume_sample, ink_reservoir, size_transfer, dest, ink_reservoir, 1, extra_dispensal)
        p300.drop_tip()

    #transfer water "sample" with P300
    if TRANSFER_WATER == True:
        p300.pick_up_tip()
        for dest in dests:
            #Distribute the mmix in different wells
            distribute_custom(p300, volume_sample, water    , size_transfer, dest, ink_reservoir, 1, extra_dispensal)
        p300.drop_tip()
    gpio.set_button_light(0,1,0)
