from opentrons import protocol_api
from opentrons.drivers.rpi_drivers import gpio


# metadata
metadata = {
    'protocolName': 'S2 Station C Version 2',
    'author': 'Aitor & JL',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.0'
}

"""
REAGENT SETUP:

- slot 5 2ml tuberack:
    - mastermixes: tube A1
    - positive control: tube B1
    - negative control: tube B2
"""

NUM_SAMPLES = 8
TRANSFER_MMIX = True
TRANSFER_SAMPLES = True


def run(ctx: protocol_api.ProtocolContext):
    #Change light color to red
    gpio.set_button_light(1,0,0)

    source_plate = ctx.load_labware(
       'roche_96_wellplate_100ul', '1',
        'chilled RNA elution plate from station B')

    tempdeck = ctx.load_module('tempdeck', '4')

    pcr_plate = tempdeck.load_labware('transparent_96_wellplate_250ul'
         , 'PCR plate')

    tempdeck.set_temperature(25) # Define temperature of module. Should be 4. 25 for testing purposes

    tuberack = ctx.load_labware(
        'bloquealuminio_24_wellplate_1500ul', '2',
        'Bloque Aluminio 24 Eppendorf Well Plate 1500 µL')

    tips20 = [
        ctx.load_labware('opentrons_96_filtertiprack_20ul', slot)
        for slot in ['5']
    ]

    # pipette
    p20 = ctx.load_instrument('p20_single_gen2', 'right', tip_racks=tips20)

    # setup up sample sources and destinations
    samples = source_plate.wells()[:NUM_SAMPLES]
    dests = pcr_plate.wells()[:NUM_SAMPLES]
    mmix = tuberack.wells()[0]

    # transfer mastermix
    if TRANSFER_MMIX == True:
        p20.pick_up_tip()
        for d in dests:
            p20.transfer(20, mmix, d, new_tip='never')
            p20.blow_out(d.bottom(5))
        p20.drop_tip()

    # transfer samples to corresponding locations
    if TRANSFER_SAMPLES == True:
        for s, d in zip(samples, dests):
            p20.pick_up_tip()
            p20.transfer(5, s, d, new_tip='never')
            p20.mix(1, 10, d)
            p20.aspirate(5, d.top(2))
            p20.drop_tip()

    #Change light color to green
    gpio.set_button_light(0,1,0)
