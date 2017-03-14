import time
import numpy as np
import visa
from collections import OrderedDict
from .hardware import format,BaseHardware

this_format = format + ('current','cup_in')
write_params = []

class Hardware(BaseHardware):
    def __init__(self):
        super(Hardware,self).__init__(name = 'Current',
                                  format=this_format,
                                  write_params = write_params,
                                  refresh_time=300)

        self.mapping = {'switch_cup':self.switch_cup}

    def connect_to_device(self):

        ######## Current readout
        rm = visa.ResourceManager()
        self.inst = rm.open_resource('GPIB0::14::INSTR')
        self.inst.write("*RST")          # Return 6485/6487 to GPIB defaults.
        self.inst.write("SYST:ZCH ON")   # Enable zero check.
        self.inst.write("RANG 2e-9")     # Select the 2nA range.
        self.inst.write("INIT")          # Trigger reading to be used as zero
                                         # correction.
        self.inst.write("SYST:ZCOR:ACQ") # Use last reading taken as zero
                                         # correct value.
        self.inst.write("SYST:ZCOR ON")  # Perform zero correction.
        self.inst.write("RANG:AUTO ON")  # Enable auto range.
        self.inst.write("SYST:ZCH OFF")  # Disable zero check.
        self.inst.query("READ?")         # Trigger and return one reading.


        ######## Switcher
        # rm = visa.ResourceManager()
        # self.switch = rm.open_resource('GPIB0::15::INSTR')
        # self.switch.write('*RST')

        # self.config = OrderedDict()
        # with open('switcher_config','r') as f:
        #     for i,line in enumerate(f.readlines()):
        #         name, relay, switch = [x.strip() for x in line.split(',')]
        #         self.config[name] = [relay, switch]
        # status_data = {}
        # status_data['cup_names'] = list(self.config.keys())
        # self.ns.status_data = status_data
        # print(self.ns.status_data)
        # self.current_cup = self.ns.status_data['cup_names'][0]

    def read_from_device(self):
        current = float(self.inst.query("READ?").split(',')[0].strip('A'))
        # status_data = {}

        return [current]

    # def view_cup(self):
    #     print("checking cup")
    #     relay,ch_switch=self.config[self.current_cup]

    #     return self.switch.query(":open? (@ "+ch_switch+")").strip('\n').strip('\r')

    def switch_cup(self,cup):
        print('switching cup')
        self.current_cup = cup['cup']

        #switch relays# - make sure config is in physical seqential order..
        relays_switched=[]
        for c in self.config.keys():#turns on relays up to the chosen cup
            relay=self.config[c][1]
            if not relay in relays_switched:
                if relay == self.config[self.current_cup][1]:
                    self.relay_write(relay,"on")
                else:
                    self.relay_write(relay,"off")
                relays_switched.append(relay)
        
        for c in self.config.keys():#turns on relays up to the chosen cup
            if c == self.current_cup:
                self.switch.write(":close (@ "+self.config[c][0]+")")
            else:
                self.switch.write(":open (@ "+self.config[c][0]+")") # close 'all' might work too

    def relay_write(self,relayNum,relayCmd):
        #print("relay:",relayNum,relayCmd)
        pass
        # serPort = serial.Serial(portName, 19200, timeout=1)

        # if (int(relayNum) < 10):
        #   relayIndex = str(relayNum)
        # else:
        #   relayIndex = chr(55 + int(relayNum))

        # serPort.write("relay "+ str(relayCmd) +" "+ relayIndex + "\n\r")

        # serPort.close()
        # return True

    def relay_read(self,relayNum):
        pass
        return True

        # serPort = serial.Serial(portName, 19200, timeout=1)

        # if (int(relayNum) < 10):
        #   relayIndex = str(relayNum)
        # else:
        #   relayIndex = chr(55 + int(relayNum))

        # serPort.write("relay read "+ relayIndex + "\n\r")

        # response = serPort.read(25)
        # serPort.close()

        # if(response.find("on") > 0):
        #   #print ("Relay " + str(relayNum) +" is ON")
        #   return True

        # elif(response.find("off") > 0):
        #   #print ("Relay " + str(relayNum) +" is OFF")
        #   return False