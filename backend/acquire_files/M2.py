import socket
import time
import backend.acquire_files.SolsTiScommands as comm
import numpy as np
import json
import ctypes
import traceback

from .device import format,Device

M2_format = ('status', 'wavelength', 'temperature', 'temperature_status',
    'etalon_lock', 'etalon_voltage', 'cavity_lock', 'resonator_voltage',
    'ecd_lock', 'ecd_voltage', 'output_monitor', 'etalon_pd_dc', 'dither')
this_format = format + M2_format
write_params = ['wavenumber']

class M2(Device):
    def __init__(self):
        mapping = {
            "Set Wavelength": comm.set_wave_m,
            "Poll Wavelength": comm.poll_wave_m,
            "Lock Wavelength": comm.lock_wave_m,
            "Stop Wavelength": comm.stop_wave_m,
            "Set Wavelength Tune": comm.move_wave_t,
            "Poll Wavelength Tune": comm.poll_move_wave_t,
            "Stop Wavelength Tune": comm.stop_move_wave_t,
            "Tune Etalon": comm.tune_etalon,
            "Tune Cavity": comm.tune_cavity,
            "Finetune Cavity": comm.fine_tune_cavity,
            "Tune Resonator": comm.tune_resonator,
            "Finetune Resonator": comm.fine_tune_resonator,
            "Lock Etalon": comm.etalon_lock,
            "Etalon Lock Status": comm.etalon_lock_status,
            "Lock Reference Cavity": comm.ref_cavity_lock,
            "Reference Cavity Lock Status": comm.ref_cavity_lock_status,
            "Lock ECD": comm.ecd_lock,
            "ECD Lock Status": comm.ecd_lock_status,
            "Monitor A": comm.monitor_a,
            "Monitor B": comm.monitor_b,
            "Select Etalon Profile": comm.select_profile,
            "Get Status": comm.get_status,
            "Get Alignment Status": comm.get_alignment_status,
            "Beam Alignment Mode": comm.beam_alignment,
            "Beam Alignment x": comm.beam_adjust_x,
            "Beam Alignment y": comm.beam_adjust_y,
            "Initialize Scan Stitch": comm.scan_stitch_initialise,
            "Scan Stitch": comm.scan_stitch_op,
            "Scan Stitch Status": comm.scan_stitch_status,
            "Scan Stitch Output": comm.scan_stitch_output,
            "Start Fast Scan": comm.fast_scan_start,
            "Poll Fast Scan": comm.fast_scan_poll,
            "Stop Fast Scan": comm.fast_scan_stop,
            "Stop Fast Scan Without Return": comm.fast_scan_stop_nr
        }

        super(M2,self).__init__(name = 'M2',
                                     format=this_format,
                                     write_params = write_params,
                                     mapping = mapping,
                                     needs_stabilization = True,
                                     refresh_time = 0.1)
        
        self.settings = {'host': '192.168.1.216',
                         'port':39933}

        self.wavenumber = 0
        self.cavity_value = 50.20
        self.etalon_value = 50.20

    def connect_to_device(self):

        ### Wavemeter stuff
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

        ### M2 stuff
        host,port = self.settings['host'],self.settings['port']
        for res in socket.getaddrinfo(host, port, socket.AF_UNSPEC, socket.SOCK_STREAM):
            af, socktype, proto, canonname, sa = res
            try:
                self.socket = socket.socket(af, socktype, proto)
            except OSError as msg:
                print(msg)
                self.socket = None
                continue
            try:
                self.socket.connect(sa)
            except OSError as msg:
                self.socket.close()
                self.socket = None
                print(msg)
                continue
            break
        if not self.socket is None:
            self.socket.sendall(comm.start_link())
            data = self.socket.recv(1024)
            return(data.decode('utf-8'))
        else:
            raise Exception('Failed to connect to M2')

    def write_to_device(self):
        pass

    def stabilize_device(self):
        error = self.wavenumber - self.ns.setpoint
        if not (self.ns.status_data["etalon_lock"] \
                and self.ns.status_data["cavity_lock"]):
            # etalon and cavity are not locked
            return

        if abs(error) < 0.25 and abs(error) > 10**-6:
            correction = self.prop * error
            self.cavity_value += correction
            print(self.cavity_value)
            self.socket.sendall(comm.tune_cavity(self.cavity_value))
            response = json.loads(self.socket.recv(1024).decode('utf-8'))
            self.last_stabilization = time.time()

        if not self.ns.on_setpoint and abs(error) < 5*10**-5:
            self.setpoint_reached()
            return ([0],'{} setpoint reached'.format(self.ns.scan_parameter))

    def read_from_device(self):
        self.socket.sendall(comm.get_status())
        response = json.loads(self.socket.recv(1024).decode('utf-8'))
        status_data = response['message']['parameters']       
        status_data['wavelength_lock'] = self.wavelength_lock
        status_data['etalon_value'] = self.etalon_value
        status_data['cavity_value'] = self.cavity_value
        self.ns.status_data = status_data

        self.wavenumber = self.wlmdata.GetFrequencyNum(1,0) / 0.0299792458

        data = [convert_data(self.ns.status_data[m]) for m in M2_format]

        return data

def convert_data(d):
    if d == 'on':
        return 1
    elif d == 'off' or d == 'error':
        return 0
    elif d in ['debug','search','low','not_fitted']:
        return 2
    else:
        return float(d[0])