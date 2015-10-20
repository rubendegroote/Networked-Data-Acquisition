import time
import numpy as np
from PyDAQmx import *
from PyDAQmx.DAQmxConstants import *
from PyDAQmx.DAQmxFunctions import *

from .hardware import format,Hardware

this_format = format + ('AOV','Counts','AIChannel1','AIChannel2')
write_params = ['AOV']

class Beamline(Hardware):
    def __init__(self):
        super(Beamline,self).__init__(name = 'Beamline',
                                  format=this_format,
                                  write_params = write_params,
                                  refresh_time=100)
        self.mapping  = {'change_voltages':self.change_voltages}

        ini = open('beamline_config.ini','rb')
        data = np.genfromtxt(ini,delimiter = '\t',dtype=str)
        supply_names = data.T[0]
        names = data.T[1]
        output_names = data.T[2]
        input_names = data.T[3]

        ai_channels = ["/PXI1" + n for n in input_names]
        no_of_ai = len(ai_channels)
        ais = ",".join(ai_channels)

        self.settings = dict(names=names,
                            aoChannel="/Dev1/ao0",
                            ai_channels=ais,
                            no_of_ai=no_of_ai)

        self.voltages = []
        self.last_voltages_written = []


    def connect_to_device(self):
        self.timeout = 10.0
        maxRate = 10000.0  # Again, copied from old code

        # Create the task handles (just defines different task)
        # self.aoTaskHandle = TaskHandle(0)
        self.aiTaskHandle = TaskHandle(0)

        # Creates the tasks
        # DAQmxCreateTask("", byref(self.aoTaskHandle))
        DAQmxCreateTask("", byref(self.aiTaskHandle))

        # Connect the tasks to PyDAQmx stuff...
        # DAQmxCreateAOVoltageChan(self.aoTaskHandle,
        #             self.settings['aoChannel'],
        #             "", -10,10,DAQmx_Val_Volts, None)

        DAQmxCreateAIVoltageChan(self.aiTaskHandle,
                    self.settings['ai_channels'], "",
                    DAQmx_Val_RSE, -10.0, 10.0,
                    DAQmx_Val_Volts, None)

        # Start the tasks
        # DAQmxStartTask(self.aoTaskHandle)
        DAQmxStartTask(self.aiTaskHandle)

        self.no_of_ai = self.settings['no_of_ai']
        self.aiData = np.zeros((self.no_of_ai,), dtype=np.float64)
        
    def write_to_device(self):
        if not self.voltages == self.last_voltages_written:
            # DAQmxWriteAnalogScalarF64(self.aoTaskHandle,
            #                               True, self.timeout,
            #                               self.voltages, None)
            self.last_voltages_written = self.voltages
            print(self.voltages)
            pass

    def read_from_device(self):
        DAQmxReadAnalogF64(self.aiTaskHandle,
                           -1, self.timeout,
                           DAQmx_Val_GroupByChannel, self.aiData,
                           self.no_of_ai,
                           byref(ctypes.c_long()), None)

        self.ns.status_data = {n:d for n,d in zip(self.settings['names'],self.aiData)}

        return self.aiData

    def change_voltages(self,volts):
        print(volts)
        self.voltages = volts