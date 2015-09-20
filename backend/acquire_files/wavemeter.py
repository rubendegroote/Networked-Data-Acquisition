import ctypes
import traceback

from .hardware import format,Hardware

this_format = format + ('wavenumber_wsu_1','wavenumber_wsu_2',
	                    'expos_12','expos_21','expos_21','expos_22')

write_params = []

class Wavemeter(Hardware):
    def __init__(self):
    	super(Wavemeter,self).__init__(name = 'Wavemeter',
                             format=this_format,
                             write_params = write_params,
                             needs_stabilization = False)


    def connect_to_device(self):
        try:
            # Load the .dll file
            self.wlmdata = ctypes.WinDLL("c:\\windows\\system32\\wlmData.dll")

            # Specify required argument types and return types for function calls
            self.wlmdata.GetFrequencyNum.argtypes = [ctypes.c_long, ctypes.c_double]
            self.wlmdata.GetFrequencyNum.restype  = ctypes.c_double

            self.wlmdata.GetExposureNum.argtypes = [ctypes.c_long, ctypes.c_long, ctypes.c_long]
            self.wlmdata.GetExposureNum.restype  = ctypes.c_long
        except:
        	raise Exception('Failed to connect to wavemeter\n',traceback.format_exc())

    def read_from_device(self):
        wavenumber_wsu_1 = self.wlmdata.GetFrequencyNum(1,0) / 0.0299792458
        wavenumber_wsu_2 = self.wlmdata.GetFrequencyNum(2,0) / 0.0299792458
        expos_11 = self.wlmdata.GetExposureNum(1,1,0)
        expos_12 = self.wlmdata.GetExposureNum(1,2,0)
        expos_21 = self.wlmdata.GetExposureNum(2,1,0)
        expos_22 = self.wlmdata.GetExposureNum(2,2,0)

        data = [wavenumber_wsu_1,wavenumber_wsu_2,expos_11,
                expos_12,expos_21,expos_22]

        self.ns.status_data = {'wavenumber_wsu_1':wavenumber_wsu_1,
                               'wavenumber_wsu_2':wavenumber_wsu_2}

        return data

