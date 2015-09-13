import socket
import time
import SolsTiScommands as comm
import numpy as np

from .device import format,Device

this_format = format + ('status', 'wavelength', 'temperature', 'temperature_status',
    'etalon_lock', 'etalon_voltage', 'ref_cavity_lock', 'resonator_voltage',
    'ecd_lock', 'ecd_voltage', 'output_monitor', 'etalon_pd_dc', 'dither')

class M2(Device):
    def __init__(self):
        write_param = 'wavelength'

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
            "Lock Reference Cavity": comm.cavity_lock,
            "Reference Cavity Lock Status": comm.cavity_lock_status,
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
                                     write_param = write_param,
                                     mapping = mapping,
                                     needs_stabilization = True)
        
        self.settings = {'host': '192.168.1.216',
                         'port':39933}

        self.wavelength=0

        print('Note: the methods below should be reworked with raise statements')

    def connect_to_device(self):
        # host,port = self.settings['host'],self.settings['port']
        # for res in socket.getaddrinfo(self.host, self.port, socket.AF_UNSPEC, socket.SOCK_STREAM):
        #     af, socktype, proto, canonname, sa = res
        #     try:
        #         self.socket = socket.socket(af, socktype, proto)
        #     except OSError as msg:
        #         print(msg)
        #         self.socket = None
        #         continue
        #     try:
        #         self.socket.connect(sa)
        #     except OSError as msg:
        #         self.socket.close()
        #         self.socket = None
        #         print(msg)
        #         continue
        #     break
        # if not self.socket is None:
        #     self.socket.sendall(json.dumps(comm.start_link()))
        #     data = self.socket.recv(1024)
        #     print(repr(data))
        # else:
        #     print('derp')
        pass

    def write_to_device(self):
        # self.socket.sendall(json.dumps(comm.move_wave_t(self.ns.setpoint)))
        # response = json.loads(self.socket.recv(1024))
        # if response['operator'] == 'move_wave_t_reply':
        #     stat = response['parameters']['status']
        #     if stat == 0:
        #         return ([0],'Wavelength tuned to {} via table tuning'.format(self.ns.setpoint))
        #     elif stat == 1:
        #         return ([1],'Command failed.')
        #     elif stat == 2:
        #         return ([1],'Wavelength out of range.')
        # elif response['operator'] == 'parse_fail':
        #     return ([1],'Parse fail: received message is "{}"'.format(str(response)))
        
        # Given that we have to stabilize, this could remain a 
        # simple pass, and the stabilization can then take over and 
        # go to the setpoint as needed. 
        # So, perhaps this can always return a fail, so that 
        # ns.on_setpoint is not set to True, so that the stabilization
        # kicks in??
        pass

    def read_from_device(self):
        # self.socket.sendall(json.dumps(comm.get_status()))
        # response = self.socket.recv(1024)
        # data = [response['parameters'][string] for string in data_channels]

        data = [np.random.rand()] * (len(self.ns.format)-3)

        return data

