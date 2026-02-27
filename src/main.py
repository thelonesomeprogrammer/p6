from flask import Flask
from flask_cors import CORS
from threading import Thread
import atexit
import pandas as pd
from datetime import datetime
from pyModbusTCP.client import ModbusClient
import os
import time
import snap7

class collector():
    def __init__(self):
        self.running = True

        ## PLC connection
        self.client = snap7.client.Client()
        self.client.connect('172.20.1.148', 0, 1)
        self.db_number = 19
        self.start_offset = 0
        self.bit_offset = 0

        ## Modbus connection to UR10
        self.c = ModbusClient(host='172.20.1.50', port=502, auto_open=True, debug=False)

        self.flag = False

        self.registers = [
                [0, 400],
                [0, 401],
                [0, 402],
                [0, 403],
                [0, 404],
                [0, 405],
                [0, 450]
                ]

        self.cols = ['Time(ms)', 'TCP_x(mm)', 'TCP_y(mm)', 'TCP_z(mm)', 
                     'TCP_rx(mm)', 'TCP_ry(mm)', 'TCP_rz(mm)', 'Robot_I(A)']

        # Set up the variables for the PLC signal monitoring
        self.counter = 1
        ext_dir = os.getcwd()+'\data'
        self.directory = os.path.expanduser(ext_dir)

        self.data = []


    #magic conversion function
    def unsigned(self, a):
        if a > 32767:
            a = a - 65535
        else:
            a = a
        return a


    def plc_run(self):
        while self.running:
            for reg in self.registers:
                try:
                    reg[0] = self.c.read_holding_registers(reg[1])
                except Exception:
                    pass


    def run(self):
        while self.running:
            self.start_time_loop = time.time()
            reading = self.client.db_read(self.db_number, self.start_offset, 1)
            result = snap7.util.get_bool(reading, 0, self.bit_offset)

            if result and not self.flag:
                self.flag = True
                start_time = datetime.now()
                self.data = []
            
            # If the flag is True, record audio until the PLC signal goes back to False
            if self.flag:
                current_time = datetime.now()
                elapsed_time = (current_time - start_time).total_seconds() * 1000
                line = []
                line.append(elapsed_time)
                for reg in self.registers:
                    line.append(reg[0])
                self.data.append(line)
                
                # If the PLC signal is False or if the recording has reached its maximum duration, stop recording
                if not result:
                    self.flag = False
                    self.counter += 1
                    
                    df = pd.DataFrame(data=self.data, columns=self.cols)
                    df = df.applymap(self.unsigned)
                    df[['TCP_x(mm)', 'TCP_y(mm)', 'TCP_z(mm)']] /= 10
                    df[['TCP_rx(mm)', 'TCP_ry(mm)', 'TCP_rz(mm)', 'Robot_I(A)']] /= 1000

                    filename_t = os.path.join(self.directory, f"data_{self.counter}")
                    df.to_csv(filename_t+".csv", index=False)


    def stop(self):
        self.running = False

w = collector()
Thread(target=w.run).start()
Thread(target=w.plc_run).start()


# create flask app
app = Flask(__name__)
CORS(app)

# main flask page
@app.route('/')
def index():
    return "API is running"

@app.route('/data')
def get_data():
    return {"data": w.data}

## Main funcion, only initiate the Flask app
def main(args=None):
    atexit.register(w.stop) # call the function to close things properly when the server is down
    app.run(host='0.0.0.0', port=5000, debug=False)

if __name__ == '__main__':
    main()
