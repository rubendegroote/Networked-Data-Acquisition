import ctypes
import traceback
import time

from .hardware import format,BaseHardware

this_format = format + ('wavenumber_1','wavenumber_2')
write_params = []

class Hardware(BaseHardware):
    def __init__(self):

        super(Hardware,self).__init__(name = 'wavemeter',
                             format=this_format,
                             write_params = write_params,
                             needs_stabilization = False,
                             refresh_time = 10)

        self.mapping = {
                        "calibrate_wavemeter": self.calibrate
                       }

    def connect_to_device(self):
        try:
            # Load the .dll file
            self.wlmdata = ctypes.WinDLL("c:\\windows\\system32\\wlmData.dll")

            # Specify required argument types and return types for function calls
            self.wlmdata.GetFrequencyNum.argtypes = [ctypes.c_long, ctypes.c_double]
            self.wlmdata.GetFrequencyNum.restype  = ctypes.c_double

            # self.wlmdata.GetLinewidth.argtypes = [ctypes.c_long, ctypes.c_double]
            # self.wlmdata.GetLinewidth.restype  = ctypes.c_double

            self.wlmdata.GetExposureNum.argtypes = [ctypes.c_long, ctypes.c_long, ctypes.c_long]
            self.wlmdata.GetExposureNum.restype  = ctypes.c_long
            self.wlmdata.Calibration.argtypes = [ctypes.c_long, ctypes.c_long,
                                    ctypes.c_double, ctypes.c_long]
            self.wlmdata.Calibration.restype  = ctypes.c_long
            
            self.wlmdata.Operation.argtypes = [ctypes.c_int]
            self.wlmdata.Operation.restype  = ctypes.c_long

        except:
            raise Exception('Failed to connect to wavemeter\n',traceback.format_exc())
        
        wavenumber_1 = self.wlmdata.GetFrequencyNum(1,0) / 0.0299792458
        wavenumber_2 = self.wlmdata.GetFrequencyNum(2,0) / 0.0299792458

        self.ns.status_data = {'wavenumber_1':wavenumber_1,
                               'wavenumber_2':wavenumber_2}


    def read_from_device(self):
        wavenumber_1 = self.wlmdata.GetFrequencyNum(1,0) / 0.0299792458
        wavenumber_2 = self.wlmdata.GetFrequencyNum(2,0) / 0.0299792458

        idx = 0
        while wavenumber_1 == self.ns.status_data['wavenumber_1'] \
              and wavenumber_2 == self.ns.status_data['wavenumber_2'] \
              and idx<10:
            idx +=1
            wavenumber_1 = self.wlmdata.GetFrequencyNum(1,0) / 0.0299792458
            wavenumber_2 = self.wlmdata.GetFrequencyNum(2,0) / 0.0299792458
            
            time.sleep(0.001*self.ns.refresh_time)

        # expos_11 = self.wlmdata.GetExposureNum(1,1,0)
        # expos_12 = self.wlmdata.GetExposureNum(1,2,0)
        # expos_21 = self.wlmdata.GetExposureNum(2,1,0)
        # expos_22 = self.wlmdata.GetExposureNum(2,2,0)
        # print(self.wlmdata.GetLinewidth(2,0))

        data = [wavenumber_1,wavenumber_2]

        self.ns.status_data = {'wavenumber_1':wavenumber_1,
                               'wavenumber_2':wavenumber_2}

        return data

    def calibrate(self,args):
        self.wlmdata.Operation(0) # stop
        self.wlmdata.Calibration(0,3,15798.0117779,2) #calibrate
        self.wlmdata.Operation(2) #start

