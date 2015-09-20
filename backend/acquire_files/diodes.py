import socket
import time
import numpy as np
from .Helpers import try_deco
from PyDAQmx import *
from PyDAQmx.DAQmxConstants import *
from PyDAQmx.DAQmxFunctions import *

from .hardware import format,Hardware

this_format = format +  ('AIChannel1','AIChannel2','AIChannel3')

class diodes(Hardware):
    def __init__(self):
        settings = dict(aiChannel="/Dev1/ai1,/Dev1/ai2,/Dev1/ai3",
                               noOfAi=3)

        super(diodes,self).__init__(name = 'diodes',
                                  format=this_format,
                                  settings=settings)

    def connect_to_device(self):
        timeout = 10.0
        maxRate = 10000.0  # Again, copied from old code

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

        aiData = np.zeros((settings['noOfAi'],), dtype=np.float64)

        # checking if everything is OK
        DAQmxReadCounterScalarU32(self.countTaskHandle,
                    timeout,
                    byref(self.countData), None)

    def read_from_device(self):
        DAQmxReadAnalogF64(aiTaskHandle,
                           -1, timeout,
                           DAQmx_Val_GroupByChannel, aiData,
                           AIChannels,
                           byref(ctypes.c_long()), None)
        data = aiData
        
        return data

