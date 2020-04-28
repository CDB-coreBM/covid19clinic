from opentrons import protocol_api

metadata = {'apiLevel': '2.0'}
height = 17

def run(protocol):
  magdeck = protocol.load_module('magdeck','4')
  magplate = magdeck.load_labware('nunc_96_wellplate_2000ul')
  magdeck.disengage()
  magdeck.engage(height=height)
