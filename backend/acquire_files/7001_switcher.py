import time
import numpy as np
import visa
from collections import OrderedDict
from .hardware import format,BaseHardware

this_format = format
write_params = []

class Hardware(BaseHardware):
    def __init__(self):
        super(Hardware,self).__init__(name = '7001_switcher',
                                  format=this_format,
                                  write_params = write_params,
                                  refresh_time = 100)

        self.config = {}
        self.cup_status = {}
        self.cup_status_needed = False
        self.cup_to_check = None
        self.load_config()

        self.mapping = {'switch_cup':self.switch_cup}


    def load_config(self):
        sc=open(u'\\\\cern.ch\\dfs\\Users\\c\\CRIS\\Documents\\Networked-Data-Acquisition\\config\\7001_config.ini','r')
        for line in sc:
            cup, ch_switch = [x.strip() for x in line.split(',')]
            self.config[cup] = ch_switch
            self.cup_status[cup] = False

        self.cup_status_needed = True

    def connect_to_device(self):
        ### switching channels
        rm = visa.ResourceManager()
        self.switch = rm.open_resource('GPIB0::15::INSTR')
        self.switch.write(":open all")

    def switch_cup(self, args):
        cup, state = args['cup_info']
        self.switch.write(":open all")
        if state:
            # close channel
            if int(self.config[cup][0]) == 2: 
                self.switch.write(":close (@ 1!10)")
            self.switch.write(":close (@ "+self.config[cup]+")")

            self.cup_to_check = cup
        else:
            self.cup_to_check = None

        for c in self.cup_status.keys():
            self.cup_status[c] = False

        self.cup_status_needed = True

    def read_status(self):
        status_data = self.cup_status
        print(self.cup_status_needed,self.cup_to_check)
        if self.cup_status_needed and not self.cup_to_check is None:
            status_data[self.cup_to_check] = self.cup_status[self.cup_to_check]
            reply = self.switch.query(":open? (@ "+self.config[self.cup_to_check]+")")
            reply = reply.strip('\n').strip('\r') == '0'
            self.cup_status[self.cup_to_check] = reply

            self.cup_status_needed = False

        self.ns.status_data = status_data

