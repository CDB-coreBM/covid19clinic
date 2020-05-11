import pandas as pd
import string
import os

input_file = "/home/jl/Documentos/code/covid19clinic/Kingfisher_protocols/KF_qpcr_scripts/qpcr_kf_template.txt"
out_file = "/home/jl/Documentos/code/covid19clinic/Kingfisher_protocols/KF_qpcr_scripts/qpcr_kf_file_test4.txt"

#Read the excel file from the run and obtain the dictionary of samples
#df = pd.read_excel (r'/run/user/1003/gvfs/smb-share:server=cscfs2,share=usr2/USERS/COREBM/OPENTRONS/RUNS/2020_04_28_RUN_PROVA/2020_04_28_RUN_PROVA.xls',
 #sheet_name='Deepwell layout', header = None, index_col = 0)

df = pd.read_excel (r'/run/user/1003/gvfs/smb-share:server=cscfs2,share=usr2/USERS/COREBM/OPENTRONS/barcode_template/muestras.xlsx',
  sheet_name='Deepwell layout', header = None, index_col = 0)
df = df.iloc[1:]
df_dict = df.to_dict('index')
merged_dict={}
for key in df_dict:
    for key2 in df_dict[key]:
        merged_dict[str(key)+format(key2)]=df_dict[key][key2]

#input file
fin = open(input_file, "rt")
#output file to write the result to
fout = open(out_file+'_temp', "wt")
#for each line in the input file

for line in fin:
	#read replace the string and write to output file
    if line[0] in list(string.ascii_uppercase[0:8]):
        well = line.rstrip().split('\t')[0]
        if merged_dict[well] != 0 and well != 'A1' and well != 'H12':
            fout.write(line.replace(well+'\t', well+'\t'+format(merged_dict[well])))
        else:
            fout.write(line)
    else:
        fout.write(line)

#close input and output files
fin.close()
fout.close()

#Transform into windows format
WINDOWS_LINE_ENDING = b'\r\n'
UNIX_LINE_ENDING = b'\n'
contents = open(out_file+'_temp', 'rb').read()
open(out_file, 'wb').write(contents.replace(UNIX_LINE_ENDING, WINDOWS_LINE_ENDING))
os.system('rm '+out_file+'_temp')
