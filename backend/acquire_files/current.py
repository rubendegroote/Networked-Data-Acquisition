import time
import numpy as np
import visa
from collections import OrderedDict
from .hardware import format,Hardware

this_format = format + ('current','cup_in')
write_params = []

class Current(Hardware):
    def __init__(self):
        super(Current,self).__init__(name = 'Current',
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
        rm = visa.ResourceManager()
        self.switch = rm.open_resource('GPIB0::15::INSTR')
        self.switch.write('*RST')

        self.config = OrderedDict()
        with open('switcher_config','r') as f:
            for i,line in enumerate(f.readlines()):
                name, relay, switch = [x.strip() for x in line.split(',')]
                self.config[name] = [relay, switch]
        status_data = {}
        status_data['cup_names'] = list(self.config.keys())
        self.ns.status_data = status_data

        self.cup = self.ns.status_data['cup_names'][0]
        self.cup_in = 0

    def read_from_device(self):
        current = float(self.inst.query("READ?").split(',')[0].strip('A'))

        status_data['cup_names'] = list(self.config.keys())
        status_data['cup_in'] = self.cup_in
        self.ns.status_data = status_data

        return [current]

    def switch_cup(self,cup):
        print('switching cup')
        self.cup_in = False
        self.cup = cup['cup']
        self.switch.write(":open all")

        ch_switch=self.config[cup,1]

        if int(ch_switch[0]) == 0:
            self.none=0
            self.cup_in = int(self.view_cup())
        else:
            self.none=1
            if int(ch_switch[0]) == 2: self.switch.write(":close (@ 1!10)")
            self.switch.write(":close (@ "+ch_switch+")")
            self.cup_in = int(self.view_cup())

    def view_cup(self):
        cup=self.cup
        ch_switch=self.config[cup,1]

        if int(ch_switch[0]) == 0:
            reply=self.none
        else:
            reply = self.switch.query(":open? (@ "+ch_switch+")")
            reply = reply.strip('\n').strip('\r')

        return reply
