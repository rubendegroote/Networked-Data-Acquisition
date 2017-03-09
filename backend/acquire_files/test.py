from .hardware import format,BaseHardware

this_format = format + ('testing1_1',)
write_params = ['testing1']

class Hardware(BaseHardware):
    def __init__(self):
        super(Hardware,self).__init__(name = 'test',
                                  format=this_format,
                                  write_params = write_params,
                                  refresh_time=100)