# This file will aim to update and customize the protocol for each sample
# run. Set the number of samples, date, register technician name and create
# the directories to run
from datetime import datetime
import os
import os.path
import pandas as pd
import string
import math
homedir=os.path.expanduser("~")
main_path = '/Volumes/opentrons/'
code_path = main_path + 'code/covid19clinic/automation/'
KF_path = code_path + 'KF_config/'
HC_path = code_path + 'HC_config/'
excel = main_path + 'barcode_template/muestras.xlsx'

# Function to distinguish between OT and KF protocols
def select_protocol_type(p1, p2):
    ff=False
    while ff==False:
        protocol=input('Introducir protocolo: \nCustom protocol (HC) o Kingfisher (KF) \nProtocolo: ')
        if protocol=='KF':
            pr=protocol
            p=p1
            ff=True
        elif protocol=='HC':
            pr=protocol
            p=p2
            ff=True
        else:
            print('Please, try again')
    return pr,p

def rep_data(n, name, f, d, run_name):
    d=d.replace('$num_samples', str(n))
    d=d.replace('$technician', '\'' + str(name) + '\'')
    d=d.replace('$date', '\'' + str(f) + '\'')
    d=d.replace('$run_id','\'' + str(run_name) + '\'')
    return d

###############################################################################
def main():

    # Read the excel file from the run and obtain the dictionary of samples
    # muestras.xlsx
    df = pd.read_excel (excel,
     sheet_name='Deepwell layout', header = None, index_col = 0)
    df = df.iloc[1:]
    df_dict = df.to_dict('index')
    merged_dict={}
    for key in df_dict:
        for key2 in df_dict[key]:
            merged_dict[str(key)+format(key2)]=df_dict[key][key2]

    # count number of declared elements in Dictionary
    num_samples_control = 0
    for elem in merged_dict.values():
        if elem != 0:
            num_samples_control += 1

    # Get sample data from user
    control=False
    while control==False:
        num_samples = int(input('Número de muestras a procesar (incluidos PC + NC): '))
        if (num_samples>0 and num_samples<=96):
            control=True
        else:
            print('Número de muestras debe ser un número entre 1 y 96')
    print('El número de muestras registradas en el excel es: '+str(num_samples_control))
    if num_samples_control!=num_samples:
        print('Error: El número de muestras entre excel y reportado no coincide')
        exit()
    else:
        print('El número de muestras coincide')

    # Get technician name
    control=False
    while control==False:
        tec_name = (input('Nombre del técnico (usuario HCP): '))
        if isinstance(tec_name, str):
            control=True
        else:
            print('Introduce tu usuario HCP, por favor')

    # Get run session ID
    control=False
    while control==False:
        id = int(input('ID run: '))
        if isinstance(id,int):
            control=True
        else:
            print('Por favor, assigna un ID numérico para éste RUN')

    # Get date
    fecha=datetime.now()
    t_registro=fecha.strftime("%m/%d/%Y, %H:%M:%S")
    dia_registro=fecha.strftime("%Y_%m_%d")

    # select the type of protocol to be run
    [protocol,protocol_path]=select_protocol_type(KF_path, HC_path)
    #determine output path
    run_name = str(dia_registro)+'_OT'+str(id)+'_'+protocol
    final_path=os.path.join(main_path+'RUNS/',run_name)

    # create folder in case it doesn't already exist and copy excel registry file there
    if not os.path.isdir(final_path):
        os.mkdir(final_path)
        os.mkdir(final_path+'/scripts')
        os.mkdir(final_path+'/results')
        os.mkdir(final_path+'/logs')
        os.system('cp ' + excel +' '+ final_path+'/OT'+str(id)+'_samples.xlsx')

    if protocol=='KF':
        file_name = 'qpcr_template_OT'+str(id)+'_'+protocol+'.txt'
        os.system('python3 '+code_path+'thermoqpcr_generate_template.py "' + final_path + '/'+ file_name+'"')
    for file in os.listdir(protocol_path): # look for all protocols in folder
        if file.endswith('.py') and 'rmarkdown' not in file:
            fin = open(protocol_path+file, "rt") # open file and copy protocol
            data = fin.read()
            fin.close()
            final_protocol=rep_data(num_samples, tec_name, t_registro, data, run_name) #replace data
            position=file.find('_',12) # find _ position after the name and get value
            filename=str(dia_registro)+'_'+file[:position]+'_OT'+str(id)+'.py' # assign a filename date + station name + id
            fout = open(os.path.join(final_path+'/scripts/',filename), "wt")
            fout.write(final_protocol)
            fout.close()
        if file.endswith('.Rmd'):
            fin = open(protocol_path+file, "rt") # open file and copy protocol
            data = fin.read()
            fin.close()
            final_protocol=data.replace('$THERUN', str(run_name))
            filename=str(dia_registro)+'_OT'+str(id)+'.Rmd' # assign a filename date + station name + id
            fout = open(os.path.join(final_path+'/scripts/',filename), "wt")
            fout.write(final_protocol)
            fout.close()

    #Calculate needed volumes and wells in stations B and C
    num_wells=math.ceil(num_samples / 32)
    bead_volume=260 * 8 * math.ceil(num_samples/8) * 1.1
    mmix_vol=(num_samples * 1.1 * 20)
    num_wells_mmix=math.ceil(mmix_vol/2000)

    #Print the information to a txt file
    f = open(final_path + '/OT'+str(id)+"volumes.txt", "wt")
    print('######### Station B ##########', file=f)
    print('Volumen y localización de beads', file=f)
    print('##############################', file=f)
    print('Es necesario un volumen mínimo de beads total de '+format(round(bead_volume,2))+ ' \u03BCl', file=f)
    print('A dividir en '+format(num_wells)+' pocillos', file=f)
    print('Volumen mínimo por pocillo: '+ format(round(bead_volume/num_wells,2))+ ' \u03BCl', file=f)
    print('######### Station C ##########', file=f)
    print('Volumen y número tubos de MMIX', file=f)
    print('###############################', file=f)
    print('Serán necesarios '+format(round(mmix_vol,2))+' \u03BCl', file=f)
    print('A dividir en '+format(num_wells_mmix), file=f)
    print('Volumen mínimo por pocillo: '+ format(round(mmix_vol/num_wells_mmix,2))+ ' \u03BCl', file=f)
    f.close()
    print('Revisa los volúmenes y pocillos necesarios en el archivo OT'+str(id)+'volumes.txt dentro de la carpeta '+run_name)

if __name__ == '__main__':
    main()

    print('Success!')
