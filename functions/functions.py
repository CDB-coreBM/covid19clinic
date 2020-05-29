#How to activate simulator
#opentrons_simulate /Users/covid19warriors/Documents/covid19clinic/Station\ B/Station_B_S2_Aitor_JL_v1.py -L /Users/covid19warriors/Desktop/labware2

class Reagent:
    def __init__(self, name, flow_rate_aspirate, flow_rate_dispense, rinse,
                 reagent_reservoir_volume, delay, num_wells, h_cono, v_fondo,
                  tip_recycling = 'none'):
        self.name = name
        self.flow_rate_aspirate = flow_rate_aspirate
        self.flow_rate_dispense = flow_rate_dispense
        self.rinse = bool(rinse)
        self.reagent_reservoir_volume = reagent_reservoir_volume
        self.delay = delay
        self.num_wells = num_wells
        self.col = 0
        self.vol_well = 0
        self.h_cono = h_cono
        self.v_cono = v_fondo
        self.unused=[]
        self.tip_recycling = tip_recycling
        self.vol_well_original = reagent_reservoir_volume / num_wells


#Reagents and their characteristics
Ethanol = Reagent(name = 'Ethanol',
                flow_rate_aspirate = 0.5,
                flow_rate_dispense = 1,
                rinse = True,
                reagent_reservoir_volume = 12000,
                delay = 2,
                num_wells = 4, #num_Wells max is 4
                h_cono = 1.95,
                v_fondo = 1.95*7*71/2, #Prismatic
                tip_recycling = 'A1')

Beads = Reagent(name = 'Magnetic beads',
                flow_rate_aspirate = 0.5,
                flow_rate_dispense = 1,
                rinse = True,
                reagent_reservoir_volume = 12000,
                delay = 2,
                num_wells = 4,
                h_cono = 1.95,
                v_fondo = 1.95*7*71/2, #Prismatic
                tip_recycling = 'A2')

Isopropanol = Reagent(name = 'Isopropanol',
                flow_rate_aspirate = 0.5,
                flow_rate_dispense = 1,
                rinse = True,
                reagent_reservoir_volume = 5000,
                delay = 2,
                num_wells = 2, #num_Wells max is 2
                h_cono = 1.95,
                v_fondo = 1.95*7*71/2, #Prismatic
                tip_recycling = 'A3')

Water = Reagent(name = 'Water',
                flow_rate_aspirate = 1,
                flow_rate_dispense = 1,
                rinse = False,
                reagent_reservoir_volume = 6000,
                num_wells = 1, #num_Wells max is 1
                h_cono = 1.95,
                v_fondo = 1.95*7*71/2) #Prismatic

Elution = Reagent(name = 'Elution',
                flow_rate_aspirate = 0.25,
                flow_rate_dispense = 1,
                rinse = False,
                reagent_reservoir_volume = 800,
                num_wells = num_cols, #num_cols comes from available columns
                h_cono = 4,
                v_fondo = 4*math.pi*4**3/3) #Sphere

Ethanol.vol_well=Ethanol.vol_well_original()
Beads.vol_well=Beads.vol_well_original()
Isopropanol.vol_well=Isopropanol.vol_well_original()
Water.vol_well=Water.vol_well_original()
Elution.vol_well=350

beads = reagent_res.rows()[0][:Beads.num_wells] # 1 row, 4 columns (first ones)
isoprop = reagent_res.rows()[0][4:(4 + Isopropanol.num_wells)] # 1 row, 2 columns (from 5 to 6)
etoh = reagent_res.rows()[0][6:Ethanol.num_wells] # 1 row, 2 columns (from 7 to 10)
water = reagent_res.rows()[0][-1] # 1 row, 1 column (last one) full of water
work_destinations = deepwell_plate.rows()[0][:Elution.num_wells]
final_destinations = elution_plate.rows()[0][:Elution.num_wells]

tip_recycle = [ctx.load_labware('opentrons_96_tiprack_300ul', '5', '200µl filter tiprack')]

pipette.pick_up_tip(tip_recycle[reagent.tip_recycling])
pipette.return_tip()

def move_vol_multichannel(pipet, reagent, source, dest, vol, air_gap_vol, x_offset,
                   pickup_height, rinse, disp_height, blow_out, touch_tip):
    '''
    x_offset: list with two values. x_offset in source and x_offset in destination i.e. [-1,1]
    pickup_height: height from bottom where volume
    rinse: if True it will do 2 rounds of aspirate and dispense before the tranfer
    disp_height: dispense height; by default it's close to the top (z=-2), but in case it is needed it can be lowered
    blow_out, touch_tip: if True they will be done after dispensing
    '''
    # Rinse before aspirating
    if rinse == True:
        custom_mix(pipet, reagent, location = source, vol = vol,
                   rounds = 2, blow_out = True, mix_height = 0,
                   x_offset = x_offset)
    # SOURCE
    s = source.bottom(pickup_height).move(Point(x = x_offset[0]))
    pipet.aspirate(vol, s, rate = reagent.flow_rate_aspirate)  # aspirate liquid
    if air_gap_vol != 0:  # If there is air_gap_vol, switch pipette to slow speed
        pipet.aspirate(air_gap_vol, source.top(z = -2),
                       rate = reagent.flow_rate_aspirate)  # air gap
    # GO TO DESTINATION
    drop = dest.top(z = disp_height).move(Point(x = x_offset[1]))
    pipet.dispense(vol + air_gap_vol, drop,
                   rate = reagent.flow_rate_dispense)  # dispense all
    ctx.delay(seconds = reagent.delay) # pause for x seconds depending on reagent
    if blow_out == True:
        pipet.blow_out(dest.top(z = -2))
    if touch_tip == True:
        pipet.touch_tip(speed = 20, v_offset = -5)


def custom_mix(pipet, reagent, location, vol, rounds, blow_out, mix_height,
x_offset, source_height = 3):
    '''
    Function for mixing a given [vol] in the same [location] a x number of [rounds].
    blow_out: Blow out optional [True,False]
    x_offset = [source, destination]
    source_height: height from bottom to aspirate
    mix_height: height from bottom to dispense
    '''
    if mix_height == 0:
        mix_height = 3
    pipet.aspirate(1, location=location.bottom(
        z=source_height).move(Point(x=x_offset[0])), rate=reagent.flow_rate_aspirate)
    for _ in range(rounds):
        pipet.aspirate(vol, location=location.bottom(
            z=source_height).move(Point(x=x_offset[0])), rate=reagent.flow_rate_aspirate)
        pipet.dispense(vol, location=location.bottom(
            z=mix_height).move(Point(x=x_offset[1])), rate=reagent.flow_rate_dispense)
    pipet.dispense(1, location=location.bottom(
        z=mix_height).move(Point(x=x_offset[1])), rate=reagent.flow_rate_dispense)
    if blow_out == True:
        pipet.blow_out(location.top(z=-2))  # Blow out

def calc_height(reagent, cross_section_area, aspirate_volume, min_height = 0.5, extra_volume = 50):
    nonlocal ctx
    ctx.comment('Remaining volume ' + str(reagent.vol_well) +
                '< needed volume ' + str(aspirate_volume) + '?')
    if reagent.vol_well < aspirate_volume + extra_volume:
        reagent.unused.append(reagent.vol_well)
        ctx.comment('Next column should be picked')
        ctx.comment('Previous to change: ' + str(reagent.col))
        # column selector position; intialize to required number
        reagent.col = reagent.col + 1
        ctx.comment(str('After change: ' + str(reagent.col)))
        reagent.vol_well = reagent.vol_well_original
        ctx.comment('New volume:' + str(reagent.vol_well))
        height = (reagent.vol_well - aspirate_volume - reagent.v_cono) / cross_section_area
                #- reagent.h_cono
        reagent.vol_well = reagent.vol_well - aspirate_volume
        ctx.comment('Remaining volume:' + str(reagent.vol_well))
        if height < min_height:
            height = min_height
        col_change = True
    else:
        height = (reagent.vol_well - aspirate_volume - reagent.v_cono) / cross_section_area #- reagent.h_cono
        reagent.vol_well = reagent.vol_well - aspirate_volume
        ctx.comment('Calculated height is ' + str(height))
        if height < min_height:
            height = min_height
        ctx.comment('Used height is ' + str(height))
        col_change = False
    return height, col_change

def distribute_custom(pipette, volume, src, dest, waste_pool, pickup_height, extra_dispensal, disp_height=0):
    # Custom distribute function that allows for blow_out in different location and adjustement of touch_tip
    pipette.aspirate((len(dest) * volume) +
                     extra_dispensal, src.bottom(pickup_height))
    pipette.touch_tip(speed=20, v_offset=-5)
    pipette.move_to(src.top(z=5))
    pipette.aspirate(5)  # air gap
    for d in dest:
        pipette.dispense(5, d.top())
        drop = d.top(z = disp_height)
        pipette.dispense(volume, drop)
        pipette.move_to(d.top(z=5))
        pipette.aspirate(5)  # air gap
    try:
        pipette.blow_out(waste_pool.wells()[0].bottom(pickup_height + 3))
    except:
        pipette.blow_out(waste_pool.bottom(pickup_height + 3))
    return (len(dest) * volume)

def divide_volume(volume, max_vol):
    # Divide a volume in a list of smaller ones, depending on the maximum capacity of a pipette
    num_transfers=math.ceil(volume/max_vol)
    vol_roundup=math.ceil(volume/num_transfers)
    last_vol=vol-vol_roundup*(num_transfers-1)
    vol_list=[v*vol_roundup for v in range(1,num_transfers)]
    vol_list.append(last_vol)
    return vol_list

##### FLOW RATES #######
m300.flow_rate.aspirate = 150
m300.flow_rate.dispense = 300
m300.flow_rate.blow_out = 300
p1000.flow_rate.aspirate = 100
p1000.flow_rate.dispense = 1000
