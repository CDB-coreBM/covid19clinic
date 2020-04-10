import re
import functools
import opentrons
import typing

metadata = {"apiLevel": "2.2"}


PAUSE_ON_EACH_CROSS = False


DECK_CLEARANCE = 0.5
CALIBRATION_CROSSES = [
    {"coordinates": (12.13,  9.0,   DECK_CLEARANCE), "reach_with_front_channel": True},
    {"coordinates": (380.87, 9.0,   DECK_CLEARANCE), "reach_with_front_channel": True},
    {"coordinates": (12.13,  348.5, DECK_CLEARANCE), "reach_with_front_channel": False}
]


TIP_RACK_SLOTS = [5, 8]


def is_multi_channel(pipette_name: str) -> bool:
    return "multi" in pipette_name

    
def tip_rack_for_pipette(pipette_name: str) -> str:
    pipette_volume = re.match(r"^p(?P<volume>\d+)_.*$", pipette_name).group("volume")
    tip_volume = {
        "50": "300", # P50s use 300 µL tips.
        "20": "10", # P20s use 10 µL tips.
    }.get(pipette_volume, pipette_volume)
    return f"opentrons_96_tiprack_{tip_volume}ul"


def load_tip_racks(protocol: opentrons.protocol_api.ProtocolContext, pipette_names: typing.Iterable[str]) -> typing.Dict[str, opentrons.protocol_api.labware.Labware]:
    needed_tip_rack_names = set(tip_rack_for_pipette(pipette_name) for pipette_name in pipette_names)
    tip_racks_by_name = {name: protocol.load_labware(name, slot) for name, slot in zip(needed_tip_rack_names, TIP_RACK_SLOTS)}
    return tip_racks_by_name

     
def load_attached_pipettes(protocol: opentrons.protocol_api.ProtocolContext) -> typing.List[opentrons.protocol_api.InstrumentContext]:
    pipette_names_by_mount = {mount: name for mount, name in attached_pipette_names(protocol).items() if name is not None}
    tip_racks_by_name = load_tip_racks(protocol, pipette_names=pipette_names_by_mount.values())
    pipettes = [
        protocol.load_instrument(
            name,
            mount=mount,
            tip_racks=[tip_racks_by_name[tip_rack_for_pipette(name)]]
        )
        for mount, name in pipette_names_by_mount.items()
    ]
    return pipettes


@functools.lru_cache(maxsize=1)
def attached_pipette_names(protocol: opentrons.protocol_api.ProtocolContext) -> typing.Dict[str, typing.Optional[str]]:
    """
    Return the load names of the pipettes that are currently attached to the robot.
    
    They're returned in a dict indexed by mount name ("left" or "right").
    
    If a mount is unoccupied, its value is None.
    """
    
    # functools.lru_cache is so cache_instruments() is only called once.  Calling it more than
    # once invalidates previous InstrumentContext objects, which would make this useless for
    # protocols where more than one pipette is loaded.
    
    # Use secret internal magic to get the currently attached pipette.
    protocol._hw_manager.hardware.cache_instruments()
    attached_instruments = protocol._hw_manager.hardware.get_attached_instruments()
    
    instrument_name = lambda i: i["name"] if i else None
    return {
        "left": instrument_name(attached_instruments[opentrons.types.Mount.LEFT]),
        "right": instrument_name(attached_instruments[opentrons.types.Mount.RIGHT])
    }

    
def run(protocol: opentrons.protocol_api.ProtocolContext):
    pipettes = load_attached_pipettes(protocol)
    
    for p in pipettes:
        p.pick_up_tip()

    for cross in CALIBRATION_CROSSES:
        for p in pipettes:
            location = opentrons.types.Location(opentrons.types.Point(*(cross["coordinates"])), None)
            if is_multi_channel(p.name) and cross["reach_with_front_channel"]:
                location = location.move(opentrons.types.Point(0, 9*7, 0))
            p.move_to(location)
            if (PAUSE_ON_EACH_CROSS):
                protocol.pause()
            else:
                protocol.delay(seconds=4)
    
    for p in pipettes:
        p.return_tip()