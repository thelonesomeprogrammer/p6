import serial
import time
import struct


class SerialMonitor:
    def __init__(self, port, baudrate):
        self.port = port
        self.baudrate = baudrate
        self.serial_connection = None

    def connect(self):
        try:
            self.serial_connection = serial.Serial(self.port, self.baudrate)
            print(f"Connected to {self.port} at {self.baudrate} baud.")
        except Exception as e:
            print(f"Failed to connect: {e}")

    def read_data(self):
        if self.serial_connection and self.serial_connection.is_open:
            try:
                while True:
                    if self.serial_connection.in_waiting > 0:
                        data = self.serial_connection.readline()
                        decoded = struct.unpack('<2sHHHBB', data)
                        print(f"Received: {decoded}")
                    time.sleep(0.1)
            except KeyboardInterrupt:
                print("Stopping serial monitor.")
            except Exception as e:
                print(f"Error reading data: {e}")
        else:
            print("Serial connection is not open.")

    def disconnect(self):
        if self.serial_connection and self.serial_connection.is_open:
            self.serial_connection.close()
            print("Disconnected from serial port.")

if __name__ == "__main__":
    monitor = SerialMonitor(port='/dev/ttyUSB0', baudrate=19200)
    monitor.connect()
    monitor.read_data()
    monitor.disconnect()
