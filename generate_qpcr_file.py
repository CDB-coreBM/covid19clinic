

file_path='/Users/covid19warriors/Downloads/run9999.txt'

f = open(file_path,'r')
for line in f:
    print(line)


for line in fileinput.input("/Users/covid19warriors/Downloads/run9999.txt", inplace=True):
    print('{} {}'.format(fileinput.filelineno(), line), end='') # for Python 3
    # print "%d: %s" % (fileinput.filelineno(), line), # for Python 2


fin = open("/Users/covid19warriors/Downloads/TaqPath%20COVID-19%20Kit%20Template%20v1-1_data.txt")
fout = open("b.txt", "wt")
for line in fin:
    fout.write(line.replace('A1\t', 'A1\tsample'))
fin.close()
fout.close()
