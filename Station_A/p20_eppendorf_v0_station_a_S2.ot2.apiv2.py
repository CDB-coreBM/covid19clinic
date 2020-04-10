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
SAMPLE_VOLUME = 15


def run(ctx: protocol_api.ProtocolContext):

    # load labware
    source_racks = [
        ctx.load_labware(
            'opentrons_24_tuberack_eppendorf_2ml_safelock_snapcap', slot,
            'source tuberack ' + str(i+1))
        for i, slot in enumerate(['1', '4','7','10'])
    ]
    dest_plate = ctx.load_labware(
        'roche_96_wellplate_100ul', '5',
        'ROCHE 96 Well Plate 100 µL')
    tiprack = ctx.load_labware(
        'opentrons_96_filtertiprack_20ul', '11', '20µl tiprack')

    # load pipette
    #p1000 = ctx.load_instrument('p1000_single_gen2', 'right', tip_racks=[tiprack])

    p20 = ctx.load_instrument(
        'p20_single_gen2', 'right', tip_racks=[tiprack])

    # setup samples
    sources = [well for rack in source_racks for well in rack.wells()][:NUM_SAMPLES]

    dests = [well for col in dest_plate.columns()[0::2] for well in col] + [well for col in dest_plate.columns()[1::2] for well in col]

    # transfer with p1000
    """for s, d in zip(sources, dests):
        p1000.pick_up_tip()
        p1000.transfer(
            SAMPLE_VOLUME, s.bottom(5), d.bottom(5), new_tip='never')
        p1000.aspirate(10, d.top())
        p1000.drop_tip()"""

    # transfer with p20
    for s, d in zip(sources, dests):
        p20.pick_up_tip()
        p20.transfer(
            SAMPLE_VOLUME, s.bottom(5), d.bottom(5), new_tip='never')
        p20.aspirate(10, d.top())
        p20.drop_tip()
