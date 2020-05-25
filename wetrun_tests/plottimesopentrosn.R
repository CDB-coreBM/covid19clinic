library(lubridate)
library(tidyverse)
#install.packages("kableExtra")

data_A <- read_delim("/Users/covid19warriors/Documents/code/covid19clinic/Sample_tests/23_04_2020/StationA_23_04_2020.txt", "\t", escape_double = FALSE, col_types = cols(execution_time = col_character()), trim_ws = TRUE)
data_A$station <- 'A'
data_B <- read_delim("/Users/covid19warriors/Documents/code/covid19clinic/Sample_tests/23_04_2020/StationB_23_04_2020.txt", "\t", escape_double = FALSE, col_types = cols(execution_time = col_character()), trim_ws = TRUE)
data_B$station <- 'B'
data_C <- read_delim("/Users/covid19warriors/Documents/code/covid19clinic/Sample_tests/23_04_2020/StationC_23_04_2020.txt", "\t", escape_double = FALSE, col_types = cols(execution_time = col_character()), trim_ws = TRUE)
data_C$station <- 'C'


data<-rbind(data_A,data_B,data_C)

#Format time
data$Time <- parse_time(data$execution_time, "%H:%M:%OS")
#Format Steps
data$STEP <- as.numeric(data$STEP)
data$new_desc <- paste0(data$station,' - ',data$STEP,': ',data$description)

ggplot(data,aes(x=fct_reorder(fct_reorder(new_desc, STEP),station), y=Time)) + 
  geom_col(aes(fill=station)) +  theme_minimal()+
  theme(text = element_text(size=20), axis.text.x = element_text(angle = 45, hjust = 1)) + 
  xlab('Protocol Step')+
  ylab('Time in minutes')+
  scale_fill_brewer(palette = "Set1")

ggsave('station_times_test2_23042020_.png',plot=last_plot())

table1 <- data %>%
  group_by(station) %>%
  summarize(steps=n(),total_time=sum(as.double(Time))/60)

