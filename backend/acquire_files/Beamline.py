import time
import numpy as np
from PyDAQmx import *
from PyDAQmx.DAQmxConstants import *
from PyDAQmx.DAQmxFunctions import *
from ..OpenOPC.OpenOPC import *

from .hardware import format,Hardware


ini = open('beamline_config.ini','rb')
data = np.genfromtxt(ini,delimiter = '\t',dtype=str)
supply_names = list(data.T[0])
names = list(data.T[1])
output_names = list(data.T[2])
input_names = list(data.T[3])

ai_channels = ["/PXI1" + n for n in input_names]
ao_channels = ["/PXI1" + n for n in output_names]
ao_channels_1 = ["/PXI1" + n for n in output_names if 'Slot3' in n]
ao_channels_2 = ["/PXI1" + n for n in output_names if 'Slot4' in n]
aos = {'Slot3':",".join(ao_channels_1),
       'Slot4':",".join(ao_channels_2)}


this_format = format + tuple(names) + ('current',)
write_params = ['voltages']

class Beamline(Hardware):
    def __init__(self):
        super(Beamline,self).__init__(name = 'Beamline',
                                  format=this_format,
                                  write_params = write_params,
                                  refresh_time=100)

        no_of_ai = len(ai_channels)
        ais = ",".join(ai_channels)


        self.settings = dict(names=names,
                            supply_names = supply_names,
                            output_names = output_names,
                            input_names = input_names,
                            ao_channels = aos,
                            ai_channels = ais,
                            no_of_ai = no_of_ai)

        self.last_setpoints = {}
        self.ramp = 200
        self.last_time = time.time()
        self.opc = None

    def connect_to_device(self):

        ######## Current readout
        pywintypes.datetime = pywintypes.TimeType # Needed to avoid some weird bug
        self.opc = client()
        self.opc.connect('National Instruments.Variable Engine.1')
        current = float(self.opc.read('Beamline.current')[0])

        ###### voltage control
        self.timeout = 1.0
        maxRate = 10000.0  # Again, copied from old code

        self.aiTaskHandle = TaskHandle(0)
        DAQmxCreateTask("", byref(self.aiTaskHandle))
        DAQmxCreateAIVoltageChan(self.aiTaskHandle,
                    self.settings['ai_channels'], "",
                    DAQmx_Val_RSE, -10.0, 10.0,
                    DAQmx_Val_Volts, None)
        DAQmxStartTask(self.aiTaskHandle)
        self.no_of_ai = self.settings['no_of_ai']
        self.aiData = np.zeros((self.no_of_ai,), dtype=np.float64)

        self.aoTaskHandles = {}
        for slot,aos in self.settings['ao_channels'].items():
            self.aoTaskHandles[slot] = TaskHandle(0)
            DAQmxCreateTask("", byref(self.aoTaskHandles[slot]))

            DAQmxCreateAOVoltageChan(self.aoTaskHandles[slot],
                         aos,"",
                         -10,10,
                         DAQmx_Val_Volts, None)
            DAQmxStartTask(self.aoTaskHandles[slot])

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

                if time.time() - self.last_time < 1:
                    return
                else:
                    self.last_time = time.time()

                next_val = prev + self.ramp*np.sign(val-prev)
                done = False
            else:
                next_val = val
            self.last_setpoints[key] = next_val

                
        for key,handle in self.aoTaskHandles.items():
            voltages = [self.last_setpoints[n] for n in self.settings['names']]

            voltages = [v/500 if '5KV' in t else v/1000 for v,t in \
                    zip(voltages,self.settings['supply_names'])]

            voltages = np.array([v for i,v in enumerate(voltages) \
                    if key in self.settings['output_names'][i]])

            DAQmxWriteAnalogF64(handle,1,
                                True, self.timeout,DAQmx_Val_GroupByChannel,
                                voltages, byref(ctypes.c_long()),None)
        
        return done

    def read_from_device(self):
        DAQmxReadAnalogF64(self.aiTaskHandle,
                           -1, self.timeout,
                           DAQmx_Val_GroupByChannel, self.aiData,
                           self.no_of_ai,
                           byref(ctypes.c_long()), None)
        voltages = [v*500 if '5KV' in t else v*1000 for v,t in \
                zip(self.aiData,self.settings['supply_names'])]
        current = float(self.opc.read('Beamline.current')[0])
        data = voltages
        data.append(current)
        
        return data
