import socket
import time
import numpy as np
from PyDAQmx import *
from PyDAQmx.DAQmxConstants import *
from PyDAQmx.DAQmxFunctions import *

from .hardware import format,BaseHardware

this_format = format +  ('Voltage_1','Voltage_2','Voltage_3','Voltage_4')
write_params = []


#### Change these if required and restart diodes device
aichannels = "/Dev1/ai1,/Dev1/ai2,/Dev1/ai3,/Dev1/ai4"
noOfAi = 4

class Hardware(BaseHardware):
    def __init__(self):
        super(Hardware,self).__init__(name = 'diodes',
                                  format=this_format)

        self.settings = dict(aiChannel=aichannels,
                               noOfAi=noOfAi)


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

