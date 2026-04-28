# screwingcell_task_and_acoustics


This program consistet of the two python scripts, one for the gui and screwdriver data, and one for the task and extrinsic (sound) data. Tor launch the program run the run.bat file.

Between the two scripts is a UDP connection, this make the gui able to specify what proccestype, woodnumber, date and pinhole is begin run

The robot data from the robot is pulish with around 115Hz, we are sampling with around 400-500Hz.


PC to robot communication is modbusTCP
Screwdriver to PC communication is Serial port
PC to PLC communication is IP/TCP (python snap7)





remeber to have open an running WSK3
use ./run.bat


There is a tab that can delete samples and one for editing sample. in the editing sample can be used to change the label of the sample.


##  Before start and getting data
* Open the WSK3 program fron weber and plug in the USB from the C30S controller
![image](https://user-images.githubusercontent.com/72868875/181718508-928cc301-6564-4261-9b72-ffca0b3669c4.png)
* Go to settings and select the right COM port
* Select then where the kxml files is going to be saved, chosse WS3 folder in the screwingcell_task_and_acoustics folder
![image](https://user-images.githubusercontent.com/72868875/181718796-60de4b94-4b70-4f86-abc3-4d9406893dc0.png)




Error Type is the type of error performed in the screwing, eks. normal screwing is A, where an anorther error is B.
Use Capital letters(example A,B,C)

Woodnumber is the number of the wood being use, every wood unit have a unique number. eks. 1 or 8.

The detecting folder is the name of the folder where WSK3 program is saveing the data(kxml files) from the C30S controller. it have to be in the same folder as this program.

The detecting folder needs to empty before starting.

An example on a name of a json file is: date8A32.json
'date' is the date
'8' is the woodnumber
'A' is the process type
'32' is the the screw number

normal is A
under is b, can you get youre finger nail under
Over is C
Over is determined by using a screwdriver to see if the treads in the wood is bad by apply only a little bit of torque
robot slip screw is S
No screw is N

New wood:
Reset PLC counter
Close convertsoftware
Close WSK3 auto transmit
restart robot program (check that modbus_5 is 0)
check if there are enough screws in the feeder
place new wood in write on top (date,woodnumber,processtype)
Start WSK3 auto transmit
start convert software and set and check (date, woodnumber, processtype) and start
Check that convert software counter is 0
