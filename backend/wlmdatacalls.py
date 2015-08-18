import ctypes
import time

# Load the .dll file
wlmdata = ctypes.WinDLL("c:\\windows\\system32\\wlmData.dll")

# Specify required argument types and return types for function calls
wlmdata.GetFrequencyNum.argtypes = [ctypes.c_long, ctypes.c_double]
wlmdata.GetFrequencyNum.restype  = ctypes.c_double

wlmdata.GetExposureNum.argtypes = [ctypes.c_long, ctypes.c_long, ctypes.c_long]
wlmdata.GetExposureNum.restype  = ctypes.c_long


while True:
        # Execute function calls
        wavenumber = wlmdata.GetFrequencyNum(1, 0)/ 0.0299792458
        expos      = wlmdata.GetExposureNum(1,1,0),wlmdata.GetExposureNum(1,2,0)
        print(wavenumber)

        time.sleep(0.001*max(expos))
