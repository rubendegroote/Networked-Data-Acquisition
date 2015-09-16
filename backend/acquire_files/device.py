import socket
import time
import backend.Helpers as hp 

format = ('timestamp','scan_number','mass','setpoint')

class Device():
    def __init__(self,name = 'device',
                      format = (),
                      settings = {},
                      ns = None,
                      write_params = 'name_of_parameter',
                      mapping = {},
                      needs_stabilization = False,
                      sleeptime = 0.001):

        self.name = name
        self.format = format
        self.settings = settings
        self.ns = ns
        self.write_params = write_params
        self.mapping = mapping

        self.needs_stabilization = needs_stabilization

        self.sleeptime = sleeptime

    def connect_to_device(self):
        # to be overridden
        pass

    def write_to_device(self):
        # to be overridden
        pass

    def read_from_device(self):
        # to be overridden
        pass

    @hp.try_deco
    def setup(self):
        self.connect_to_device()
        return ([0],"Communication with {} achieved.".format(self.name))

    @hp.try_deco
    def interpret(self,instr):
        if instr == 'scan':
            if self.ns.scan_parameter in self.write_params:
                self.ns.current_position = 0
                self.ns.scanning = True
                return ([0],'Starting {} scan.'.format(self.ns.scan_parameter))
            else:
                return ([1],'{} cannot be scanned.'.format(self.ns.scan_parameter))

        elif instr == 'go_to_setpoint':
            if self.ns.parameter in self.write_params:
                self.ns.on_setpoint = False
                return ([0],'{} setpoint acknowledged.'.format(self.write_params))

            else:
                return ([1],'{} cannot be set.'.format(self.ns.parameter))

        elif instr in self.mapping.keys():
            translation = self.mapping[instr]
            translation()
            return ([0],'Executed {} instruction.'.format(instr))
        
        else:
            return ([1],'Unknown instruction {}.'.format(instr))

    @hp.try_deco
    def scan(self):
        if self.ns.on_setpoint and time.time() - self.ns.start_of_setpoint > self.ns.time_per_step:
            print('scanning')
            self.ns.on_setpoint = False
            if self.ns.current_position == len(self.ns.scan_array):
                self.ns.scanning = False
                self.ns.progress = 1.0
                self.ns.current_position = 0
                self.ns.scan_number = -1 #back to the stream
                return ([0],'Stopped {} scan.'.format(self.ns.scan_parameter))
            else:
                self.ns.setpoint = self.ns.scan_array[self.ns.current_position]
                print(self.ns.setpoint)
                return ([0],'{} scan: setpoint acknowledged'.format(self.ns.scan_parameter))

    @hp.try_deco
    def output(self):
        self.write_to_device()
        self.ns.on_setpoint = True
        if self.ns.scanning:
            self.setpoint_reached()
        return ([0],'{} setpoint reached'.format(self.ns.scan_parameter))

    def setpoint_reached(self):
        self.ns.on_setpoint = True
        if self.ns.scanning:
            self.ns.progress = self.ns.current_position/len(self.ns.scan_array)
            self.ns.current_position += 1
            self.ns.start_of_setpoint = time.time()

    @hp.try_deco
    def stabilize(self):
        self.stabilize_device()

    @hp.try_deco
    def input(self):
        data_from_device = self.read_from_device()
        data = [time.time(),
                self.ns.scan_number,
                self.ns.mass, 
                self.ns.setpoint]
        data.extend(data_from_device)
        return ([0],data)
    

