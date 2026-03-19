import eventlet
from flask import Flask
from flask_cors import CORS
from flask_socketio import SocketIO
from threading import Thread
import atexit
import pandas as pd
from datetime import datetime
from pyModbusTCP.client import ModbusClient
import os
import time
import snap7


eventlet.monkey_patch()

class collector():
    def __init__(self, client=None, c=None):
        self.running = True

        self.today = datetime.today().strftime('%d%m%Y')

        ## PLC connection
        self.client = client if client else snap7.client.Client()
        self.client.connect('172.20.1.148', 0, 1)
        self.db_number = 19
        self.start_offset = 0
        self.bit_offset = 0

        ## Modbus connection to UR10
        self.c = c if c else ModbusClient(host='172.20.1.50', port=502, auto_open=True)

        self.flag = False

        self.registers = [
                [[0], 400],
                [[0], 401],
                [[0], 402],
                [[0], 403],
                [[0], 404],
                [[0], 405],
                [[0], 450]
                ]

        self.cols = ['Time(ms)', 'TCP_x(mm)', 'TCP_y(mm)', 'TCP_z(mm)', 
                     'TCP_rx(mm)', 'TCP_ry(mm)', 'TCP_rz(mm)', 'Robot_I(A)']

        # Set up the variables for the PLC signal monitoring
        self.counter = 1
        ext_dir = os.getcwd()+'/data'
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
                    val = self.c.read_holding_registers(reg[1])
                    if val is not None:
                        reg[0] = val
                except Exception:
                    pass
            
            if socketio:
                modbus_data = {}
                for i, reg in enumerate(self.registers):
                    val = self.unsigned(reg[0][0])
                    
                    if i < 3:
                        val /= 10.0
                    else:
                        val /= 1000.0
                    modbus_data[self.cols[i+1]] = val
                socketio.emit('modbus_data', modbus_data)
            
            time.sleep(0.1) # Frequency of monitoring


    def run(self):
        while self.running:
            self.start_time_loop = time.time()
            reading = self.client.db_read(self.db_number, self.start_offset, 1)
            # print(reading)
            result = snap7.util.get_bool(reading, 0, self.bit_offset)
            # print(result)

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
                    line.append(reg[0][0])
                self.data.append(line)
                # print(line)
                
                # If the PLC signal is False or if the recording has reached its maximum duration, stop recording
                if not result:
                    self.flag = False
                    self.counter += 1
                    
                    df = pd.DataFrame(data=self.data, columns=self.cols)
                    df = df.map(self.unsigned)
                    df[['TCP_x(mm)', 'TCP_y(mm)', 'TCP_z(mm)']] /= 10
                    df[['TCP_rx(mm)', 'TCP_ry(mm)', 'TCP_rz(mm)', 'Robot_I(A)']] /= 1000

                    filename_t = os.path.join(self.directory, f"data_{self.today}_{self.counter}")
                    df.to_csv(filename_t+".csv", index=False)
            
            time.sleep(0.01)


    def stop(self):
        self.running = False


# create flask app
app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

w = collector()

# main flask page
@app.route('/')
def index():
    return "API is running"

@app.route('/data')
def get_data():
    return {"data": w.data}

@socketio.on('connect')
def handle_connect():
    print('Client connected')

## Main funcion, only initiate the Flask app
def main(args=None):
    Thread(target=w.run).start()
    Thread(target=w.plc_run).start()
    atexit.register(w.stop) # call the function to close things properly when the server is down
    socketio.run(app, host='0.0.0.0', port=5000, debug=False)

if __name__ == '__main__':
    main()
