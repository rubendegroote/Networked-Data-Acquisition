from .hardware import format,BaseHardware
import numpy as np

this_format = format + ('testing3_1','testing3_2','testing3_3')
write_params = []

class Hardware(BaseHardware):
    def __init__(self):
        super(Hardware,self).__init__(name = 'test3',
                                  format=this_format,
                                  write_params = write_params,
                                  refresh_time=100)

    def read_from_device(self):
        data1 = np.array([1,4])
        data2 = np.array([2,5])
        data3 = np.array([3,6])
        return np.column_stack((np.array(data1),np.array(data2),np.array(data3)))