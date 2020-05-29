*Under construction*

The developed code has been structured as a step by step process, using a python dictionary, and relies on previously defined custom functions (see functions.py). They include multiple parameters in order to customise the pipetting action, as each reactive has different physical properties. Coping with different physical properties has been achieved with the definition of a general class where parameters are defined in order to modify the pipetting action. At the same time, a template has been generated according to the defined structure in order to ease the protocol writing.
Currently, custom functions need to be defined inside the "run" function in each protocol. This is a limitation from the OT2 core code. 

Template structure with examples
----------------------
**Import libraries**

**Define variables**
Variables can be defined externally. 
The first code section would prompt the user to feed in multiple parameters of the task being performed such as the number of samples, run ID, user name, reactive to be used, well geometrical shape, among others.

**Calculated variables**

**Dictionary of steps**
Already inside the run section, a dictionary where the list of steps being run is defined. 
We will navigate this dictionary during the protocol, using it to save the time log. Only steps with the execute == True will be processed.
This is interesting for debugging or resuming runs in a certain point after a problem.

**Reagents**
The following step contains the reactive and custom function definitions, where reactives are defined as classes and will include details on how to deal with them when pipetting, while the custom functions are fully parametrised in order to achieve flexibility and adaption to pipetting techniques such as rinsing, picking offsets and touching the edges of a well with the tip to avoid droplet formation.

**Define labware and pipettes**
The next section would read all the labware definitions for the used equipment within the robot and depending on the type of labware, reactive and volumes will been to get slightly adapted to the needs of the protocol.

**Executing the actual steps**
Once all definitions have been made, blocks of steps would loop within cells or columns as defined by the user. 

**Write logs and exit**
Finally, a time log output would be generated from the definitions dictionary and output to a directory.
