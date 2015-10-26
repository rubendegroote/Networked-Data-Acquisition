import time
import numpy as np
from PyDAQmx import *
from PyDAQmx.DAQmxConstants import *
from PyDAQmx.DAQmxFunctions import *

from .hardware import format,Hardware


ini = open('beamline_config.ini','rb')
data = np.genfromtxt(ini,delimiter = '\t',dtype=str)
supply_names = list(data.T[0])
names = list(data.T[1])
output_names = list(data.T[2])
input_names = list(data.T[3])

ai_channels = ["/PXI1" + n for n in input_names]
ao_channels = ["/PXI1" + n for n in output_names]

this_format = format + tuple(ai_channels)
write_params = ['voltages']

class Beamline(Hardware):
    def __init__(self):
        super(Beamline,self).__init__(name = 'Beamline',
                                  format=this_format,
                                  write_params = write_params,
                                  refresh_time=100)

        no_of_ai = len(ai_channels)
        ais = ",".join(ai_channels)

        no_of_ao = len(ao_channels)
        aos = ",".join(ao_channels)

        self.settings = dict(names=names,
                            supply_names = supply_names,
                            ao_channels=aos,
                            no_of_ao=no_of_ao,
                            ai_channels=ais,
                            no_of_ai=no_of_ai)

        self.last_setpoints = {}
        self.ramp = 100

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
        #             self.settings['aoChannel'],"",
        #              -10,10,
        #              DAQmx_Val_Volts, None)

        DAQmxCreateAIVoltageChan(self.aiTaskHandle,
                    self.settings['ai_channels'], "",
                    DAQmx_Val_RSE, -10.0, 10.0,
                    DAQmx_Val_Volts, None)

        # Start the tasks
        # DAQmxStartTask(self.aoTaskHandle)
        DAQmxStartTask(self.aiTaskHandle)

        self.no_of_ai = self.settings['no_of_ai']
        self.aiData = np.zeros((self.no_of_ai,), dtype=np.float64)

        self.no_of_ao = self.settings['no_of_ao']
        self.aoData = np.zeros((self.no_of_ao,), dtype=np.float64)
        
    def write_to_device(self):
        done = True
        if not type(self.setpoint) == dict:
            # fix this properly later
            return

        for key,val in self.setpoint.items():
            try:
                prev = self.last_setpoints[key]
            except KeyError:
                prev = 0
            if abs(val - prev) > self.ramp:
                next_val = prev + self.ramp*np.sign(val-prev)
                done = False
            else:
                next_val = val
            self.last_setpoints[key] = next_val

        voltages = [self.last_setpoints[n] for n in self.settings['names']]
        voltages = [v/500 if '5KV' in t else v/1000 for v,t in \
                zip(voltages,self.settings['supply_names'])]
        print(voltages)
        # DAQmxWriteAnalogScalarF64(self.aoTaskHandle,
        #                           True, self.timeout,
        #                           voltages, None)
        
        return done

    def read_from_device(self):
        DAQmxReadAnalogF64(self.aiTaskHandle,
                           -1, self.timeout,
                           DAQmx_Val_GroupByChannel, self.aiData,
                           self.no_of_ai,
                           byref(ctypes.c_long()), None)
        voltages = [v*500 if '5KV' in t else v*1000 for v,t in \
                zip(self.aiData,self.settings['supply_names'])]
        self.ns.status_data = [(n,d) for n,d in zip(self.settings['names'],voltages)]

        return self.aiData
