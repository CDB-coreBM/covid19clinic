from opentrons import protocol_api

# metadata
metadata = {
    'protocolName': 'S2 Station C Version 1',
    'author': 'Nick <protocols@opentrons.com>',
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
TRANSFER_MMIX=True
TRANSFER_SAMPLES=True


def run(ctx: protocol_api.ProtocolContext):
    source_plate = ctx.load_labware(
       'transparent_96_wellplate_250ul', '1',
        'chilled RNA elution plate from station B')

    tempdeck = ctx.load_module('tempdeck', '4')

    pcr_plate = tempdeck.load_labware(
         'roche_96_wellplate_100ul', 'PCR plate')

    tempdeck.set_temperature(25)

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
    mm = tuberack.rows()[0]

    # transfer mastermix
    if TRANSFER_MMIX:
        p20.pick_up_tip()
        for d in dests:
            p20.transfer(20, mm, d, new_tip='never')
            p20.blow_out(d.bottom(5))
        p20.drop_tip()

    # transfer samples to corresponding locations
    if TRANSFER_SAMPLES:
        for s, d in zip(samples, dests):
            p20.pick_up_tip()
            p20.transfer(5, s, d, new_tip='never')
            p20.mix(1, 10, d)
            p20.aspirate(5, d.top(2))
            p20.drop_tip()
