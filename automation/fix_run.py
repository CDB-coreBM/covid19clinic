import pandas as pd

import string
import os
import os.path
import sys

homedir=os.path.expanduser("~")
out_file='test.txt'
main_path='/run/user/1003/gvfs/smb-share:server=opn.cdb.nas.csc.es,share=opentrons/'
code_path = main_path + '/code/covid19clinic/automation/'
input_file = main_path + '/code/fix_run/2020_05_19_OT6_KF_Presence Absence Result.csv'

excel= main_path + 'code/fix_run/OT6_samples.xlsx'
#Read the excel file from the run and obtain the dictionary of samples
df = pd.read_excel (excel, sheet_name='Deepwell layout', header = None, index_col = 0)
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
    if line[0] != '#' and line[1]!='W':
        well = line.rstrip().split(',')[1].strip('"')
        if merged_dict[well] != 0 and well != 'A1' and well != 'H12':
            fout.write(line.replace(well+'",', well+'","'+format(merged_dict[well])+'",'))
            print 'here'
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
#os.system('rm '+out_file+'_temp')
