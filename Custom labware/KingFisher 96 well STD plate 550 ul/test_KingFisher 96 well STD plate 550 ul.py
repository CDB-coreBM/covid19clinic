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
PIPETTE_NAME = 'p300_single'

TIPRACK_SLOT = '5'
TIPRACK_LOADNAME = 'opentrons_96_tiprack_300ul'

LABWARE_DEF_JSON = """{"ordering":[["A1","B1","C1","D1","E1","F1","G1","H1"],["A2","B2","C2","D2","E2","F2","G2","H2"],["A3","B3","C3","D3","E3","F3","G3","H3"],["A4","B4","C4","D4","E4","F4","G4","H4"],["A5","B5","C5","D5","E5","F5","G5","H5"],["A6","B6","C6","D6","E6","F6","G6","H6"],["A7","B7","C7","D7","E7","F7","G7","H7"],["A8","B8","C8","D8","E8","F8","G8","H8"],["A9","B9","C9","D9","E9","F9","G9","H9"],["A10","B10","C10","D10","E10","F10","G10","H10"],["A11","B11","C11","D11","E11","F11","G11","H11"],["A12","B12","C12","D12","E12","F12","G12","H12"]],"brand":{"brand":"KingFisher","brandId":["ThermoFisher","97002534"]},"metadata":{"displayName":"KingFisher 96 well STD plate 550 ul","displayCategory":"wellPlate","displayVolumeUnits":"µL","tags":[]},"dimensions":{"xDimension":127,"yDimension":85,"zDimension":14.85},"wells":{"A1":{"depth":12.4,"totalLiquidVolume":550,"shape":"rectangular","xDimension":8,"yDimension":8,"x":14,"y":74,"z":2.45},"B1":{"depth":12.4,"totalLiquidVolume":550,"shape":"rectangular","xDimension":8,"yDimension":8,"x":14,"y":65,"z":2.45},"C1":{"depth":12.4,"totalLiquidVolume":550,"shape":"rectangular","xDimension":8,"yDimension":8,"x":14,"y":56,"z":2.45},"D1":{"depth":12.4,"totalLiquidVolume":550,"shape":"rectangular","xDimension":8,"yDimension":8,"x":14,"y":47,"z":2.45},"E1":{"depth":12.4,"totalLiquidVolume":550,"shape":"rectangular","xDimension":8,"yDimension":8,"x":14,"y":38,"z":2.45},"F1":{"depth":12.4,"totalLiquidVolume":550,"shape":"rectangular","xDimension":8,"yDimension":8,"x":14,"y":29,"z":2.45},"G1":{"depth":12.4,"totalLiquidVolume":550,"shape":"rectangular","xDimension":8,"yDimension":8,"x":14,"y":20,"z":2.45},"H1":{"depth":12.4,"totalLiquidVolume":550,"shape":"rectangular","xDimension":8,"yDimension":8,"x":14,"y":11,"z":2.45},"A2":{"depth":12.4,"totalLiquidVolume":550,"shape":"rectangular","xDimension":8,"yDimension":8,"x":23,"y":74,"z":2.45},"B2":{"depth":12.4,"totalLiquidVolume":550,"shape":"rectangular","xDimension":8,"yDimension":8,"x":23,"y":65,"z":2.45},"C2":{"depth":12.4,"totalLiquidVolume":550,"shape":"rectangular","xDimension":8,"yDimension":8,"x":23,"y":56,"z":2.45},"D2":{"depth":12.4,"totalLiquidVolume":550,"shape":"rectangular","xDimension":8,"yDimension":8,"x":23,"y":47,"z":2.45},"E2":{"depth":12.4,"totalLiquidVolume":550,"shape":"rectangular","xDimension":8,"yDimension":8,"x":23,"y":38,"z":2.45},"F2":{"depth":12.4,"totalLiquidVolume":550,"shape":"rectangular","xDimension":8,"yDimension":8,"x":23,"y":29,"z":2.45},"G2":{"depth":12.4,"totalLiquidVolume":550,"shape":"rectangular","xDimension":8,"yDimension":8,"x":23,"y":20,"z":2.45},"H2":{"depth":12.4,"totalLiquidVolume":550,"shape":"rectangular","xDimension":8,"yDimension":8,"x":23,"y":11,"z":2.45},"A3":{"depth":12.4,"totalLiquidVolume":550,"shape":"rectangular","xDimension":8,"yDimension":8,"x":32,"y":74,"z":2.45},"B3":{"depth":12.4,"totalLiquidVolume":550,"shape":"rectangular","xDimension":8,"yDimension":8,"x":32,"y":65,"z":2.45},"C3":{"depth":12.4,"totalLiquidVolume":550,"shape":"rectangular","xDimension":8,"yDimension":8,"x":32,"y":56,"z":2.45},"D3":{"depth":12.4,"totalLiquidVolume":550,"shape":"rectangular","xDimension":8,"yDimension":8,"x":32,"y":47,"z":2.45},"E3":{"depth":12.4,"totalLiquidVolume":550,"shape":"rectangular","xDimension":8,"yDimension":8,"x":32,"y":38,"z":2.45},"F3":{"depth":12.4,"totalLiquidVolume":550,"shape":"rectangular","xDimension":8,"yDimension":8,"x":32,"y":29,"z":2.45},"G3":{"depth":12.4,"totalLiquidVolume":550,"shape":"rectangular","xDimension":8,"yDimension":8,"x":32,"y":20,"z":2.45},"H3":{"depth":12.4,"totalLiquidVolume":550,"shape":"rectangular","xDimension":8,"yDimension":8,"x":32,"y":11,"z":2.45},"A4":{"depth":12.4,"totalLiquidVolume":550,"shape":"rectangular","xDimension":8,"yDimension":8,"x":41,"y":74,"z":2.45},"B4":{"depth":12.4,"totalLiquidVolume":550,"shape":"rectangular","xDimension":8,"yDimension":8,"x":41,"y":65,"z":2.45},"C4":{"depth":12.4,"totalLiquidVolume":550,"shape":"rectangular","xDimension":8,"yDimension":8,"x":41,"y":56,"z":2.45},"D4":{"depth":12.4,"totalLiquidVolume":550,"shape":"rectangular","xDimension":8,"yDimension":8,"x":41,"y":47,"z":2.45},"E4":{"depth":12.4,"totalLiquidVolume":550,"shape":"rectangular","xDimension":8,"yDimension":8,"x":41,"y":38,"z":2.45},"F4":{"depth":12.4,"totalLiquidVolume":550,"shape":"rectangular","xDimension":8,"yDimension":8,"x":41,"y":29,"z":2.45},"G4":{"depth":12.4,"totalLiquidVolume":550,"shape":"rectangular","xDimension":8,"yDimension":8,"x":41,"y":20,"z":2.45},"H4":{"depth":12.4,"totalLiquidVolume":550,"shape":"rectangular","xDimension":8,"yDimension":8,"x":41,"y":11,"z":2.45},"A5":{"depth":12.4,"totalLiquidVolume":550,"shape":"rectangular","xDimension":8,"yDimension":8,"x":50,"y":74,"z":2.45},"B5":{"depth":12.4,"totalLiquidVolume":550,"shape":"rectangular","xDimension":8,"yDimension":8,"x":50,"y":65,"z":2.45},"C5":{"depth":12.4,"totalLiquidVolume":550,"shape":"rectangular","xDimension":8,"yDimension":8,"x":50,"y":56,"z":2.45},"D5":{"depth":12.4,"totalLiquidVolume":550,"shape":"rectangular","xDimension":8,"yDimension":8,"x":50,"y":47,"z":2.45},"E5":{"depth":12.4,"totalLiquidVolume":550,"shape":"rectangular","xDimension":8,"yDimension":8,"x":50,"y":38,"z":2.45},"F5":{"depth":12.4,"totalLiquidVolume":550,"shape":"rectangular","xDimension":8,"yDimension":8,"x":50,"y":29,"z":2.45},"G5":{"depth":12.4,"totalLiquidVolume":550,"shape":"rectangular","xDimension":8,"yDimension":8,"x":50,"y":20,"z":2.45},"H5":{"depth":12.4,"totalLiquidVolume":550,"shape":"rectangular","xDimension":8,"yDimension":8,"x":50,"y":11,"z":2.45},"A6":{"depth":12.4,"totalLiquidVolume":550,"shape":"rectangular","xDimension":8,"yDimension":8,"x":59,"y":74,"z":2.45},"B6":{"depth":12.4,"totalLiquidVolume":550,"shape":"rectangular","xDimension":8,"yDimension":8,"x":59,"y":65,"z":2.45},"C6":{"depth":12.4,"totalLiquidVolume":550,"shape":"rectangular","xDimension":8,"yDimension":8,"x":59,"y":56,"z":2.45},"D6":{"depth":12.4,"totalLiquidVolume":550,"shape":"rectangular","xDimension":8,"yDimension":8,"x":59,"y":47,"z":2.45},"E6":{"depth":12.4,"totalLiquidVolume":550,"shape":"rectangular","xDimension":8,"yDimension":8,"x":59,"y":38,"z":2.45},"F6":{"depth":12.4,"totalLiquidVolume":550,"shape":"rectangular","xDimension":8,"yDimension":8,"x":59,"y":29,"z":2.45},"G6":{"depth":12.4,"totalLiquidVolume":550,"shape":"rectangular","xDimension":8,"yDimension":8,"x":59,"y":20,"z":2.45},"H6":{"depth":12.4,"totalLiquidVolume":550,"shape":"rectangular","xDimension":8,"yDimension":8,"x":59,"y":11,"z":2.45},"A7":{"depth":12.4,"totalLiquidVolume":550,"shape":"rectangular","xDimension":8,"yDimension":8,"x":68,"y":74,"z":2.45},"B7":{"depth":12.4,"totalLiquidVolume":550,"shape":"rectangular","xDimension":8,"yDimension":8,"x":68,"y":65,"z":2.45},"C7":{"depth":12.4,"totalLiquidVolume":550,"shape":"rectangular","xDimension":8,"yDimension":8,"x":68,"y":56,"z":2.45},"D7":{"depth":12.4,"totalLiquidVolume":550,"shape":"rectangular","xDimension":8,"yDimension":8,"x":68,"y":47,"z":2.45},"E7":{"depth":12.4,"totalLiquidVolume":550,"shape":"rectangular","xDimension":8,"yDimension":8,"x":68,"y":38,"z":2.45},"F7":{"depth":12.4,"totalLiquidVolume":550,"shape":"rectangular","xDimension":8,"yDimension":8,"x":68,"y":29,"z":2.45},"G7":{"depth":12.4,"totalLiquidVolume":550,"shape":"rectangular","xDimension":8,"yDimension":8,"x":68,"y":20,"z":2.45},"H7":{"depth":12.4,"totalLiquidVolume":550,"shape":"rectangular","xDimension":8,"yDimension":8,"x":68,"y":11,"z":2.45},"A8":{"depth":12.4,"totalLiquidVolume":550,"shape":"rectangular","xDimension":8,"yDimension":8,"x":77,"y":74,"z":2.45},"B8":{"depth":12.4,"totalLiquidVolume":550,"shape":"rectangular","xDimension":8,"yDimension":8,"x":77,"y":65,"z":2.45},"C8":{"depth":12.4,"totalLiquidVolume":550,"shape":"rectangular","xDimension":8,"yDimension":8,"x":77,"y":56,"z":2.45},"D8":{"depth":12.4,"totalLiquidVolume":550,"shape":"rectangular","xDimension":8,"yDimension":8,"x":77,"y":47,"z":2.45},"E8":{"depth":12.4,"totalLiquidVolume":550,"shape":"rectangular","xDimension":8,"yDimension":8,"x":77,"y":38,"z":2.45},"F8":{"depth":12.4,"totalLiquidVolume":550,"shape":"rectangular","xDimension":8,"yDimension":8,"x":77,"y":29,"z":2.45},"G8":{"depth":12.4,"totalLiquidVolume":550,"shape":"rectangular","xDimension":8,"yDimension":8,"x":77,"y":20,"z":2.45},"H8":{"depth":12.4,"totalLiquidVolume":550,"shape":"rectangular","xDimension":8,"yDimension":8,"x":77,"y":11,"z":2.45},"A9":{"depth":12.4,"totalLiquidVolume":550,"shape":"rectangular","xDimension":8,"yDimension":8,"x":86,"y":74,"z":2.45},"B9":{"depth":12.4,"totalLiquidVolume":550,"shape":"rectangular","xDimension":8,"yDimension":8,"x":86,"y":65,"z":2.45},"C9":{"depth":12.4,"totalLiquidVolume":550,"shape":"rectangular","xDimension":8,"yDimension":8,"x":86,"y":56,"z":2.45},"D9":{"depth":12.4,"totalLiquidVolume":550,"shape":"rectangular","xDimension":8,"yDimension":8,"x":86,"y":47,"z":2.45},"E9":{"depth":12.4,"totalLiquidVolume":550,"shape":"rectangular","xDimension":8,"yDimension":8,"x":86,"y":38,"z":2.45},"F9":{"depth":12.4,"totalLiquidVolume":550,"shape":"rectangular","xDimension":8,"yDimension":8,"x":86,"y":29,"z":2.45},"G9":{"depth":12.4,"totalLiquidVolume":550,"shape":"rectangular","xDimension":8,"yDimension":8,"x":86,"y":20,"z":2.45},"H9":{"depth":12.4,"totalLiquidVolume":550,"shape":"rectangular","xDimension":8,"yDimension":8,"x":86,"y":11,"z":2.45},"A10":{"depth":12.4,"totalLiquidVolume":550,"shape":"rectangular","xDimension":8,"yDimension":8,"x":95,"y":74,"z":2.45},"B10":{"depth":12.4,"totalLiquidVolume":550,"shape":"rectangular","xDimension":8,"yDimension":8,"x":95,"y":65,"z":2.45},"C10":{"depth":12.4,"totalLiquidVolume":550,"shape":"rectangular","xDimension":8,"yDimension":8,"x":95,"y":56,"z":2.45},"D10":{"depth":12.4,"totalLiquidVolume":550,"shape":"rectangular","xDimension":8,"yDimension":8,"x":95,"y":47,"z":2.45},"E10":{"depth":12.4,"totalLiquidVolume":550,"shape":"rectangular","xDimension":8,"yDimension":8,"x":95,"y":38,"z":2.45},"F10":{"depth":12.4,"totalLiquidVolume":550,"shape":"rectangular","xDimension":8,"yDimension":8,"x":95,"y":29,"z":2.45},"G10":{"depth":12.4,"totalLiquidVolume":550,"shape":"rectangular","xDimension":8,"yDimension":8,"x":95,"y":20,"z":2.45},"H10":{"depth":12.4,"totalLiquidVolume":550,"shape":"rectangular","xDimension":8,"yDimension":8,"x":95,"y":11,"z":2.45},"A11":{"depth":12.4,"totalLiquidVolume":550,"shape":"rectangular","xDimension":8,"yDimension":8,"x":104,"y":74,"z":2.45},"B11":{"depth":12.4,"totalLiquidVolume":550,"shape":"rectangular","xDimension":8,"yDimension":8,"x":104,"y":65,"z":2.45},"C11":{"depth":12.4,"totalLiquidVolume":550,"shape":"rectangular","xDimension":8,"yDimension":8,"x":104,"y":56,"z":2.45},"D11":{"depth":12.4,"totalLiquidVolume":550,"shape":"rectangular","xDimension":8,"yDimension":8,"x":104,"y":47,"z":2.45},"E11":{"depth":12.4,"totalLiquidVolume":550,"shape":"rectangular","xDimension":8,"yDimension":8,"x":104,"y":38,"z":2.45},"F11":{"depth":12.4,"totalLiquidVolume":550,"shape":"rectangular","xDimension":8,"yDimension":8,"x":104,"y":29,"z":2.45},"G11":{"depth":12.4,"totalLiquidVolume":550,"shape":"rectangular","xDimension":8,"yDimension":8,"x":104,"y":20,"z":2.45},"H11":{"depth":12.4,"totalLiquidVolume":550,"shape":"rectangular","xDimension":8,"yDimension":8,"x":104,"y":11,"z":2.45},"A12":{"depth":12.4,"totalLiquidVolume":550,"shape":"rectangular","xDimension":8,"yDimension":8,"x":113,"y":74,"z":2.45},"B12":{"depth":12.4,"totalLiquidVolume":550,"shape":"rectangular","xDimension":8,"yDimension":8,"x":113,"y":65,"z":2.45},"C12":{"depth":12.4,"totalLiquidVolume":550,"shape":"rectangular","xDimension":8,"yDimension":8,"x":113,"y":56,"z":2.45},"D12":{"depth":12.4,"totalLiquidVolume":550,"shape":"rectangular","xDimension":8,"yDimension":8,"x":113,"y":47,"z":2.45},"E12":{"depth":12.4,"totalLiquidVolume":550,"shape":"rectangular","xDimension":8,"yDimension":8,"x":113,"y":38,"z":2.45},"F12":{"depth":12.4,"totalLiquidVolume":550,"shape":"rectangular","xDimension":8,"yDimension":8,"x":113,"y":29,"z":2.45},"G12":{"depth":12.4,"totalLiquidVolume":550,"shape":"rectangular","xDimension":8,"yDimension":8,"x":113,"y":20,"z":2.45},"H12":{"depth":12.4,"totalLiquidVolume":550,"shape":"rectangular","xDimension":8,"yDimension":8,"x":113,"y":11,"z":2.45}},"groups":[{"metadata":{"displayName":"KingFisher 96 well STD plate 550 ul","displayCategory":"wellPlate","wellBottomShape":"v"},"brand":{"brand":"KingFisher","brandId":["ThermoFisher","97002534"]},"wells":["A1","B1","C1","D1","E1","F1","G1","H1","A2","B2","C2","D2","E2","F2","G2","H2","A3","B3","C3","D3","E3","F3","G3","H3","A4","B4","C4","D4","E4","F4","G4","H4","A5","B5","C5","D5","E5","F5","G5","H5","A6","B6","C6","D6","E6","F6","G6","H6","A7","B7","C7","D7","E7","F7","G7","H7","A8","B8","C8","D8","E8","F8","G8","H8","A9","B9","C9","D9","E9","F9","G9","H9","A10","B10","C10","D10","E10","F10","G10","H10","A11","B11","C11","D11","E11","F11","G11","H11","A12","B12","C12","D12","E12","F12","G12","H12"]}],"parameters":{"format":"irregular","quirks":[],"isTiprack":false,"isMagneticModuleCompatible":false,"loadName":"kingfisher_96_wellplate_550ul"},"namespace":"custom_beta","version":1,"schemaVersion":2,"cornerOffsetFromSlot":{"x":0,"y":0,"z":0}}"""
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
