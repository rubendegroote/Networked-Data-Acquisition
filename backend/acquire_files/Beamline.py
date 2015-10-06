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
        super(CRIS,self).__init__(name = 'CRIS',
                                  format=this_format,
                                  write_params = write_params)
        self.settings = dict(counterChannel="/Dev1/ctr1",  # corresponds to PFI3
                               aoChannel="/Dev1/ao0",
                               aiChannel="/Dev1/ai1,/Dev1/ai2",
                               noOfAi=2,
                               clockChannel="/Dev1/PFI1")

    def connect_to_device(self):
        self.timeout = 10.0
        maxRate = 10000.0  # Again, copied from old code

        # Create the task handles (just defines different task)
        self.aoTaskHandle = TaskHandle(0)
        self.aiTaskHandle = TaskHandle(0)

        # Creates the tasks
        DAQmxCreateTask("", byref(self.aoTaskHandle))
        DAQmxCreateTask("", byref(self.aiTaskHandle))

        # Connect the tasks to PyDAQmx stuff...
        DAQmxCreateAOVoltageChan(self.aoTaskHandle,
                    self.settings['aoChannel'],
                    "", -10,10,DAQmx_Val_Volts, None)

        DAQmxCreateAIVoltageChan(self.aiTaskHandle,
                    self.settings['aiChannel'], "",
                    DAQmx_Val_RSE, -10.0, 10.0,
                    DAQmx_Val_Volts, None)

        # Start the tasks
        DAQmxStartTask(self.aoTaskHandle)
        DAQmxStartTask(self.aiTaskHandle)

        self.no_of_ai = self.settings['noOfAi']
        self.aiData = np.zeros((self.no_of_ai,), dtype=np.float64)
        
    def write_to_device(self):
        DAQmxWriteAnalogScalarF64(self.aoTaskHandle,
                                      True, self.timeout,
                                      self.ns.setpoint, None)

    def read_from_device(self):
        DAQmxReadAnalogF64(self.aiTaskHandle,
                           -1, self.timeout,
                           DAQmx_Val_GroupByChannel, self.aiData,
                           self.no_of_ai,
                           byref(ctypes.c_long()), None)
        # Modify the gathered data, to see how many counts since the last readout
        # have registered.
        data = self.aiData

        return data
