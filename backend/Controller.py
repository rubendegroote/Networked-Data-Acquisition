import os,sys
import configparser

from backend.helpers import *
from backend.connectors import Connector, Acceptor
import backend.logbook as lb
from backend.dispatcher import Dispatcher

CONFIG_PATH = os.getcwd() + "\\Config files\\config.ini"
SCAN_PATH = os.getcwd() + "\\Config files\\scan_init.ini"

class Controller(Dispatcher):
    ### get configuration details
    config_parser = configparser.ConfigParser()
    config_parser.read(CONFIG_PATH)

    scan_parser = configparser.ConfigParser()
    scan_parser.read(SCAN_PATH)

    log_path = config_parser['paths']['log_path'] 
    if not os.path.exists(log_path):
        os.makedirs(log_path)
    log_path += 'logbook'

    PORT = int(config_parser['ports']['controller'])
    def __init__(self, PORT=PORT, name='Controller'):
        super(Controller, self).__init__(PORT, name)
        self.progress = {}
        self.scanning = {}
        self.format = {}
        self.write_params = {}
        self.on_setpoint = {}
        self.status_data = {}
        self.refresh_times = {}
        
        self.proton_info = {}

        self.scanner_name = ""
        self.last_scan = -1
        self.current_scan = -1
        self.scan_mass = {}
        self.scan_ranges = {}
        self.mass = 0

        # logbook
        try:
            self.logbook = lb.loadLogbook(self.log_path)
            self.log_edits = list(range(len(self.logbook)))
        except Exception as e:
            print(e)
            self.logbook = []
            lb.saveLogbook(self.log_path, self.logbook)
            self.log_edits = []

        self.read_config()

    def read_config(self):
        # get last scan number from config file
        self.last_scan = int(self.scan_parser['last_scan']['last_scan'])
        self.mass = int(self.scan_parser['last_scan']['mass'])
        self.scanner_name = self.scan_parser['scanner']['scanner']
        
        self.scanning[self.scanner_name] = int(self.scan_parser['scanning']['scanning']) == 1
        
        if self.scanning[self.scanner_name]:
            self.current_scan = self.last_scan
        
        scan_mass = dict(self.scan_parser['scan_mass'])
        for key,val in scan_mass.items():
            scan_mass[key] = eval(val)
        self.scan_mass = scan_mass
        
        scan_ranges = dict(self.scan_parser['scan_ranges'])
        for key,val in scan_ranges.items():
            scan_ranges[key] = eval(val)
        self.scan_ranges = scan_ranges

    @try_call
    def status(self, *args):
        to_remove = []
        for key in self.status_data.keys():
            if not key in self.connInfo.keys():
                to_remove.append(key)
        for key in to_remove:
            del self.scanning[key]
            del self.on_setpoint[key]
            del self.progress[key]
            del self.format[key]
            del self.write_params[key]
            del self.status_data[key]

        params = {'connector_info': self.connInfo,
                  'last_scan':self.last_scan,
                  'scanning': self.scanning,
                  'on_setpoint': self.on_setpoint,
                  'progress': self.progress,
                  'format': self.format,
                  'write_params': self.write_params,
                  'scan_mass':self.scan_mass,
                  'status_data':self.status_data,
                  'refresh_time':self.refresh_times}
        return params

    @try_call
    def change_save_mode(self,params):
        device = self.connectors[params['device']]
        device.add_request(('change_save_mode',
                {'save':params['save'], 'save_stream':params['stream']}))

        return {}

    def change_save_mode_reply(self,track,params):
        pass

    @try_call
    def start_scan(self,params):
        device_name = params['device']
        scan_parameter = params['scan_parameter']
        mode = params['mode']
        scan_array = params['scan_array']
        scan_summary = params['scan_summary']
        units_per_step = params['units_per_step']
        mass = params['mass'][0]

        self.last_scan += 1
        self.current_scan = self.last_scan
        self.mass = mass
        
        try:
            self.scan_mass[str(mass)].append(self.last_scan)
        except:
            self.scan_mass[str(mass)] = [self.last_scan]
        self.scan_ranges[str(self.last_scan)] = scan_summary

        self.scan_device(device_name,scan_parameter,mode,
                         scan_array,units_per_step)

        # logbook updating
        info_for_log = {'Scan Number': self.last_scan,
                        'Author': 'Automatic Entry',
                        'Mass': mass,
                        'Tags': {"Scan": True},
                        'Text': lb.stringify_scan_summary(\
                                   device_name,scan_summary)}
        self.add_to_logbook(info_for_log)

        return {}

    def scan_device(self,device_name,scan_parameter,mode,
                         scan_array,units_per_step):
        self.scanner_name = device_name
        scanner = self.connectors[device_name]
        scanner.add_request(('execute_instruction',
                {'instruction':'start_scan',
                 'arguments':{'scan_parameter':scan_parameter,
                              'scan_array':scan_array,
                              'mode':mode,
                              'units_per_step':units_per_step}}))

    @try_call
    def stop_scan(self,params):
        scanner = self.connectors[self.scanner_name]
        scanner.add_request(('execute_instruction',
               {'instruction':'stop_scan',
                'arguments':{}}))

        return {}

    @try_call
    def go_to_setpoint(self,params):
        device_name = params['device']
        parameter = params['parameter']
        setpoint = params['setpoint']

        self.set_device(device_name,parameter,setpoint)

        return {}

    @try_call
    def get_scan_ranges(self,params):
        scans = params['scans']
        ranges = {k:v for k,v in self.scan_ranges.items() if int(k) in scans}
        return {'ranges':ranges}

    def set_device(self,device_name,parameter,setpoint):
        device_to_set = self.connectors[device_name]
        device_to_set.add_request(('execute_instruction',
               {'instruction':'go_to_setpoint',
                'arguments':{'parameter':parameter,
                             'setpoint':setpoint}}))

        info_for_log =  {'Author': 'Automatic Entry',
                 'Tags': {"Setpoint":True},
                 'Text': lb.SET.format(device_name, parameter, setpoint[0])}
        self.add_to_logbook(info_for_log)

    @try_call
    def logbook_status(self,params):
        no_of_edits = params['no_of_log_edits'][0]
        edits_missing = len(self.log_edits) - no_of_edits
        if not edits_missing == 0:
            log_edit_numbers = self.log_edits[-edits_missing:]
            log_edits = [self.logbook[e] for e in log_edit_numbers]
        else:
            log_edit_numbers = []
            log_edits = []

        return {'log_edit_numbers':log_edit_numbers,
                'log_edits':log_edits} # send all edits that have not been sent yet

    @try_call
    def add_entry_to_log(self,params):
        self.add_to_logbook(info_for_log = {})
        return {}

    @try_call
    def change_entry(self,params):
        number = params['number'][0]
        entry = params['entry']
        lb.editEntry(self.logbook,number,entry)
        lb.saveEntry(self.log_path, self.logbook, number)
        self.log_edits.append(number) # number of the entry that was edited
        return {}

    @try_call
    def add_new_field(self,params):
        field_name = params['field_name']
        for number,entry in enumerate(self.logbook):
            new_info = {field_name:""}
            lb.editEntry(self.logbook,number,new_info)
            lb.saveEntry(self.log_path, self.logbook, number)
            self.log_edits.append(number) # number of the entry that was edited
        return {}

    @try_call
    def add_new_tag(self,params):
        tag_name = params['tag_name']
        number = params['number']
        new_info = {'Tags':{tag_name:True}}
        lb.editEntry(self.logbook,number,new_info)
        lb.saveEntry(self.log_path, self.logbook, number)
        self.log_edits.append(number) # number of the entry that was edited
        return {'tag_name':tag_name}

    def add_to_logbook(self,info_for_log):
        lb.addEntryFromCopy(self.logbook,info_for_log)
        lb.saveEntry(self.log_path, self.logbook, -1)
        self.log_edits.append(len(self.logbook)-1) # number of the entry that was added

    def default_cb(self):
        return 'status',{'scan_number': [self.current_scan],
                         'mass': [self.mass],
                         'proton_info':self.proton_info}

    def status_reply(self,track,params):
        origin, track_id = track[-1]
        if origin == self.scanner_name:
            if self.scanning[origin] and not params['scanning']:
                self.current_scan = -1
                # update scan progress in ini file
                self.update_scan_file(0)
            elif not self.scanning[origin] and params['scanning']:
                self.update_scan_file(1)

        self.scanning[origin] = params['scanning']
        self.progress[origin] = params['progress']
        self.on_setpoint[origin] = params['on_setpoint']
        self.status_data[origin] = params['status_data']
        self.refresh_times[origin] = params['refresh_time']
        if 'proton' in self.status_data.keys():
            self.proton_info = self.status_data['proton']

    def update_scan_file(self,scanning):
        self.scan_parser['last_scan'] = {'last_scan': self.last_scan,'mass': self.mass}
        self.scan_parser['scanner'] = {'scanner': self.scanner_name}
        self.scan_parser['scanning'] = {'scanning': scanning}
        self.scan_parser['scan_mass'] = self.scan_mass
        self.scan_parser['scan_ranges'] = self.scan_ranges

        with open(SCAN_PATH, 'w') as scanfile:
            self.scan_parser.write(scanfile)

    def initial_information_reply(self,track,params):
        origin, track_id = track[-1]
        self.format[origin] = params['format']
        self.write_params[origin] = params['write_params']

def makeController():
    return Controller()
