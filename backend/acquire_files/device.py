import socket
import time
# from . import Helpers as hp 

format = ('timestamp','scan_number','mass','setpoint')

class Device():
    def __init__(self,name = 'device',
                      format = (),
                      settings = {},
                      ns = None,
                      write_param = 'name_of_parameter',
                      mapping = {},
                      needs_stabilization = False):

        self.name = name
        self.format =  format
        self.settings = settings
        self.ns = ns
        self.write_param = write_param
        self.mapping = mapping

        self.needs_stabilization = needs_stabilization

    def connect_to_device(self):
        # to be overridden
        pass

    def write_to_device(self):
        # to be overridden
        pass

    def read_from_device(self):
        # to be overridden
        pass

    # @hp.try_deco
    def setup(self):
        self.connect_to_device()
        return ([0],"Communication with {} achieved.".format(self.name))

    # @hp.try_deco
    def interpret(self,instr):
        if instr == 'scan':
            if self.ns.scan_parameter == self.write_param:
                self.ns.current_position = 0
                self.ns.scanning = True
                return ([0],'Starting {} scan.'.format(self.ns.scan_parameter))
            else:
                return ([1],'{} cannot be scanned.'.format(self.ns.scan_parameter))

        elif instr == 'go_to_setpoint':
            if self.ns.parameter == self.write_param:
                self.ns.on_setpoint = False
                return ([0],'{} setpoint acknowledged.'.format(self.write_param))

            else:
                return ([1],'{} cannot be set.'.format(self.ns.parameter))

        elif instr in self.mapping.keys():
            translation = self.mapping[instr]
            translation()
            return ([0],'Executed {} instruction.'.format(instr))
        
        else:
            return ([1],'Unknown instruction {}.'.format(instr))

    # @hp.try_deco
    def scan(self):
        if time.time() - self.ns.start_of_setpoint > self.ns.time_per_step:
            self.ns.on_setpoint = False
            if self.ns.current_position == len(self.ns.scan_array):
                self.ns.scanning = False
                self.ns.progress = 1.0
                return ([0],'Stopped {} scan.'.format(self.ns.scan_parameter))
            else:
                self.ns.setpoint = self.ns.scan_array[self.ns.current_position]
                return ([0],'{} scan: setpoint acknowledged'.format(self.ns.scan_parameter))

    # @hp.try_deco
    def stabilize(self):
        # do stabilization if needed
        if not self.ns.on_setpoint: # go to setpoint if needed
            self.write_to_device()
            self.ns.on_setpoint = True
            if self.ns.scanning:
                self.ns.progress = self.ns.current_position/len(self.ns.scan_array)
                self.ns.current_position += 1
                self.ns.start_of_setpoint = time.time()
            return ([0],'{} setpoint reached'.format(self.ns.scan_parameter))
        
        if self.needs_stabilization:
            # do stuff to stabilize on setpoint
            # this will probz take some self.write_to_device() calls
            # self.write_to_device()
            pass

    # @hp.try_deco
    def input(self):
        data_from_device = self.read_from_device()
        data = [time.time(),
                self.ns.scan_number,
                self.ns.mass, 
                self.ns.setpoint]
        data.extend(data_from_device)
        return ([0],data)
    

