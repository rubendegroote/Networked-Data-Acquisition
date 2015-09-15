import socket
import time
import numpy as np
from .Helpers import try_deco
from PyDAQmx import *
from PyDAQmx.DAQmxConstants import *
from PyDAQmx.DAQmxFunctions import *

from .device import format,Device

this_format = format + ('AOV','Counts','AIChannel1','AIChannel2')
write_params = ['AOV']

class CRIS(Device):
    def __init__(self):
        settings = dict(counterChannel="/Dev1/ctr1",  # corresponds to PFI3
                               aoChannel="/Dev1/ao0",
                               aiChannel="/Dev1/ai1,/Dev1/ai2",
                               noOfAi=2,
                               clockChannel="/Dev1/PFI1")
        super(CRIS,self).__init__(name = 'CRIS',
                                  format=this_format,
                                  settings=settings,
                                  write_params = write_params)

    def connect_to_device(self):
        timeout = 10.0
        maxRate = 10000.0  # Again, copied from old code

        # Create the task handles (just defines different task)
        self.countTaskHandle = TaskHandle(0)
        self.aoTaskHandle = TaskHandle(0)
        self.aiTaskHandle = TaskHandle(0)

        # Creates the tasks
        DAQmxCreateTask("", byref(self.countTaskHandle))
        DAQmxCreateTask("", byref(self.aoTaskHandle))
        DAQmxCreateTask("", byref(self.aiTaskHandle))

        # Connect the tasks to PyDAQmx stuff...
        DAQmxCreateCICountEdgesChan(self.countTaskHandle,
                    self.settings['counterChannel'], "",
                    DAQmx_Val_Falling, 0, DAQmx_Val_CountUp)

        DAQmxCfgSampClkTiming(self.countTaskHandle,
                    self.settings['clockChannel'],
                    maxRate, DAQmx_Val_Falling,
                    DAQmx_Val_ContSamps, 1)

        DAQmxCreateAOVoltageChan(self.aoTaskHandle,
                    self.settings['aoChannel'],
                    "", -10,10,DAQmx_Val_Volts, None)

        DAQmxCreateAIVoltageChan(self.aiTaskHandle,
                    self.settings['aiChannel'], "",
                    DAQmx_Val_RSE, -10.0, 10.0,
                    DAQmx_Val_Volts, None)

        # Start the tasks
        DAQmxStartTask(self.countTaskHandle)
        DAQmxStartTask(self.aoTaskHandle)
        DAQmxStartTask(self.aiTaskHandle)

        # Initialize the counters
        self.lastCount = uInt32(0)
        self.countData = uInt32(0) # the counter

        self.aiData = np.zeros((settings['noOfAi'],), dtype=np.float64)
        
        # checking if everything is OK
        DAQmxReadCounterScalarU32(self.countTaskHandle,
                    timeout,
                    byref(self.countData), None)

    def write_to_device(self):
        DAQmxWriteAnalogScalarF64(self.aoTaskHandle,
                                      True, timeout,
                                      self.ns.setpoint, None)

    def read_from_device(self):
        DAQmxReadCounterScalarU32(countTaskHandle,
                                  timeout,
                                  byref(countData), None)
        DAQmxReadAnalogF64(aiTaskHandle,
                           -1, timeout,
                           DAQmx_Val_GroupByChannel, self.aiData,
                           AIChannels,
                           byref(ctypes.c_long()), None)
        # Modify the gathered data, to see how many counts since the last readout
        # have registered.
        counts = countData.value - lastCount.value
        lastCount.value = countData.value

        data = [counts]
        data.extend(self.aiData)

        return data

