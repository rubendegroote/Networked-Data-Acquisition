import time
import numpy as np
import serial
from collections import OrderedDict
from .hardware import format,BaseHardware

this_format = format
write_params = []

PORT_NAME="COM10"


class Hardware(BaseHardware):
    def __init__(self):
        super(Hardware,self).__init__(name = 'relay_switcher',
                                  format=this_format,
                                  write_params = write_params,
                                  refresh_time = 100)
        self.config = {}
        self.actuator_status = {}
        self.actuator_status_needed = True
        self.load_config()

        self.mapping = {'switch_actuator':self.switch_actuator}

    def load_config(self):
        sc=open(u'\\\\cern.ch\\dfs\\Users\\c\\CRIS\\Documents\\Networked-Data-Acquisition\\config\\24V_config.ini','r')
        for line in sc:
            act, num = [x.strip() for x in line.split(',')]
            self.config[act] = num
            self.actuator_status[act] = False
            if act == 'IRTurbo':
                self.actuator_status[act] = True

        self.actuator_status_needed = True

    def switch_actuator(self, args):
        actuator_info = args['actuator_info']
        for act in self.actuator_status.keys():
            on = actuator_info[act]
            if on:
                self.relay_write(self.config[act],"on") 
            else:
                self.relay_write(self.config[act],"off")

        self.actuator_status_needed = True

    def relay_write(self,relayNum,relayCmd):
        serPort = serial.Serial(PORT_NAME, 19200, timeout=1)

        if (int(relayNum) < 10):
            relayIndex = str(relayNum)
        else:
            relayIndex =  chr(55 + int(relayNum))

        serPort.write(bytes("relay "+ str(relayCmd) +" "+ relayIndex + "\n\r",'utf8'))

        serPort.close()
        return True

    def read_status(self):
        status_data = self.actuator_status
        if self.actuator_status_needed:
            for act, on in self.actuator_status.items():
                self.actuator_status[act] = self.relay_read(self.config[act])
            self.actuator_status_needed = False

        self.ns.status_data = status_data

    def relay_read(self,relayNum):
        serPort = serial.Serial(PORT_NAME, 19200, timeout=1)

        if (int(relayNum) < 10):
            relayIndex = str(relayNum)
        else:
            relayIndex = chr(55 + int(relayNum))

        serPort.write(bytes("relay read "+ str(relayIndex) + "\n\r",'utf8'))

        response = serPort.read(25).decode("utf-8")
        serPort.close()

        if(response.find("on") > 0):
            return True
        elif(response.find("off") > 0):
            return False
