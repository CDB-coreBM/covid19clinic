opentrons_simulate /Users/covid19warriors/Documents/covid19clinic/Station\ B/Station_B_S2_Aitor_JL_v1.py -L /Users/covid19warriors/Desktop/labware2


class Reagent():
    def __init__(self,name,flow_rate_aspirate,flow_rate_dispense,rinse):
        self.name=name
        self.flow_rate_aspirate=flow_rate_aspirate
        self.flow_rate_dispense=flow_rate_dispense
        self.rinse=rinse

Ethanol=Reagent('Ethanol',150,300,True)
Beads=Reagent('Magnetic beads',150,300,True)
Isopropanol=Reagent('Isopropanol',150,300,True)
Water=Reagent('Water',150,300,False)
Elution=Reagent('Elution',25,200,False)



def mix_custom


def move_vol_multi(pipet, reagent, source, dest, vol, air_gap_vol, x_offset,
pickup_height, touch_tip):
    # SOURCE
    s = source.bottom(pickup_height).move(Point(x = x_offset))
    pipet.move_to(s) # go to source
    pipet.aspirate(vol, s) # aspirate liquid
    if air_gap_vol !=0: #If there is air_gap_vol, switch pipette to slow speed
        pipet.move_to(source.top(z = -2), speed = 20)
        pipet.aspirate(air_gap_vol, source.top(z = -2), rate = reagent.flow_rate_aspirate) #air gap

    # GO TO DESTINATION
    pipet.move_to(dest.top())
    pipet.dispense(vol + air_gap_vol + 20, dest.top(z = -1), rate = reagent.flow_rate_dispense) #dispense all
    pipet.blow_out(dest.top(z = -1)) # Blow out
    if air_gap_vol != 0:
        pipet.move_to(dest.top(z = -2), speed = 20)
        pipet.aspirate(air_gap_vol,dest.top(z = -2),rate = reagent.flow_rate_aspirate) #air gap
    # Touch tip
    if touch_tip == True:
        pipet.touch_tip(speed = 20, radius = 1.05)
