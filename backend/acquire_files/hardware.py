import socket
import time
import backend.Helpers as hp
import json

format = ('timestamp','offset','scan_number','mass')
TIME_OFFSET = 1420070400 # 01/01/2015

class Hardware():
    def __init__(self,name = 'hardware',
                      format = (),
                      settings = {},
                      ns = None,
                      write_params = 'name_of_parameter',
                      mapping = {},
                      needs_stabilization = False,
                      refresh_time = 1):

        self.name = name
        self.format = format
        self.settings = settings
        self.ns = ns
        self.write_params = write_params
        self.mapping = mapping
        self.refresh_time = refresh_time
        self.start_of_setpoint = time.time()
        self.clock_offset = 0

        self.needs_stabilization = needs_stabilization
        if needs_stabilization:
            self.wavelength_lock = False
            self.prop = 10

    def connect_to_device(self):
        # to be overridden
        pass

    def write_to_device(self):
        # to be overridden
        pass

    def read_from_device(self):
        # to be overridden
        pass

    def stabilize_device(self):
        pass

    @hp.try_deco
    def setup(self):
        self.connect_to_device()
        return ([0],"Communication with {} achieved.".format(self.name))

    @hp.try_deco
    def interpret(self,instr):
        instr_name,args = instr
        if instr_name == 'start_scan':
            self.scan_parameter = params['scan_parameter'][0]
            self.scan_array = params['scan_array']
            self.time_per_step = params['time_per_step'][0]

            if self.scan_parameter in self.write_params:
                self.current_position = 0
                self.ns.scanning = True
                return ([0],'Starting {} scan.'.format(self.scan_parameter))
            else:
                return ([1],'{} cannot be scanned.'.format(self.scan_parameter))

        elif instr_name == 'stop_scan':
            self.ns.scanning = False
            return ([0],'Stopped {} scan.'.format(self.scan_parameter))

        elif instr_name == 'go_to_setpoint':
            self.parameter = args['parameter'][0]
            self.setpoint = args['setpoint'][0]
            if self.parameter in self.write_params:
                self.on_setpoint = False
                return ([0],'{} setpoint acknowledged.'.format(self.write_params))

            else:
                return ([1],'{} cannot be set.'.format(self.parameter))

        elif instr_name == 'change_prop':
            self.prop = args
            return ([0],'Executed {} instruction.'.format(instr_name))

        elif instr_name == 'change_device_refresh':
            self.refresh_time = args['time']

        elif instr_name in self.mapping.keys():
            response = self.mapping[instr_name](args)
            return ([0],'Executed {} instruction.'.format(instr_name))
        
        else:
            return ([1],'Unknown instruction {}.'.format(instr_name))

    @hp.try_deco
    def scan(self):
        if self.ns.on_setpoint and time.time() - self.start_of_setpoint > self.time_per_step:
            print('scanning')
            self.ns.on_setpoint = False
            if self.ns.current_position == len(self.scan_array):
                self.ns.scanning = False
                self.ns.progress = 1.0
                self.current_position = 0
                self.ns.scan_number = -1 #back to the stream
                return ([0],'Stopped {} scan.'.format(self.scan_parameter))
            else:
                self.setpoint = self.scan_array[self.ns.current_position]
                return ([0],'{} scan: setpoint acknowledged'.format(self.scan_parameter))

    @hp.try_deco
    def input(self):
        data_from_device = self.read_from_device()
        data = [time.time() - TIME_OFFSET - self.clock_offset,
                self.clock_offset,
                self.ns.scan_number,
                self.ns.mass]
        data.extend(data_from_device)
        return ([0],data)
    
    @hp.try_deco
    def output(self):
        self.write_to_device()
        self.ns.on_setpoint = True
        if self.ns.scanning:
            self.setpoint_reached()
        return ([0],'{} setpoint reached'.format(self.scan_parameter))

    def setpoint_reached(self):
        self.ns.on_setpoint = True
        if self.ns.scanning:
            self.ns.progress = self.current_position/len(self.scan_array)
            self.current_position += 1
            self.start_of_setpoint = time.time()

    @hp.try_deco
    def stabilize(self):
        # wrapper to ensure proper try_deco
        if self.wavelength_lock:
            self.stabilize_device()

