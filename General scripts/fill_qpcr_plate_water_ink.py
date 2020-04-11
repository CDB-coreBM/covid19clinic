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
CLEAN_QPCR_PLATE = True
TRANSFER_MMIX = True
size_transfer=6


def divide_destinations(l, n):
    # looping till length l
    for i in range(0, len(l), n):
        yield l[i:i + n]

def run(ctx: protocol_api.ProtocolContext):
    from opentrons.drivers.rpi_drivers import gpio
    gpio.set_button_light(1,0,0)
    #Load labware
    pcr_plate = ctx.load_labware(
       'roche_96_wellplate_100ul', '1',
        'chilled RNA elution plate from station B')

    water = ctx.load_labware(
        'bloquealuminio_24_screwcap_wellplate_1500ul', '2',
        'Bloque Aluminio 24 Eppendorf Well Plate 1500 µL').wells()[0].bottom(1)

    ink = ctx.load_labware(
    'nalgene_1_reservoir_300000ul', '3', 'waste reservoir').wells()[0].bottom(1)

    tips20 = [
        ctx.load_labware('opentrons_96_filtertiprack_20ul', slot)
        for slot in ['5']
    ]

    # pipettes
    p20 = ctx.load_instrument('p20_single_gen2', 'right', tip_racks=tips20)

    # setup up sample sources and destinations
    pcr_wells = pcr_plate.wells()[:NUM_SAMPLES]

    # Clean well with P20
    if CLEAN_QPCR_PLATE == True:
        p20.pick_up_tip()
        for d in pcr_wells:
            p20.transfer(30, water, d, mix_after=(2,30), new_tip='never')
            p20.transfer(30, d, ink)
            p20.blow_out(ink.top(-5))
        p20.drop_tip()

    # transfer mastermix with P20
    if TRANSFER_MMIX == True:
        p20.pick_up_tip()
        for d in pcr_wells:
            p20.transfer(30, ink, d, new_tip='never')
            p20.blow_out(d.bottom(5))
        p20.drop_tip()

    gpio.set_button_light(0,1,0)
