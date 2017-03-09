from .hardware import format,BaseHardware
import numpy as np
import time

this_format = format + ('wavenumber_1',)
write_params = []

class Hardware(BaseHardware):
    def __init__(self):
        super(Hardware,self).__init__(name = 'test2',
                                  format=this_format,
                                  write_params = write_params,
                                  refresh_time=100)

    def read_from_device(self):
        return [12815+0.1*np.random.rand()]