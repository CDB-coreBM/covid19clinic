import math
import numpy as np

#Simulation of remaining volume in eppendorf tubes with mastermix and the calculated aspiration height

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

def calc_height(reagent, cross_section_area, aspirate_volume, min_height=0.5):
    #nonlocal ctx
    #ctx.comment('Remaining volume ' + str(reagent.vol_well) +
                #'< needed volume ' + str(aspirate_volume) + '?')
    if reagent.vol_well < aspirate_volume + 50:
        reagent.unused.append(reagent.vol_well)
        #ctx.comment('Next column should be picked')
        #ctx.comment('Previous to change: ' + str(reagent.col))
        # column selector position; intialize to required number
        reagent.col = reagent.col + 1
        #ctx.comment(str('After change: ' + str(reagent.col)))
        reagent.vol_well = reagent.vol_well_original
        #ctx.comment('New volume:' + str(reagent.vol_well))
        height = (reagent.vol_well - aspirate_volume - reagent.v_cono) / cross_section_area
                #- reagent.h_cono
        reagent.vol_well = reagent.vol_well - aspirate_volume
        #ctx.comment('Remaining volume:' + str(reagent.vol_well))
        if height < min_height:
            height = min_height
        col_change = True
    else:
        height = (reagent.vol_well - aspirate_volume - reagent.v_cono) / cross_section_area #- reagent.h_cono
        reagent.vol_well = reagent.vol_well - aspirate_volume
        #ctx.comment('Calculated height is ' + str(height))
        if height < min_height:
            height = min_height
        #ctx.comment('Used height is ' + str(height))
        col_change = False
    return height, col_change


#Defined variables
##################
total_NUM_SAMPLES = 96
air_gap_vol = 5

f=open('simulation_volumes_mmix.txt', 'w')
print('initial_samples','sample','height','tube','remaining_vol', file=f)

for simulation in range(total_NUM_SAMPLES):
    NUM_SAMPLES=simulation+1
    # Tune variables
    volume_mmix = 20  # Volume of transfered master mix
    volume_mmix_available = (NUM_SAMPLES * 1.1 * volume_mmix)  # Total volume needed
    num_wells = math.ceil(volume_mmix_available/2000)
    volume_mmix_available = volume_mmix_available + 50*num_wells
    diameter_screwcap = 8.25  # Diameter of the screwcap
    volume_cone = 50  # Volume in ul that fit in the screwcap cone
    x_offset = [0,0]
    # Calculated variables
    area_section_screwcap = (np.pi * diameter_screwcap**2) / 4
    h_cone = (volume_cone * 3 / area_section_screwcap)
    # Reagents and their characteristics
    MMIX = Reagent(name = 'Master Mix',
                      rinse = False,
                      flow_rate_aspirate = 1,
                      flow_rate_dispense = 1,
                      reagent_reservoir_volume = volume_mmix_available,
                      num_wells = math.ceil(volume_mmix_available/2000), #change with num samples
                      delay = 0,
                      h_cono = h_cone,
                      v_fondo = volume_cone  # V cono
                      )
    MMIX.vol_well = MMIX.vol_well_original
    num_col=1
    for i in range(NUM_SAMPLES):
        [pickup_height,col_change]=calc_height(MMIX, area_section_screwcap, volume_mmix)
        if col_change==True:
            num_col+=1
        print(NUM_SAMPLES, i+1, round(pickup_height,2),num_col, round(MMIX.vol_well,0), file=f)

f.close()
