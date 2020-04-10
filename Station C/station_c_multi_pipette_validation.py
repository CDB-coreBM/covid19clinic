from opentrons import protocol_api


# metadata
metadata = {
    'protocolName': 'S2 Station C Version 2',
    'author': 'Aitor & JL',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.0'
}

"""
REAGENT SETUP:
- slot 2 2ml tuberack:
    - mastermixes: tube A1
"""

NUM_SAMPLES = 96
TRANSFER_MMIX = True
TRANSFER_SAMPLES = True


def run(ctx: protocol_api.ProtocolContext):
    from opentrons.drivers.rpi_drivers import gpio
    gpio.set_button_light(1,0,0)
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

    tips20 = [
        ctx.load_labware('opentrons_96_filtertiprack_20ul', slot)
        for slot in ['5']
    ]

    tips200 = [
        ctx.load_labware('opentrons_96_filtertiprack_200ul', slot)
        for slot in ['6']
    ]

    # pipettes
    p20 = ctx.load_instrument('p20_single_gen2', 'right', tip_racks=tips20)
    p300 = ctx.load_instrument('p300_single_gen2', 'left', tip_racks=tips200)

    # setup up sample sources and destinations
    samples = source_plate.wells()[:NUM_SAMPLES]
    dests = pcr_plate.wells()[:NUM_SAMPLES]
    #dests2 = pcr_plate.wells()[int(NUM_SAMPLES/2):NUM_SAMPLES]
    dest_fin= pcr_plate.wells()[:NUM_SAMPLES]
    mmix = tuberack.wells()[0]

'''
    # transfer mastermix with P20
    if TRANSFER_MMIX == True:
        p20.pick_up_tip()
        for d in dests:
            p20.transfer(20, mmix, d, new_tip='never')
            p20.blow_out(d.bottom(5))
        p20.drop_tip()
'''
    # transfer mastermix with P300
    if TRANSFER_MMIX == True:
        p300.pick_up_tip()
        p300.distribute(20, mmix, dests2, new_tip='never', disposal_volume=0)
        #p300.blow_out(d.bottom(5))
        p300.drop_tip()

    # transfer 8 first samples to corresponding locations
    if TRANSFER_SAMPLES == True:
        for s, d in zip(samples, dest_fin):
            p20.pick_up_tip()
            p20.transfer(5, s, d, new_tip='never')
            p20.mix(1, 10, d)
            p20.aspirate(5, d.top(2))
            p20.drop_tip()

    gpio.set_button_light(0,1,0)
