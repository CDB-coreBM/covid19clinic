library(lubridate)
library(tidyverse)
#install.packages("kableExtra")

data_A <- read_delim("/Users/covid19warriors/Documents/code/covid19clinic/tests/Kingfisher_pathogen_wetrun/KA_SampleSetup_pathogen_time_log.txt", "\t", escape_double = FALSE, col_types = cols(execution_time = col_character()), trim_ws = TRUE)
data_A$station <- 'A: sample setup'
data_B1 <- read_delim("/Users/covid19warriors/Documents/code/covid19clinic/tests/Kingfisher_pathogen_wetrun/KB_sample_prep_pathogen_log.txt", "\t", escape_double = FALSE, col_types = cols(execution_time = col_character()), trim_ws = TRUE)
data_B1$station <- 'B1: sample prep'
data_B2 <- read_delim("/Users/covid19warriors/Documents/code/covid19clinic/tests/Kingfisher_pathogen_wetrun/KB_plate_filling_time_log.txt", "\t", escape_double = FALSE, col_types = cols(execution_time = col_character()), trim_ws = TRUE)
data_B2$station <- 'B2: plate filling'
data_C <- read_delim("/Users/covid19warriors/Documents/code/covid19clinic/tests/Kingfisher_pathogen_wetrun/KC_qPCR_time_log.txt", "\t", escape_double = FALSE, col_types = cols(execution_time = col_character()), trim_ws = TRUE)
data_C$station <- 'C: qPCR'

data<-rbind(data_A,data_B1,data_B2,data_C)

#Format time
data$Time <- parse_time(data$execution_time, "%H:%M:%OS")
#Format Steps
data$STEP <- as.numeric(data$STEP)
data$new_desc <- paste0(data$STEP,': ',data$description)

ggplot(data,aes(x=fct_reorder(fct_reorder(new_desc, STEP),station), y=Time)) + 
  geom_col(aes(fill=station)) +  theme_minimal()+
  theme(text = element_text(size=20), axis.text.x = element_text(angle = 45, hjust = 1)) + 
  xlab('Protocol Step')+
  ylab('Time in minutes')+
  scale_fill_brewer(palette = "Set1")

ggsave('/Users/covid19warriors/Documents/code/covid19clinic/tests/Kingfisher_pathogen_wetrun/kingfisher_times_test_27042020_nomix.png', height=6, width=9, plot=last_plot())

table1 <- data %>%
  group_by(station) %>%
  summarize(steps=n(),total_time=sum(as.double(Time))/60)

write.table(table1, file="/Users/covid19warriors/Documents/code/covid19clinic/tests/Kingfisher_pathogen_wetrun/table1_times.txt",row.names = FALSE, sep='\t', quote = FALSE)
