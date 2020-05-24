# covid19clinic

Current global pandemic due to the SARS-COVID19 have struggled and pushed the limits of global health systems. Supply chain disruptions and scarce availability of RNA extraction kits have motivated worldwide actors to do research on virus detection systems.

The NGO ***COVIDwarriors*** made a donation to multiple hospitals in Spain to automatize the PCR testing of SARS-cov2 by equiping them with opensource programmable robots, developed by the US company ***Opentrons***. They also collaborated in the installation and setup by providing one engineer.
Here, at the [CORE biologia molecular](http://cdb.hospitalclinic.org/laboratorios/laboratorio_core_bm/en_index/) from ***Centre de Diagnòstic Biomèdic (CDB)***, within the ***Hospital Clínic de Barcelona*** we have developed an automation system to perform *Polymerase Chain Reaction* (PCR) tests using these opensource robots. These robots prepare already inactivated samples for their analysis with a qPCR equipment.

Most importantly, we have created a framework by providing a template, custom functions, and other support code to help others implement similar systems faster than we did. With it, is relatively easy to create a new station from scratch or to adapt an existing one to a change in the experimental protocol or perform fine adjustements.

We demonstrate its use by providing fully functional and tested code for Thermo-KingFisher, using this robot for the extraction step.

We are currently developing more automated protocols, including a homebrew protocol. The extraction step does not rely on the use of any commercial kits, as it implements a custom protocol using commonly available reactives. [cite original protocol here]. 


**Folder structure**
- *Custom labware:* contains the .json files with definitions for all the labware we have defined so far along with measures and pictures for some of them.
- *Homebrew_protocol:*
- *Kingfisher_protocols:*
- *automation*:
- *general_scripts:*
- *labware_simulate:* when simulating protocols a folder containing only .json files is needed. This is a copy of custom labware, containing only such files.
- *protocol_diagrams:*

