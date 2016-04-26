import ctypes
import traceback

from .hardware import format,Hardware

this_format = format + ('wavenumber_1',)

write_params = []

class Wavemeter_pdl(Hardware):
    def __init__(self):

        super(Wavemeter_pdl,self).__init__(name = 'Wavemeter_pdl',
                             format=this_format,
                             write_params = write_params,
                             needs_stabilization = False,
                             refresh_time = 0.01)

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

            self.wlmdata.GetExposureNum.argtypes = [ctypes.c_long, ctypes.c_long, ctypes.c_long]
            self.wlmdata.GetExposureNum.restype  = ctypes.c_long
            self.wlmdata.Calibration.argtypes = [ctypes.c_long, ctypes.c_long,
                                    ctypes.c_double, ctypes.c_long]
            self.wlmdata.Calibration.restype  = ctypes.c_long
            
            self.wlmdata.Operation.argtypes = [ctypes.c_int]
            self.wlmdata.Operation.restype  = ctypes.c_long

        except:
            raise Exception('Failed to connect to wavemeter_pdl\n',traceback.format_exc())

    def read_from_device(self):
        wavenumber_1 = self.wlmdata.GetFrequencyNum(1,0) / 0.0299792458
##        while not wavenumber_1 > 10**4:
##            wavenumber_1 = self.wlmdata.GetFrequencyNum(1,0) / 0.0299792458

        data = [wavenumber_1]

        self.ns.status_data = {'wavenumber_1':wavenumber_1}

        return data

    def calibrate(self,args):
        pass
        #self.wlmdata.Operation(0) # stop
        #self.wlmdata.Calibration(0,3,15798.0117779,2) #calibrate
        #self.wlmdata.Operation(2) #start


