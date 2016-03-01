import time
import numpy as np
import visa

from .hardware import format,Hardware

this_format = format + ('current',)
write_params = []

class Current(Hardware):
    def __init__(self):
        super(Current,self).__init__(name = 'Current',
                                  format=this_format,
                                  write_params = write_params,
                                  refresh_time=100)


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

    def read_from_device(self):
        current = float(self.inst.query("READ?").split(',')[0].strip('A'))
       
        return [current]
