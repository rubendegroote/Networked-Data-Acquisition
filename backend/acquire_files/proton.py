from ..OpenOPC.OpenOPC import *
from .hardware import format,BaseHardware

this_format = format + ('SC_bunches','SC_current_bunch',
                        'HRS_bunches','HRS_current',
                        'HRS_protons_per_pulse','HRS_protons_on')
write_params = []

class Hardware(BaseHardware):
    def __init__(self):
        super(Hardware,self).__init__(name = 'Proton info',
                                  format=this_format,
                                  write_params = write_params,
                                  refresh_time=5)

    def connect_to_device(self):
        pywintypes.datetime = pywintypes.TimeType # Needed to avoid some weird bug
        self.opc = client()
        self.opc.connect('National Instruments.Variable Engine.1')
        
        tags = ['PSBooster Overall Bunches in SC',
                'PSBooster Current Bunch Number',
                'PSBooster HRS Proton Bunches in SC',
                'PSBooster HRS Proton Current',
                'PSBooster HRS Protons Per Pulse',
                'PSBooster HRS Proton Pulse'
               ]
        tags = ['protons.'+tag for tag in tags]

        self.opc.read(tags, group = 'Proton Variables')
        variables = self.opc.read(group = 'Proton Variables')

    def read_from_device(self):
        read_back = self.opc.read(group = 'Proton Variables')
        current_pulse = read_back[1][1]
        while read_back[1][1] == current_pulse:
            read_back = self.opc.read(group = 'Proton Variables')
            time.sleep(0.001*self.ns.refresh_time)

        variables = [v[1] for v in read_back]
        if variables[-1]:
            variables[-1] = 1
        else:
            variables[-1] = 0

        self.ns.status_data = {'SC_bunches':variables[0],
                               'SC_current_bunch':variables[1],
                               'HRS_bunches':variables[2],
                               'HRS_current':variables[3],
                               'HRS_protons_per_pulse':variables[4],
                               'HRS_protons_on':variables[5]
                               }
        return variables