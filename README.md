# covid19clinic

Current global pandemic due to the SARS-COVID19 have struggled and pushed the limits of global health systems. Supply chain disruptions and scarce availability of RNA extraction kits have motivated worldwide actors to do research on virus detection systems.

The NGO ***COVIDwarriors*** made a donation to multiple hospitals in Spain to automatize the PCR testing of SARS-cov2 by equiping them with opensource programmable robots, developed by the US company ***Opentrons***. They also collaborated in the installation and setup by providing one engineer.
The [CORE biologia molecular](http://cdb.hospitalclinic.org/laboratorios/laboratorio_core_bm/en_index/) from ***Centre de Diagnòstic Biomèdic (CDB)***, within the ***Hospital Clínic de Barcelona*** have developed an automated method to extract RNA using these opensource robots. This methodology does not rely on the use of any commercial kits, as it implements a custom protocol using commonly available reactives. [cite original protocol here]. These robots will prepare the already inactivated samples for their analysis with a qPCR equipment, *Polymerase Chain Reaction*.

One working unit is composed by 4 multidispensing robots divided in 3 different stations named A, B, and C. Each of the stations perform different actions as described below:

- **Station A**: This station does a sample setup. Original samples are distributed in 4 racks of 24 samples each. The samples are redistributed in a 96 deepwell plate and a control reactive is added to each well.

- **Station B**: RNA extraction procedure using magnetic microbeads and transfer to a 96 well elution plate .

- **Station C**: The qPCR plate is prepared by adding 5µl of the sample from the elution plate and 24.6µl of a custom mastermix.

