from .hardware import format,BaseHardware
import numpy as np

this_format = format + ('testing1_1',)
write_params = ['testing1']

class Hardware(BaseHardware):
    def __init__(self):
        super(Hardware,self).__init__(name = 'test',
                                  format=this_format,
                                  write_params = write_params,
                                  refresh_time=100)
    def read_from_device(self):
        data1 = np.array([1,4])
        data2 = np.array([2,5])
        data3 = np.array([3,6])
        data3 = np.array([4,7])
        data3 = np.array([5,8])
        return np.column_stack((np.array(data1),np.array(data2),np.array(data3)))