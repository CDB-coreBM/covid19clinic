# This file will aim to update and customize the protocol for each sample
# run. Set the number of samples, date, register technician name and create
# the directories to run
from datetime import datetime
import os
import pandas as pd
import string
KF_path='/home/jl/Documentos/code/covid19clinic/Test/KF_config/'
OT_path='/home/jl/Documentos/code/covid19clinic/Test/OT_config/'

# Funtion to distinguish between OT and KF protocols
def select_protocol_type(p1,p2):
    ff=False
    while ff==False:
        protocol=input('Input type of test you would like to run: \nCustom protocol (OT) or Kingfisher (KF) \nProtocol type: ')
        if protocol=='KF':
            pr=protocol
            p=p1
            ff=True
        elif protocol=='OT':
            pr=protocol
            p=p2
            ff=True
        else:
            print('Please, try again')
    return pr,p

def rep_data(n,name,f,d):
    d=d.replace('$num_samples',str(n))
    d=d.replace('$technician','\''+str(name)+'\'')
    d=d.replace('$date','\''+str(f)+'\'')
    return d

###############################################################################
def main():

    #Read the excel file from the run and obtain the dictionary of samples
    df = pd.read_excel (r'/home/jl/Documentos/code/covid19clinic/Test/2020_04_28_RUN_PROVA/2020_04_28_RUN_PROVA.xls',
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

    print('Number of samples registered in control excel file: '+str(num_samples_control))

    control=False
    # Get sample data from user
    while control==False:
        num_samples = int(input('Numero de muestras a declarar: '))
        if (num_samples>0 and num_samples<=96):
            control=True
        else:
            print('Sample number must be between 1 and 96')

    control=False
    # Get technician name
    while control==False:
        tec_name = (input('Nombre del tecnico: '))
        if isinstance(tec_name,str):
            control=True
        else:
            print('Your name, please')

    control=False

    # Get run session ID
    while control==False:
        id = int(input('ID run: '))
        if isinstance(id,int):
            control=True
        else:
            print('Please, assing a numeric ID for this run')
    # Get date
    fecha=datetime.now()
    t_registro=fecha.strftime("%m/%d/%Y, %H:%M:%S")
    dia_registro=fecha.strftime("%m_%d_%Y")

    # select the type of protocol to be run
    [protocol,protocol_path]=select_protocol_type(KF_path,OT_path)
    #determine output path
    final_path=os.path.join('/home/jl/Documentos/code/covid19clinic/Test/',str(dia_registro)+'_ID_'+str(id)+'_prueba')

    # create folder in case it doesn't already exist and copy excel registry file there
    if not os.path.isdir(final_path):
        os.mkdir(final_path)
        os.system('cp /home/jl/Documentos/code/covid19clinic/2020_04_28_RUN_PROVA/2020_04_28_RUN_PROVA.xls '+final_path+'/2020_04_28_RUN_PROVA.xls')

    for file in os.listdir(protocol_path): # look for all protocols in folder
        if file.endswith('.py'):
            fin = open(protocol_path+file, "rt") #open file and copy protocol
            data = fin.read()
            fin.close()
            final_protocol=rep_data(num_samples, tec_name, t_registro, data) #replace data
            position=file.find('_',12) # find _ position after the name and get value
            filename=str(dia_registro)+'_'+file[:position]+'_'+str(id)+'.py' # assign a filename date + station name + id
            fout = open(os.path.join(final_path,filename), "wt")
            fout.write(final_protocol)
            fout.close()

if __name__ == '__main__':
    main()
    print('Success!')
