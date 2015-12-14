from ..OpenOPC.OpenOPC import *
from .hardware import format,Hardware


this_format = format + ('voltage',)
write_params = []

class ISCOOL(Hardware):
    def __init__(self):
        super(ISCOOL,self).__init__(name = 'ISCOOL',
                                  format=this_format,
                                  write_params = write_params,
                                  refresh_time=300)

        self.settings = dict()

        self.opc = None

    def connect_to_device(self):
        ######## Current readout
        pywintypes.datetime = pywintypes.TimeType # Needed to avoid some weird bug
        self.opc = client()
        self.opc.connect('National Instruments.Variable Engine.1')
        voltage = float(self.opc.read('ISCOOL.Voltage')[0])


    def read_from_device(self):
        voltage = float(self.opc.read('ISCOOL.Voltage')[0])*10000
        self.ns.status_data = {'voltage':voltage}
        return [voltage]
