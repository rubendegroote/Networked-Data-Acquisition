import socket
import time
import numpy as np
import ctypes
from ..OpenOPC.OpenOPC import *

from .hardware import format,Hardware

this_format = format + ('setpoint','on_setpoint','wavenumber','wavenumber 2')
write_params = ['wavenumber']
class Matisse(Hardware):
    def __init__(self):      
        super(Matisse,self).__init__(name = 'Matisse',
                                     format=this_format,
                                     write_params = write_params)
       	self.opc = None
       	self.wlmdata = None

    def connect_to_device(self):
        pywintypes.datetime = pywintypes.TimeType # Needed to avoid some weird bug
        self.opc = client()
        self.opc.connect('National Instruments.Variable Engine.1')
        self.wavenumber = float(self.opc.read('Wavemeter.Setpoint')[0])/0.0299792458

        ### Wavemeter stuff
        # Load the .dll file
        self.wlmdata = ctypes.WinDLL("c:\\windows\\system32\\wlmData.dll")

        # Specify required argument types and return types for function calls
        self.wlmdata.GetFrequencyNum.argtypes = [ctypes.c_long, ctypes.c_double]
        self.wlmdata.GetFrequencyNum.restype  = ctypes.c_double

        self.wlmdata.GetExposureNum.argtypes = [ctypes.c_long, ctypes.c_long, ctypes.c_long]
        self.wlmdata.GetExposureNum.restype  = ctypes.c_long

    def write_to_device(self):
        self.opc.write(('Wavemeter.Setpoint',self.ns.setpoint*0.0299792458))

    def read_from_device(self):
        self.wavenumber = self.wlmdata.GetFrequencyNum(1,0)/0.0299792458
        wavenumber2 = self.wlmdata.GetFrequencyNum(2,0)/0.0299792458

        data = [self.wavenumber,wavenumber2]

        return data

