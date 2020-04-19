# covid19clinic

Current global pandemic due to the SARS-COVID19 have struggled and pushed the limits of global health systems. Supply chain disruptions and scarce availability of RNA extraction kits have motivated  worldwide actors to do research on virus detection systems.  

The NGO ***COVIDwarriors*** made a proposal to multiple hospitals in Spain to develop a home made protocol to extract the RNA from patient samples without using any commercial standard kits. COVIDWarriors, under collaboration with the ***Hospital Clinic de Barcelona*** and ***Centre de Diagnostic de Barcelona*** research group have developed an automated method to extract RNA using some opensource robots developed by the US company ***Opentrons***. These robots will prepare the already inactivated samples for their study with a PCR equipment, *Polymerase Chain Reaction*.

The equipment is composed by 4 multidispensing robots divided in 3 different stations named A, B and C. Each of the stations will carry different assignments as described below:

- **Station A**: in this station the sample tubes will be redistributed in a 96 deepwell plate and add a control reactive to each of them, which later on will go to station B.

- **Station B**: samples will go under a RNA extraction procedure using magnetic microbeads and will be transferred to a different 96 well plate.

- **Station A**: this step aims to prepare the qPCR plate by adding 5µl of the sample to 24.6µl of a home prepared starter.
