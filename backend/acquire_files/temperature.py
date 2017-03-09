import time
import numpy as np
import serial

from .hardware import format,Hardware

this_format = format + ('temperature',)
write_params = []

class Temperature(Hardware):
    def __init__(self):
        super(Temperature,self).__init__(name = 'Temperature',
                                  format=this_format,
                                  write_params = write_params,
                                  refresh_time=1000)

    def connect_to_device(self):
        ######## Current readout
        self.ser = serial.Serial(
				port='COM4',
				baudrate=9600.,
				parity=serial.PARITY_NONE,
				stopbits=serial.STOPBITS_ONE,
				bytesize=serial.EIGHTBITS
				)
        command = "*IDN?"
        print(self.write(command))

    def write(self,command):
        # print(command)
        command = bytes(command + '\r\n','utf-8')
        self.ser.write(command)

        return self.get_reply()

    def get_reply(self):
        # let's wait 0.one second before reading output (let's give device time to answer)
        time.sleep(0.1)
        out = ''
        while self.ser.inWaiting() > 0:
                out += self.ser.read(1).decode('utf-8')

        return out
        
    def read_from_device(self):
        cont = True
        while cont:
            try:
                command = ":MEAS:TEMP?"
                temperature = float(self.write(command).strip('+'))
                cont = False
            except:
                time.sleep(1)
        print(temperature) 
        return [temperature]

