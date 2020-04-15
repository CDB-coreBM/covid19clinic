opentrons_simulate /Users/covid19warriors/Documents/covid19clinic/Station\ B/Station_B_S2_Aitor_JL_v1.py -L /Users/covid19warriors/Desktop/labware2


class Reagent:
    def __init__(self,name,flow_rate_aspirate,flow_rate_dispense,rinse,reagent_reservoir,num_wells,h_cono,v_fondo,tip_recycling='A1'):
        self.name=name
        self.flow_rate_aspirate=flow_rate_aspirate
        self.flow_rate_dispense=flow_rate_dispense
        self.rinse=bool(rinse)
        self.reagent_reservoir=reagent_reservoir
        self.num_wells=num_wells
        self.col=0
        self.vol_well=0
        self.h_cono=h_cono
        self.v_cono=v_fondo
        self.tip_recycling=tip_recycling
    def vol_well_original(self):
        return self.reagent_reservoir/self.num_wells

Ethanol=Reagent('Ethanol',0.5,1,True,12000,4,,tip_recycling='A1') #num_Wells max is 4
Beads=Reagent('Magnetic beads',0.5,1,True,12000,4,,tip_recycling='A2') #num_Wells max is 4
Isopropanol=Reagent('Isopropanol',0.5,1,True,5000,2,,tip_recycling='A3') #num_Wells max is 2
Water=Reagent('Water',1,1,False,6000,1,,) #num_Wells max is 1
Elution=Reagent('Elution',0.25,1,False,800,num_cols,,) #num_cols comes from available columns

[custom_mix(p,r,s,vol) for _ in range(5)]

def custom_mix(pipet,reagent,source,destination,vol):
    pipet.flow_rate.aspirate=reagent.flow_rate_aspirate
    pipet.aspirate(vol,source)
    pipet.flow_rate.dispense=reagent.flow_rate_dispense
    pipet.dispense(vol,destination)
    pipet.dispense(30, dest.top(z=-5))

beads = reagent_res.rows()[0][:Beads.num_wells] # 1 row, 4 columns (first ones)
isoprop = reagent_res.rows()[0][4:(4+Isopropanol.num_wells)] # 1 row, 2 columns (from 5 to 6)
etoh = reagent_res.rows()[0][6:Ethanol.num_wells] # 1 row, 2 columns (from 7 to 10)
water = reagent_res.rows()[0][-1] # 1 row, 1 column (last one) full of water
work_destinations = deepwell_plate.rows()[0][:Elution.num_wells]
final_destinations = elution_plate.rows()[0][:Elution.num_wells]

    def calc_height(reagent,cross_section_area,aspirate_volume,):
        if reagent.vol_well<aspirate_volume:
            reagent.vol_well=reagent.vol_well_original-aspirate_volume
            height=(reagent.vol_well-reagent.v_cono)/cross_section_area-reagent.h_cono
            reagent.col=reagent.col+1 # column selector position; intialize to required number
            if height<0:
                height=0.1
        else:
            height=(reagent.vol_well-reagent.v_cono)/cross_section_area-reagent.h_cono
            reagent.col=0+reagent.col
            reagent.vol_well=reagent.vol_well-aspirate_volume
            if height<0:
                height=0.1
        return height

tip_recycle = [ctx.load_labware('opentrons_96_tiprack_300ul', '5', '200µl filter tiprack')]

pipette.pick_up_tip(tip_recycle[reagent.tip_recycling])
pipette.return_tip()

def move_vol_multi(pipet, reagent, source, dest, vol, air_gap_vol, x_offset,
pickup_height, rinse):
    # Rinse before aspirating
    if rinse == True:
        [custom_mix(pipet, reagent, source, dest, vol) for _ in range(2)]
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
