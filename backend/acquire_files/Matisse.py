import socket
import time
import numpy as np
import ctypes
from ..OpenOPC.OpenOPC import *

from .hardware import format,BaseHardware

this_format = format + ('setpoint',)
write_params = ['wavenumber']
class Hardware(BaseHardware):
    def __init__(self):      
        super(Hardware,self).__init__(name = 'Matisse',
                                     format=this_format,
                                     write_params = write_params,
                                     refresh_time = 500,
                                     needs_stabilization = False)
       	
        self.mapping = {
            "change_device_prop":self.change_prop,
            "change_device_int":self.change_int,
            "change_device_diff":self.change_diff,
            "lock_device_wavelength":self.lock_wavelength
        }
        self.opc = None
       	self.wlmdata = None
        self.tolerance = 2 ##MHz
        self.prev_set = 0
        self.converged_it = 0

    def connect_to_device(self):
        pywintypes.datetime = pywintypes.TimeType # Needed to avoid some weird bug
        self.opc = client()
        self.opc.connect('National Instruments.Variable Engine.1')

        tags = ['Setpoint (THz)',
                'Difference (MHz)',
                'P',
                'I',
                'D',
                'Stabilization Active',
                'Laser Locked'
               ]
        tags = ['Matisse Control.'+tag for tag in tags]

        self.opc.read(tags,group='Matisse variables')

        data = self.read_all()

        self.difference = data['Difference (MHz)']
        self.prop = data['P']
        self.int = data['I']
        self.diff = data['D']
        self.wavelength_lock = data['Stabilization Active']

    def read_from_device(self):
        data = self.read_all()
        self.ns.status_data = data
        self.difference = self.ns.status_data['Difference (MHz)']

        if not self.ns.on_setpoint:
            if abs(data['Difference (MHz)']) < self.tolerance:
                self.converged_it += 1
                if self.converged_it == 4:
                    self.setpoint_reached()
                    self.converged_it = 0

        return [self.difference]

    def change_prop(self,args):
        self.prop = args['prop']
        self.opc.write(('Matisse Control.P',self.prop))

    def change_int(self,args):
        self.int = args['int']
        self.opc.write(('Matisse Control.I',self.int))

    def change_diff(self,args):
        self.diff = args['diff']
        self.opc.write(('Matisse Control.D',self.diff))

    def lock_wavelength(self,args):
        lock = args['lock']
        self.wavelength_lock = lock
        self.opc.write(('Matisse Control.Stabilization Active',lock))

    def write_to_device(self):
        if not self.setpoint == self.prev_set:
            self.converged_it = 0
            self.prev_set = self.setpoint
            self.opc.write(('Matisse Control.Setpoint (THz)',self.setpoint*0.0299792458))
        return False

    def read_all(self):
        wn, diff, P, I, D, A, L = self.opc.read(group='Matisse variables')
        return {'Setpoint (THz)': float(wn[1]),
                'Difference (MHz)': float(diff[1]),
                'P':P[1],
                'I':I[1],
                'D':D[1],
                'Stabilization Active': bool(A[1]),
                'Laser Locked': bool(L[1])
        }