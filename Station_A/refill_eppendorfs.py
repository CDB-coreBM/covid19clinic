from opentrons import protocol_api

# metadata
metadata = {
    'protocolName': 'S2 Station A Version 1',
    'author': 'Nick <protocols@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.0'
}


NUM_SAMPLES = 96
SAMPLE_VOLUME = 400


def run(ctx: protocol_api.ProtocolContext):
    from opentrons.drivers.rpi_drivers import gpio
    gpio.set_button_light(1,0,0) # RGB 0-1
    # load labware
    dest_racks = [ctx.load_labware(
            'opentrons_24_tuberack_eppendorf_2ml_safelock_snapcap', slot,
            'source tuberack with eppendorf' + str(i+1)) for i, slot in enumerate(['4','6','3','1'])
        ]
    water_src = ctx.load_labware(
        'nalgene_1_reservoir_300000ul','2',
        'Water source 300ml')


# Load tipracks
    #tiprack = ctx.load_labware(
    #    'opentrons_96_filtertiprack_20ul', '11', '20µl tiprack')
    tips1000 = ctx.load_labware(
        'opentrons_96_filtertiprack_1000ul', '10', '1000µl tiprack')

    # Load pipettes
    #p20 = ctx.load_instrument(
    #    'p20_single_gen2', 'right', tip_racks=[tiprack])
    p1000 = ctx.load_instrument('p1000_single_gen2', 'left', tip_racks=[tips1000])

    source=water_src.wells()[0]
    p1000.pick_up_tip()
    for dest in dest_racks:
        p1000.distribute(SAMPLE_VOLUME,water_src.wells()[0],[d.bottom(2) for d in dest.wells()],disposal_volume=0,new_tip='never')
