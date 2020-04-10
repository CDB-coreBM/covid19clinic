from opentrons import protocol_api

# metadata
metadata = {
    'protocolName': 'S2 Station A Version 1',
    'author': 'Nick <protocols@opentrons.com>',
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

NUM_SAMPLES = 96
SAMPLE_VOLUME = 300
CONTROL_VOLUME = 10


def run(ctx: protocol_api.ProtocolContext):
    from opentrons.drivers.rpi_drivers import gpio
    gpio.set_button_light(1,0,0) # RGB 0-1
    # load labware
    source_racks = [ctx.load_labware(
            'opentrons_24_tuberack_eppendorf_2ml_safelock_snapcap', slot,
            'source tuberack with eppendorf' + str(i+1)) for i, slot in enumerate(['1','3','4','6'])
        ]
    tempdeck=ctx.load_module('tempdeck','7')
    tempdeck.set_temperature(25)
    control_src = tempdeck.load_labware(
        'bloquealuminio_24_wellplate_1500ul',
        'Bloque Aluminio 24 Well Plate 1500 µL')

    dest_plate = ctx.load_labware(
        'nunc_96_wellplate_2000ul', '5',
        'NUNC STORAGE 96 Well Plate 2000 µL')

    tiprack = ctx.load_labware(
        'opentrons_96_filtertiprack_20ul', '11', '20µl tiprack')
    tips1000 = ctx.load_labware(
        'opentrons_96_filtertiprack_1000ul', '10', '1000µl tiprack')

    # load pipette
    #p1000 = ctx.load_instrument('p1000_single_gen2', 'right', tip_racks=[tiprack])

    p20 = ctx.load_instrument(
        'p20_single_gen2', 'right', tip_racks=[tiprack])

    p1000 = ctx.load_instrument('p1000_single_gen2', 'left', tip_racks=[tips1000])

    # setup samples
    sources = [well for rack in source_racks for well in rack.wells()][:NUM_SAMPLES]

    dests = [well for col in dest_plate.columns()[0::2] for well in col] + [well for col in dest_plate.columns()[1::2] for well in col]

    cntrl_src_well=control_src.wells()[0]

    # transfer with p1000 samples
    for s, d in zip(sources, dests):
        p1000.pick_up_tip()
        p1000.transfer(
            SAMPLE_VOLUME, s.bottom(5), d.bottom(5), new_tip='never')
        p1000.aspirate(10, d.top())
        p1000.drop_tip()

    # transfer with p20 from control source
    for d in dests:
        p20.pick_up_tip()
        p20.transfer(
            SAMPLE_VOLUME, cntrl_src_well.bottom(5), d.bottom(5), new_tip='never')
        p20.aspirate(10, d.top())
        p20.drop_tip()

    ctx.comment('Move deepwell plate (slot 5) to Station B for RNA \
extraction.')
