import socket
import time
import numpy as np
import ctypes
from .Helpers import try_deco
from .OpenOPC.OpenOPC import *

class Matisse(Device):
    def __init__(self):
        format =  ('timestamp','scan_number','setpoint',
                        'wavenumber','wavenumber 2')
        write_param = 'wavelength'
        
        super(Matisse,self).__init__(name = 'Matisse',
                                     format=format,
                                     write_param = write_param)

    def connect_to_device(self):
        pywintypes.datetime = pywintypes.TimeType # Needed to avoid some weird bug
        opc = client()
        opc.connect('National Instruments.Variable Engine.1')
        self.wavelength = float(opc.read('Wavemeter.Setpoint')[0])/0.0299792458

        ### Wavemeter stuff
        # Load the .dll file
        wlmdata = ctypes.WinDLL("c:\\windows\\system32\\wlmData.dll")

        # Specify required argument types and return types for function calls
        wlmdata.GetFrequencyNum.argtypes = [ctypes.c_long, ctypes.c_double]
        wlmdata.GetFrequencyNum.restype  = ctypes.c_double

        wlmdata.GetExposureNum.argtypes = [ctypes.c_long, ctypes.c_long, ctypes.c_long]
        wlmdata.GetExposureNum.restype  = ctypes.c_long

    def write_to_device(self):
        opc.write(('Wavemeter.Setpoint',self.ns.setpoint))

    def read_from_device(self):
        wavenumber = wlmdata.GetFrequencyNum(1,0)/0.0299792458
        wavenumber2 = wlmdata.GetFrequencyNum(2,0)/0.0299792458

        data = [wavenumber,wavenumber2]

        return data

