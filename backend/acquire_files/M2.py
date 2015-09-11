import socket
import time
import SolsTiScommands as comm
import numpy as np

class M2():
    def __init__(self):
        self.format =  ('timestamp','status', 'wavelength', 'temperature', 'temperature_status',
        'etalon_lock', 'etalon_voltage', 'ref_cavity_lock', 'resonator_voltage',
        'ecd_lock', 'ecd_voltage', 'output_monitor', 'etalon_pd_dc', 'dither')

        self.mapping = {
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

        self.host = '192.168.1.216'
        self.port = 39933

        self.ns = None

        self.wavelength=0

        self.settings = {}

    def setup(self):
        pass
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
        return ([0],"Communication with ICE-BLOC achieved.")

    def interpret(self,instr):
        if instr == 'scan':
            if self.ns.scan_parameter == 'wavelength':
                self.ns.current_position = 0
                self.ns.scanning = True
                return ([0],'Starting {} scan.'.format(self.ns.scan_parameter))
            else:
                return ([1],'{} cannot be scanned.'.format(self.ns.scan_parameter))

        elif instr == 'go_to_setpoint':
            # self.socket.sendall(json.dumps(comm.move_wave_t(841.0)))
            # response = json.loads(self.socket.recv(1024))
            # if response['operator'] == 'move_wave_t_reply':
            #     stat = response['parameters']['status']
            #     if stat == 0:
            #         return ([0],'Wavelength tuned to {} via table tuning'.format(841.0))
            #     elif stat == 1:
            #         return ([1],'Command failed.')
            #     elif stat == 2:
            #         return ([1],'Wavelength out of range.')
            # elif response['operator'] == 'parse_fail':
            #     return ([1],'Parse fail: received message is "{}"'.format(str(response)))
            if self.ns.parameter == 'wavelength':
                # go to setpoint
                return ([0],'Wavelength tuned to {} via table tuning'.format(self.ns.setpoint))
                self.ns.on_setpoint = True
            else:
                return ([1],'{} cannot be set.'.format(self.ns.parameter))

        else:
            try:
                translation = self.mapping[instr[0]](instr[1])
                return ([0],'Executed {} instruction.'.format(instr))

            except KeyError:
                return ([1],'Unknown instruction {}.'.format(instr))

    def output(self):
        if self.ns.scanning:
            if time.time() - self.ns.start_of_setpoint > self.ns.time_per_step:
                self.ns.on_setpoint = False
                if self.ns.current_position == len(self.ns.scan_array):
                    self.ns.scanning = False
                    self.ns.progress = 1.0
                    return ([0],'Stopped {} scan.'.format(self.ns.scan_parameter))
                else:
                    setpoint = self.ns.scan_array[self.ns.current_position]
                    # self.mapping["Set Wavelength"](setpoint)
                    self.wavelength = setpoint
                
                    self.ns.progress = self.ns.current_position/len(self.ns.scan_array)
                    self.ns.current_position += 1
                    self.ns.start_of_setpoint = time.time()
                    self.ns.on_setpoint = True
                    return ([0],'{} scan: setpoint reached'.format(self.ns.scan_parameter))

    def input(self):
        # self.socket.sendall(json.dumps(comm.get_status()))
        # response = self.socket.recv(1024)
        # data = [response['parameters'][string] for string in data_channels]

        now = time.time()
        # put data on the queue
        data = [now,1,self.wavelength]
        data.extend([np.random.rand()] * (len(self.ns.format)-3))

        return data

