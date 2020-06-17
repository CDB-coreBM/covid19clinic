import json
from opentrons import protocol_api, types

CALIBRATION_CROSS_COORDS = {
    '1': {
        'x': 12.13,
        'y': 9.0,
        'z': 0.0
    },
    '3': {
        'x': 380.87,
        'y': 9.0,
        'z': 0.0
    },
    '7': {
        'x': 12.13,
        'y': 258.0,
        'z': 0.0
    }
}
CALIBRATION_CROSS_SLOTS = ['1', '3', '7']
TEST_LABWARE_SLOT = '3'

RATE = 0.25  # % of default speeds
SLOWER_RATE = 0.1

PIPETTE_MOUNT = 'right'
PIPETTE_NAME = 'p1000_single_gen2'

TIPRACK_SLOT = '5'
TIPRACK_LOADNAME = 'opentrons_96_tiprack_1000ul'

LABWARE_DEF_JSON = """{"ordering":[["A1","B1","C1","D1"],["A2","B2","C2","D2"],["A3","B3","C3","D3"],["A4","B4","C4","D4"],["A5","B5","C5","D5"],["A6","B6","C6","D6"]],"brand":{"brand":"NGNY","brandId":["01"]},"metadata":{"displayName":"NGNY 24 Tube Rack 5000 µL","displayCategory":"tubeRack","displayVolumeUnits":"µL","tags":[]},"dimensions":{"xDimension":127.75,"yDimension":85.5,"zDimension":77},"wells":{"A1":{"depth":73,"totalLiquidVolume":5000,"shape":"circular","diameter":10,"x":18.21,"y":75.43,"z":4},"B1":{"depth":73,"totalLiquidVolume":5000,"shape":"circular","diameter":10,"x":18.21,"y":56.15,"z":4},"C1":{"depth":73,"totalLiquidVolume":5000,"shape":"circular","diameter":10,"x":18.21,"y":36.87,"z":4},"D1":{"depth":73,"totalLiquidVolume":5000,"shape":"circular","diameter":10,"x":18.21,"y":17.59,"z":4},"A2":{"depth":73,"totalLiquidVolume":5000,"shape":"circular","diameter":10,"x":38.1,"y":75.43,"z":4},"B2":{"depth":73,"totalLiquidVolume":5000,"shape":"circular","diameter":10,"x":38.1,"y":56.15,"z":4},"C2":{"depth":73,"totalLiquidVolume":5000,"shape":"circular","diameter":10,"x":38.1,"y":36.87,"z":4},"D2":{"depth":73,"totalLiquidVolume":5000,"shape":"circular","diameter":10,"x":38.1,"y":17.59,"z":4},"A3":{"depth":73,"totalLiquidVolume":5000,"shape":"circular","diameter":10,"x":57.99,"y":75.43,"z":4},"B3":{"depth":73,"totalLiquidVolume":5000,"shape":"circular","diameter":10,"x":57.99,"y":56.15,"z":4},"C3":{"depth":73,"totalLiquidVolume":5000,"shape":"circular","diameter":10,"x":57.99,"y":36.87,"z":4},"D3":{"depth":73,"totalLiquidVolume":5000,"shape":"circular","diameter":10,"x":57.99,"y":17.59,"z":4},"A4":{"depth":73,"totalLiquidVolume":5000,"shape":"circular","diameter":10,"x":77.88,"y":75.43,"z":4},"B4":{"depth":73,"totalLiquidVolume":5000,"shape":"circular","diameter":10,"x":77.88,"y":56.15,"z":4},"C4":{"depth":73,"totalLiquidVolume":5000,"shape":"circular","diameter":10,"x":77.88,"y":36.87,"z":4},"D4":{"depth":73,"totalLiquidVolume":5000,"shape":"circular","diameter":10,"x":77.88,"y":17.59,"z":4},"A5":{"depth":73,"totalLiquidVolume":5000,"shape":"circular","diameter":10,"x":97.77,"y":75.43,"z":4},"B5":{"depth":73,"totalLiquidVolume":5000,"shape":"circular","diameter":10,"x":97.77,"y":56.15,"z":4},"C5":{"depth":73,"totalLiquidVolume":5000,"shape":"circular","diameter":10,"x":97.77,"y":36.87,"z":4},"D5":{"depth":73,"totalLiquidVolume":5000,"shape":"circular","diameter":10,"x":97.77,"y":17.59,"z":4},"A6":{"depth":73,"totalLiquidVolume":5000,"shape":"circular","diameter":10,"x":117.66,"y":75.43,"z":4},"B6":{"depth":73,"totalLiquidVolume":5000,"shape":"circular","diameter":10,"x":117.66,"y":56.15,"z":4},"C6":{"depth":73,"totalLiquidVolume":5000,"shape":"circular","diameter":10,"x":117.66,"y":36.87,"z":4},"D6":{"depth":73,"totalLiquidVolume":5000,"shape":"circular","diameter":10,"x":117.66,"y":17.59,"z":4}},"groups":[{"metadata":{"displayName":"NGNY 24 Tube Rack 5000 µL","displayCategory":"tubeRack","wellBottomShape":"u"},"brand":{"brand":"NGNY","brandId":["01"]},"wells":["A1","B1","C1","D1","A2","B2","C2","D2","A3","B3","C3","D3","A4","B4","C4","D4","A5","B5","C5","D5","A6","B6","C6","D6"]}],"parameters":{"format":"irregular","quirks":[],"isTiprack":false,"isMagneticModuleCompatible":false,"loadName":"ngny_24_tuberack_5000ul"},"namespace":"custom_beta","version":1,"schemaVersion":2,"cornerOffsetFromSlot":{"x":0,"y":0,"z":0}}"""
LABWARE_DEF = json.loads(LABWARE_DEF_JSON)
LABWARE_LABEL = LABWARE_DEF.get('metadata', {}).get(
    'displayName', 'test labware')

metadata = {'apiLevel': '2.0'}


def uniq(l):
    res = []
    for i in l:
        if i not in res:
            res.append(i)
    return res

def run(protocol: protocol_api.ProtocolContext):
    tiprack = protocol.load_labware(TIPRACK_LOADNAME, TIPRACK_SLOT)
    pipette = protocol.load_instrument(
        PIPETTE_NAME, PIPETTE_MOUNT, tip_racks=[tiprack])

    test_labware = protocol.load_labware_from_definition(
        LABWARE_DEF,
        TEST_LABWARE_SLOT,
        LABWARE_LABEL,
    )

    num_cols = len(LABWARE_DEF.get('ordering', [[]]))
    num_rows = len(LABWARE_DEF.get('ordering', [[]])[0])
    well_locs = uniq([
        'A1',
        '{}{}'.format(chr(ord('A') + num_rows - 1), str(num_cols))])

    pipette.pick_up_tip()

    def set_speeds(rate):
        protocol.max_speeds.update({
            'X': (600 * rate),
            'Y': (400 * rate),
            'Z': (125 * rate),
            'A': (125 * rate),
        })

        speed_max = max(protocol.max_speeds.values())

        for instr in protocol.loaded_instruments.values():
            instr.default_speed = speed_max

    set_speeds(RATE)

    for slot in CALIBRATION_CROSS_SLOTS:
        coordinate = CALIBRATION_CROSS_COORDS[slot]
        location = types.Location(point=types.Point(**coordinate),
                                  labware=None)
        pipette.move_to(location)
        protocol.pause(
            f"Confirm {PIPETTE_MOUNT} pipette is at slot {slot} calibration cross")

    pipette.home()
    protocol.pause(f"Place your labware in Slot {TEST_LABWARE_SLOT}")

    for well_loc in well_locs:
        well = test_labware.well(well_loc)
        all_4_edges = [
            [well._from_center_cartesian(x=-1, y=0, z=1), 'left'],
            [well._from_center_cartesian(x=1, y=0, z=1), 'right'],
            [well._from_center_cartesian(x=0, y=-1, z=1), 'front'],
            [well._from_center_cartesian(x=0, y=1, z=1), 'back']
        ]

        set_speeds(RATE)
        pipette.move_to(well.top())
        protocol.pause("Moved to the top of the well")

        for edge_pos, edge_name in all_4_edges:
            set_speeds(SLOWER_RATE)
            edge_location = types.Location(point=edge_pos, labware=None)
            pipette.move_to(edge_location)
            protocol.pause(f'Moved to {edge_name} edge')

        set_speeds(RATE)
        pipette.move_to(well.bottom())
        protocol.pause("Moved to the bottom of the well")

        pipette.blow_out(well)

    set_speeds(1.0)
    pipette.return_tip()
