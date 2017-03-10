from .hardware import format,BaseHardware
import numpy as np
import time

this_format = format + ('wavenumber_1','Counts')
write_params = []

class Hardware(BaseHardware):
    def __init__(self):
        super(Hardware,self).__init__(name = 'test2',
                                  format=this_format,
                                  write_params = write_params,
                                  refresh_time=100)

    def read_from_device(self):
        x = 12815+0.1*np.random.normal()
        y=7*np.exp(-(x-12815)**2 / 2 / 0.05**2)
        return [x, np.abs(np.random.normal(y,np.sqrt(np.abs(7*np.exp(-(x-12815)**2 / 2 / 0.1**2))+1))).astype(int)]