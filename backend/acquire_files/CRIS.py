import socket
import time
import numpy as np
from PyDAQmx import *
from PyDAQmx.DAQmxConstants import *
from PyDAQmx.DAQmxFunctions import *

from .hardware import format,BaseHardware

this_format = format + ('Counts',)
write_params = []

class Hardware(BaseHardware):
    def __init__(self):
        super(Hardware,self).__init__(name = 'cris',
                                  format=this_format,
                                  write_params = write_params,
                                  refresh_time = 0)
        self.settings = dict(counterChannel="/Dev1/ctr1",  # corresponds to PFI3
                               aoChannel="/Dev1/ao0",
                               aiChannel="/Dev1/ai1,/Dev1/ai2",
                               noOfAi=2,
                               clockChannel="/Dev1/PFI1")

    def connect_to_device(self):
        self.timeout = 10.0
        maxRate = 10000.0  # Copied from old code

        # Create the task handles (just defines different task)
        self.countTaskHandle = TaskHandle(0)
##        self.aoTaskHandle = TaskHandle(0)
##        self.aiTaskHandle = TaskHandle(0)

        # Creates the tasks
        DAQmxCreateTask("", byref(self.countTaskHandle))
##        DAQmxCreateTask("", byref(self.aoTaskHandle))
##        DAQmxCreateTask("", byref(self.aiTaskHandle))

        # Connect the tasks to PyDAQmx stuff...
        DAQmxCreateCICountEdgesChan(self.countTaskHandle,
                    self.settings['counterChannel'], "",
                    DAQmx_Val_Falling, 0, DAQmx_Val_CountUp)

        DAQmxCfgSampClkTiming(self.countTaskHandle,
                    self.settings['clockChannel'],
                    maxRate, DAQmx_Val_Falling,
                    DAQmx_Val_ContSamps, 1)

##        DAQmxCreateAOVoltageChan(self.aoTaskHandle,
##                    self.settings['aoChannel'],
##                    "", -10,10,DAQmx_Val_Volts, None)
##
##        DAQmxCreateAIVoltageChan(self.aiTaskHandle,
##                    self.settings['aiChannel'], "",
##                    DAQmx_Val_RSE, -10.0, 10.0,
##                    DAQmx_Val_Volts, None)

        # Start the tasks
        DAQmxStartTask(self.countTaskHandle)
##        DAQmxStartTask(self.aoTaskHandle)
##        DAQmxStartTask(self.aiTaskHandle)

        # Initialize the counters
        self.lastCount = uInt32(0)
        self.countData = uInt32(0) # the counter

##        self.no_of_ai = self.settings['noOfAi']
##        self.aiData = np.zeros((self.no_of_ai,), dtype=np.float64)
        
        # checking if everything is OK
        DAQmxReadCounterScalarU32(self.countTaskHandle,
                    self.timeout,
                    byref(self.countData), None)


    def write_to_device(self):
##        DAQmxWriteAnalogScalarF64(self.aoTaskHandle,
##                                      True, self.timeout,
##                                      self.setpoint, None)
        pass
        return True

    def read_from_device(self):
        DAQmxReadCounterScalarU32(self.countTaskHandle,
                                  self.timeout,
                                  byref(self.countData), None)
##        DAQmxReadAnalogF64(self.aiTaskHandle,
##                           -1, self.timeout,
##                           DAQmx_Val_GroupByChannel, self.aiData,
##                           self.no_of_ai,
##                           byref(ctypes.c_long()), None)
        # Modify the gathered data, to see how many counts since the last readout
        # have registered.
        counts = self.countData.value - self.lastCount.value
        self.lastCount.value = self.countData.value

##        data = [self.setpoint,counts]
##        data.extend(self.aiData)
        data = [counts]

        return data
