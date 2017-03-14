import os,sys,time
import backend.helpers as hp
import configparser
import numpy as np

format = ('timestamp','offset','scan_number','mass')
write_params = []

config_parser = configparser.ConfigParser()
CONFIG_PATH = os.getcwd() + "\\Config files\\config.ini"
config_parser.read(CONFIG_PATH)
TIME_OFFSET = int(config_parser['other']['time_offset'])

class BaseHardware():
    def __init__(self,name = 'hardware',
                      format = format,
                      write_params=write_params,
                      needs_stabilization = False,
                      refresh_time = 100):

        self.name = name
        self.format = format
        self.write_params = write_params

        self.start_of_setpoint = time.time()
        self.setpoint = 0

        self.scan_mode = 'seconds'

        self.refresh_time = refresh_time

        ## proton sypercyle info
        self.counter = 0
        self.initial_bunch_number = -1
        self.prev_bunch_number = -1

        self.needs_stabilization = needs_stabilization
        if needs_stabilization:
            self.wavelength_lock = False
            self.prop = 10

    def connect_to_device(self):
        # to be overridden
        pass

    def write_to_device(self):
        # to be overridden
        return True

    def read_from_device(self):
        # to be overridden
        return []

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
            self.parameter = args['scan_parameter']
            self.scan_array = args['scan_array']
            self.units_per_step = args['units_per_step'][0]
            self.scan_mode = args['mode']

            if self.parameter in self.write_params:
                self.current_position = 0
                self.ns.progress = 0
                self.ns.scanning = True
                try:
                    self.initial_bunch_number = self.ns.proton_info['SC_current_bunch']
                    self.prev_bunch_number = self.ns.proton_info['SC_current_bunch']
                except:
                    self.initial_bunch_number = 0
                    self.prev_bunch_number = 0

                self.counter = 0
                return ([0],'Starting {} scan.'.format(self.parameter))
            else:
                return ([1],'{} cannot be scanned.'.format(self.parameter))

        elif instr_name == 'stop_scan':
            self.ns.scanning = False
            return ([0],'Stopped {} scan.'.format(self.parameter))

        elif instr_name == 'go_to_setpoint':
            parameter = args['parameter']
            setpoint = args['setpoint'][0]
            # if parameter in self.write_params:
            self.parameter = parameter
            self.setpoint = setpoint
            self.ns.on_setpoint = False
            return ([0],'{} setpoint acknowledged.'.format(self.parameter))

            # else:
            #     return ([1],'{} cannot be set.'.format(parameter))

        elif instr_name == 'change_device_refresh':
            self.ns.refresh_time = args['time']

        elif instr_name in self.mapping.keys():
            response = self.mapping[instr_name](args)
            return ([0],'Executed {} instruction.'.format(instr_name))
        
        else:
            return ([1],'Unknown instruction {}.'.format(instr_name))

    @hp.try_deco
    def scan(self):
        if not self.ns.on_setpoint:
            return

        if self.scan_mode == 'seconds':
            if time.time() - self.start_of_setpoint > self.units_per_step:
                return self.step_scan()

        elif self.scan_mode == 'proton pulses':
            if self.check_pp():
                return self.step_scan()    

        elif self.scan_mode == 'proton supercycles':
            if self.check_SC():
                return self.step_scan()

    def step_scan(self):
        self.ns.on_setpoint = False
        print(self.current_position)
        if self.current_position == len(self.scan_array)-1:
            self.stop_scan()
            return ([0],'Stopped {} scan.'.format(self.parameter))
        else:
            self.setpoint = self.scan_array[self.current_position]
            return ([0],'{} scan: setpoint acknowledged'.format(self.parameter))

    def check_SC(self):
        current_bunch = self.ns.proton_info['SC_current_bunch']
        if not current_bunch == self.prev_bunch_number:
            self.prev_bunch_number = current_bunch

            if current_bunch == 1:
                self.counter += 1

            if self.counter == int(self.units_per_step):
                if current_bunch == self.initial_bunch_number:
                    self.counter = 0
                    return True
                    
            elif self.counter > int(self.units_per_step):
                # in case the SC gets shorter you may never reach the initial number,
                # and then the counter will increment one further than the 
                # total SC required
                self.counter = 0
                return True

        return False

    def check_pp(self):
        current_bunch = self.ns.proton_info['SC_current_bunch']
        if not current_bunch == self.prev_bunch_number:
            self.prev_bunch_number = current_bunch
            if self.counter == int(self.units_per_step):
                # by first checking the counter we stop when we have had the required number of pulses
                # but we measured during the final pulse as well
                self.counter = 0
                return True
            if self.ns.proton_info['HRS_protons_on'] == 1:
                self.counter += 1
       
        return False

    def stop_scan(self):
        self.ns.scanning = False
        self.ns.progress = 1.0
        self.current_position = 0

    @hp.try_deco
    def input(self):
        generic_data = [time.time() - TIME_OFFSET - self.ns.clock_offset,
                self.ns.clock_offset,
                self.ns.scan_number,
                self.ns.mass]
        
        data_from_device = np.array(self.read_from_device())
        if data_from_device.ndim > 1:
            generic_data = np.row_stack([generic_data]*len(data_from_device))
            data = np.column_stack((generic_data,data_from_device))

        else:
            generic_data.extend(data_from_device)
            data = np.array([generic_data])

        return ([0],data)
    
    @hp.try_deco
    def output(self):
        done = self.write_to_device()
        if done:
            self.setpoint_reached()
            return ([0],'{} setpoint reached'.format(self.parameter))

    def setpoint_reached(self):
        self.ns.on_setpoint = True
        if self.ns.scanning:
            self.current_position += 1
            self.ns.progress = self.current_position/len(self.scan_array)
            self.start_of_setpoint = time.time()
            try:
                self.initial_bunch_number = self.ns.proton_info['SC_current_bunch']
            except:
                pass

    @hp.try_deco
    def stabilize(self):
        # wrapper to ensure proper try_deco
        if self.wavelength_lock:
            self.stabilize_device()

