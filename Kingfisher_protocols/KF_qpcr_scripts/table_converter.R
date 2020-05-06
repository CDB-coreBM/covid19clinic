library(tidyr)
library(dplyr)


raw_data <- read_delim("Documents/code/covid19clinic/Kingfisher_protocols/KF_qpcr_scripts/Prova2_results.csv", "\t", escape_double = FALSE, trim_ws = TRUE, skip = 7)

table1 <- raw_data %>%
  select(Well, `Sample Name`,`Target Name`,Task,Cт) %>%
  spread(key=`Target Name`, value=Cт)

sum_table <-raw_data %>%
  summarise()


