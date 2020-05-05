# covid19clinic

Current global pandemic due to the SARS-COVID19 have struggled and pushed the limits of global health systems. Supply chain disruptions and scarce availability of RNA extraction kits have motivated  worldwide actors to do research on virus detection systems.

The NGO ***COVIDwarriors*** made a donation to multiple hospitals in Spain to automatize the PCR testing of SARS-cov2 by equiping them with opensource programmable robots, developed by the US company ***Opentrons***.
 COVIDWarriors, under collaboration with the ***Hospital Clínic de Barcelona*** and the CORE biologia molecular from ***Centre de Diagnòstic Biomèdic (CDB)*** have developed an automated method to extract RNA using  these opensource robots. This methodology does not depend on the use of any kits, as it implements a custom protocol using commonly available reactives. [cite original protocol here]. These robots will prepare the already inactivated samples for their study with a PCR equipment, *Polymerase Chain Reaction*.

The equipment is composed by 4 multidispensing robots divided in 3 different stations named A, B, and C. Each of the stations will carry different assignments as described below:

- **Station A**: in this station the sample tubes will be redistributed in a 96 deepwell plate and add a control reactive to each of them, which later on will go to station B.

- **Station B**: samples will go under a RNA extraction procedure using magnetic microbeads and will be transferred to a different 96 well plate.

- **Station A**: this step aims to prepare the qPCR plate by adding 5µl of the sample to 24.6µl of a home prepared starter.

