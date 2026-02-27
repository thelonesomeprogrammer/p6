import pandas as pd
from datetime import datetime
from pyModbusTCP.client import ModbusClient
import os
import time
import snap7
from snap7.types import *
from snap7.util import *
import threading

#wood = input("Enter wood number: ")
wood = 10
#process = input("Enter the process type: ")
process = 'A'
today = datetime.today().strftime('%d%m%Y')


# Function that provides the signal for the start of the screwdriving and connects to modbus_______________

def PLCsignal(db_number, start_offset, bit_offset):
    reading = client.db_read(db_number, start_offset, 1)
    a = snap7.util.get_bool(reading, 0, bit_offset)
    return a


try:
    client = snap7.client.Client()
    client.connect('172.20.1.148', 0, 1)
    db_number = 19
    start_offset = 0
    bit_offset = 0

    if client.get_connected():
        print("connected")
    else:
        print("could not connect to PLC")

except Exception as e:
    print("could not connect to PLC:", e)



#_________________________________________________________________________________________________________



class ModbusReader(threading.Thread):
    def __init__(self, host, port, registers):
        threading.Thread.__init__(self)
        self.daemon = True
        self.c = ModbusClient(host=host, port=port, auto_open=True, debug=False)
        self.registers = registers
        self.register_values = {}

        self.t_modbus = 0
        self.tflag = False

    def run(self):
        while True:
            try:
                
                # Read the values of the specified registers from the UR10
                reg_TCP_x = self.c.read_holding_registers(self.registers['TCP_x'])
                reg_TCP_y = self.c.read_holding_registers(self.registers['TCP_y'])
                reg_TCP_z = self.c.read_holding_registers(self.registers['TCP_z'])
                reg_TCP_rx = self.c.read_holding_registers(self.registers['TCP_rx'])
                reg_TCP_ry = self.c.read_holding_registers(self.registers['TCP_ry'])
                reg_TCP_rz = self.c.read_holding_registers(self.registers['TCP_rz'])
                reg_Robot_I = self.c.read_holding_registers(self.registers['Robot_I'])

                # Store the register values in a dictionary
                self.register_values = {
                    'TCP_x': reg_TCP_x[0],
                    'TCP_y': reg_TCP_y[0],
                    'TCP_z': reg_TCP_z[0],
                    'TCP_rx': reg_TCP_rx[0],
                    'TCP_ry': reg_TCP_ry[0],
                    'TCP_rz': reg_TCP_rz[0],
                    'Robot_I': reg_Robot_I[0]
                }
            except Exception as e:
                print("Error reading register values:", e)


    def get_register_values(self):
        return self.register_values
    
    def get_times(self):
        self.tflag = False
        value = self.t_modbus
        self.t_modbus = 0
        return value

    def set_times(self):
        self.tflag = True


# Connect to Modbus
try:
    c = ModbusClient(host='172.20.1.50', port=502, auto_open=True, debug=False)
    print("connected",c.open())
except ValueError:
    print("Error with host or port params")

# Setting up the task data parameters
registers = {
    'TCP_x': 400,
    'TCP_y': 401,
    'TCP_z': 402,
    'TCP_rx': 403,
    'TCP_ry': 404,
    'TCP_rz': 405,
    'Robot_I': 450
}



# Create a ModbusReader thread and start it
modbus_reader = ModbusReader('172.20.1.50', 502, registers)
modbus_reader.start()

#function for unsigned integers
def unsigned(a):
    if a > 32767:
        a = a - 65535
    else:
        a = a
    return a

#________________________________________________________________________________________
"""
Main loop that monitors the PLC signal and decides when will the data be recorded and where will it be saved.
"""

# Set up the variables for the PLC signal monitoring
flag = False
counter = 1
ext_dir = os.getcwd()+'\data'
directory = os.path.expanduser(ext_dir)

gui_info = 0
# Start the main loop
while True:
    start_time_loop = time.time()
    result = PLCsignal(db_number, start_offset, bit_offset)

    if result and not flag:
        flag = True
        start_time = datetime.now()
        data = []
    
    register_values = modbus_reader.get_register_values()
    
    # If the flag is True, record audio until the PLC signal goes back to False
    if flag:
        current_time = datetime.now()
        elapsed_time = (current_time - start_time).total_seconds() * 1000
        data.append([elapsed_time, register_values['TCP_x'], register_values['TCP_y'], register_values['TCP_z'], register_values['TCP_rx'], register_values['TCP_ry'], register_values['TCP_rz'], register_values['Robot_I']])
        
        # If the PLC signal is False or if the recording has reached its maximum duration, stop recording
        if not result:
            flag = False
            counter += 1
            
            df = pd.DataFrame(data=data, columns=['Time', 'TCP_x', 'TCP_y', 'TCP_z','TCP_rx', 'TCP_ry', 'TCP_rz', 'Robot_I'])
            df = df.applymap(unsigned)
            df[['TCP_x', 'TCP_y', 'TCP_z']] = df[['TCP_x', 'TCP_y', 'TCP_z']] / 10
            df[['TCP_rx', 'TCP_ry', 'TCP_rz', 'Robot_I']] = df[['TCP_rx', 'TCP_ry', 'TCP_rz', 'Robot_I']] / 1000
            df = df.rename(columns={'Time': 'Time (ms)', 'TCP_x': 'TCP_x (mm)', 'TCP_y': 'TCP_y (mm)', 'TCP_z': 'TCP_z (mm)', 'TCP_rx': 'TCP_rx (mm)', 'TCP_ry': 'TCP_ry (mm)', 'TCP_rz': 'TCP_rz (mm)', 'Robot_I': 'Robot_I (A)'})

            filename_t = os.path.join(directory+"\\"+str(today)+str(wood), f"{today}{wood}{process}{counter}")
            df.to_csv(filename_t+".csv", index=False)
