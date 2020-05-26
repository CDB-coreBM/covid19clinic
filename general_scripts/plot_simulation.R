library(ggplot2)
simulation_volumes_mmix <- read.csv("~/Documents/simulation_volumes/simulation_volumes_mmix.txt", sep="")

data<-subset(simulation_volumes_mmix, initial_samples==96)
ggplot(data, aes(x=sample)) + 
  geom_col(aes(y=remaining_vol, fill="")) + 
  geom_col(aes(y=height*50)) + 
  scale_y_continuous(limits = c(0,2000),sec.axis = sec_axis(~./50, name = "Pickup Height in mm")) + 
  geom_hline(yintercept=50, linetype='dotted', col = 'red')+
  annotate("text", x = 24, y = 1500, label = "Screwcap 1", vjust = -0.5) + 
  annotate("text", x = 72, y = 1500, label = "Screwcap 2", vjust = -0.5) + 
  scale_fill_brewer(palette = "Set2")+
  ylab(expression("Remaining volume in " *mu*"l"))+
  xlab('Sample number')+
  theme_minimal() +
  theme(legend.position='none')



ggsave('simulated_screwcap_volume_heights.png', height=6, width=8, plot=last_plot())
