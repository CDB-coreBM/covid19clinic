library(tidyr)
library(dplyr)
library(knitr)
run="2020_05_12_OT1_KF"
raw_data <- read_delim(paste0("/run/user/1003/gvfs/smb-share:server=opn.cdb.nas.csc.es,share=opentrons/RUNS/",run,'/results/2020_05_12_R1_Presence_Absence_Result.csv'), ",", escape_double = FALSE, trim_ws = TRUE, skip = 20)
raw_data$pos<-raw_data$Well

table1 <- raw_data %>%
  select(`Well Position`, Sample,Target,Cq, pos) %>%
  spread(key=Target, value=Cq) %>%
  mutate(Sample=ifelse(nchar(Sample)>3,substr(Sample, 4, 12),Sample)) %>%
  mutate(pos=ifelse(Sample=='PC', 0, pos)) %>%
  arrange(pos) %>%
  select(-pos)

#Reorder columns
table1 <- table1[, c(1, 2, 4, 5, 6, 3)]

#Count number of genes not undetermined
table1$pos_targets = rowSums(table1[,c('N gene','ORF1ab','S gene')] != 'Undetermined')

table1 <- table1 %>%
  mutate(interpretation = case_when(
    Sample=='PC' ~ 'control',
    Sample=='NC' ~ 'control',
    MS2=='Undetermined' ~ 'No válido',
    pos_targets >=2 ~ 'Positivo',
    MS2!='Undetermined' && pos_targets == 0 ~ 'Indetectable',

    TRUE ~ 'revisar'
  ))

table(table1[table1$interpretation != 'control',]$interpretation, pos_targets = table1[table1$interpretation != 'control',]$pos_targets)

#9 cifras, 3 primeros fuera y 2 ultimos fuera
#N gene, ORF1ab, Sgene, MS2
#NA por undetermined
#NC / PC a 1/2

#interpretation. if MS2 is undetermined, interpretation = no válido
#interpretation. elif >=2 targets (excluyendo ms2) have ct --> positivo
#si ningun target tiene ct y ms2 tiene valor --> indetectable
#else: revisar

#Tabla resumen (interpretacion)
