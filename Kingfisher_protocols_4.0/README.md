**Documentation in progress**


One working unit is composed by 4 OT2 robots divided in 3 different stations named A, B1, B2, and C. 
Stations letters define a OT2 robot with a certain combination of pippettes attached, meaning the protocols can be run in the same robot. This is the case of Station B1 and B2, thus we could build this circuit using only 3 robots. Each station performs different actions as described below:

- **Station A**: This station does a sample setup. Original samples are distributed in 4 racks of 24 samples each. The samples are redistributed in a 96 deepwell plate and a control reactive is added to each well.
- **Station B1**: Plate filling
- **Station B2**: Sample preparation
- **KingFisher**: RNA extraction procedure using magnetic microbeads
- **Station C**: The qPCR plate is prepared by adding 5µl of the sample from the elution plate and 20 µl of a custom mastermix.

Station A and Station B1 can run in parallel at the same time.

The difference between **pathogen** and **viral pathogen II** is the kits that are used for the extraction procedure, with different reactives and volumes. Code for both types of kits are provided in the different folders.
