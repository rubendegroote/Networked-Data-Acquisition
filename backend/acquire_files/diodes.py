import socket
import time
import numpy as np
from PyDAQmx import *
from PyDAQmx.DAQmxConstants import *
from PyDAQmx.DAQmxFunctions import *

from .hardware import format,Hardware

this_format = format +  ('AIChannel1','AIChannel2','AIChannel3')
write_params = []

class diodes(Hardware):
    def __init__(self):
        super(diodes,self).__init__(name = 'diodes',
                                  format=this_format)

        self.settings = dict(aiChannel="/Dev1/ai1,/Dev1/ai2,/Dev1/ai3",
                               noOfAi=3)

    def connect_to_device(self):
        self.timeout = 10.0

        # Create the task handle (just defines different task)
        self.aiTaskHandle = TaskHandle(0)

        # Creates the tasks
        DAQmxCreateTask("", byref(self.aiTaskHandle))

        DAQmxCreateAIVoltageChan(self.aiTaskHandle,
                    self.settings['aiChannel'], "",
                    DAQmx_Val_RSE, -10.0, 10.0,
                    DAQmx_Val_Volts, None)

        # Start the tasks
        DAQmxStartTask(self.aiTaskHandle)

        self.no_of_ai = self.settings['noOfAi']
        self.aiData = np.zeros((self.no_of_ai,), dtype=np.float64)


    def read_from_device(self):
        DAQmxReadAnalogF64(self.aiTaskHandle,
                           -1, self.timeout,
                           DAQmx_Val_GroupByChannel, self.aiData,
                           self.no_of_ai,
                           byref(ctypes.c_long()), None)
        data = self.aiData
        
        return data

