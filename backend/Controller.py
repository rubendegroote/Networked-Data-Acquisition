import sys
import configparser

from backend.Helpers import *
from backend.connectors import Connector, Acceptor
import backend.logbook as lb
from backend.dispatcher import Dispatcher

LOG_PATH = 'C:\\Logbook\\Gallium Run\\logbook'
INI_PATH = 'C:\\Logbook\\Gallium Run\\scan_init.ini'

class Controller(Dispatcher):
    def __init__(self, PORT=5007, name='Controller'):
        super(Controller, self).__init__(PORT, name)

        self.scanner_name = ""
        self.scan_number = -1
        self.progress = {}
        self.scanning = {}
        self.format = {}
        self.write_params = {}
        self.on_setpoint = {}
        self.masses = []
        self.status_data = {}

        # logbook
        try:
            self.logbook = lb.loadLogbook(LOG_PATH)
            self.log_edits = list(range(len(self.logbook)))
        except Exception as e:
            print(e)
            self.logbook = []
            lb.saveLogbook(LOG_PATH, self.logbook)
            self.log_edits = []

        # get last scan number from config file
        self.scan_parser = configparser.ConfigParser()
        try:
            self.scan_parser.read(INI_PATH)
            self.scan_number = int(self.scan_parser['scan_number']['scan_number'])
            try:
                origin, progress = self.scan_parser['progress']['origin'], self.scan_parser['progress']['progress']
                self.progress[origin] = progress
            except:
                print('No scanprogress found.')
        except:
            print('No scan ini file found')

    @try_call
    def status(self, *args):
        params = {'connector_info': self.connInfo,
                  'scan_number': [self.scan_number],
                  'scanning': self.scanning,
                  'on_setpoint': self.on_setpoint,
                  'progress': self.progress,
                  'format': self.format,
                  'write_params': self.write_params,
                  'masses':self.masses,
                  'status_data':self.status_data}
        return params

    @try_call
    def change_device_refresh(self, params):
        device_name = params['device'][0]
        time = params['time']
        self.change_refresh(device_name,time)
        return {}

    def change_refresh(self,device_name,time):
        device = self.connectors[device_name]
        device.add_request(('change_refresh_time',{'time':time}))

    def change_refresh_time_reply(self,track,params):
        origin, track_id = track[-1]
        self.notify_connectors(([0],"Device {} received change refresh time instruction correctly.".format(origin)))

    @try_call
    def change_device_prop(self, params):
        device_name = params['device'][0]
        prop = params['prop']
        self.change_prop(device_name,prop)
        return {}

    def change_prop(self,device_name,prop):
        device = self.connectors[device_name]
        device.add_request(('change_prop',{'prop':prop}))

    def change_prop_reply(self,track,params):
        origin, track_id = track[-1]
        self.notify_connectors(([0],"Device {} received change proportionality instruction correctly.".format(origin)))

    @try_call
    def lock_device_etalon(self, params):
        device_name = params['device'][0]
        lock = params['lock']
        self.lock_etalon(device_name,lock)
        return {}

    def lock_etalon(self,device_name,lock):
        device = self.connectors[device_name]
        device.add_request(('lock_etalon',{'lock':lock}))

    def lock_etalon_reply(self,track,params):
        origin, track_id = track[-1]
        self.notify_connectors(([0],"Device {} received lock etalon instruction correctly.".format(origin)))

    @try_call
    def set_device_etalon(self, params):
        device_name = params['device'][0]
        etalon_value = params['etalon_value']
        self.set_etalon(device_name,etalon_value)
        return {}

    def set_etalon(self,device_name,etalon_value):
        device = self.connectors[device_name]
        device.add_request(('set_etalon',{'etalon_value':etalon_value}))

    def set_etalon_reply(self,track,params):
        origin, track_id = track[-1]
        self.notify_connectors(([0],"Device {} received set etalon instruction correctly.".format(origin)))

    @try_call
    def lock_device_cavity(self, params):
        device_name = params['device'][0]
        lock = params['lock']
        self.lock_cavity(device_name,lock)
        return {}

    def lock_cavity(self,device_name,lock):
        device = self.connectors[device_name]
        device.add_request(('lock_cavity',{'lock':lock}))

    def lock_cavity_reply(self,track,params):
        origin, track_id = track[-1]
        self.notify_connectors(([0],"Device {} received lock cavity instruction correctly.".format(origin)))

    @try_call
    def set_device_cavity(self, params):
        device_name = params['device'][0]
        cavity_value = params['cavity_value']
        self.set_cavity(device_name,cavity_value)
        return {}

    def set_cavity(self,device_name,cavity_value):
        device = self.connectors[device_name]
        device.add_request(('set_cavity',{'cavity_value':cavity_value}))

    def set_cavity_reply(self,track,params):
        origin, track_id = track[-1]
        self.notify_connectors(([0],"Device {} received set cavity instruction correctly.".format(origin)))

    @try_call
    def lock_device_wavelength(self, params):
        device_name = params['device'][0]
        lock = params['lock']
        self.lock_wavelength(device_name,lock)
        return {}

    def lock_wavelength(self,device_name,lock):
        device = self.connectors[device_name]
        device.add_request(('lock_wavelength',{'lock':lock}))

    def lock_wavelength_reply(self,track,params):
        origin, track_id = track[-1]
        self.notify_connectors(([0],"Device {} received lock wavelength instruction correctly.".format(origin)))

    @try_call
    def lock_device_ecd(self, params):
        device_name = params['device'][0]
        lock = params['lock']
        self.lock_ecd(device_name,lock)
        return {}

    def lock_ecd(self,device_name,lock):
        device = self.connectors[device_name]
        device.add_request(('lock_ecd',{'lock':lock}))

    def lock_ecd_reply(self,track,params):
        origin, track_id = track[-1]
        self.notify_connectors(([0],"Device {} received lock doubler instruction correctly.".format(origin)))

    @try_call
    def start_scan(self, params):
        device_name = params['device'][0]
        scan_parameter = params['scan_parameter']
        scan_array = params['scan_array']
        time_per_step = params['time_per_step']
        mass = params['mass']

        self.scan_device(device_name,scan_parameter,
                         scan_array,time_per_step,mass)

        return {}

    def scan_device(self,device_name,scan_parameter,
                         scan_array,time_per_step,
                         mass):
        self.scanner_name = device_name
        scanner = self.connectors[device_name]
        self.scan_number += 1
        self.set_all_masses(mass[0])
        self.set_scan_info(self.scan_number)
        scanner.add_request(('start_scan',{'scan_parameter':scan_parameter,
                                     'scan_array':scan_array,
                                     'time_per_step':time_per_step,
                                     'mass':mass}))
        # lgobook updating
        info_for_log = {'Scan Number': self.scan_number,
                        'Author': 'Automatic Entry',
                        'Mass': mass[0],
                        'Tags': {"Scan": True},
                        'Text': lb.START.format(device_name,
                                                scan_array[0],
                                                scan_array[-1],
                                                len(scan_array),
                                                time_per_step[0])}
        self.add_to_logbook(info_for_log)
        self.current_scan_log_number = len(self.logbook)-1

        # update scan progress in ini file
        self.scan_parser['scan_number'] = {'scan_number': self.scan_number}
        with open(INI_PATH, 'w') as scanfile:
            self.scan_parser.write(scanfile)

    def start_scan_reply(self,track,params):
        origin, track_id = track[-1]
        self.notify_connectors(([0],"Device {} received scanning instruction correctly.".format(origin)))

    @try_call
    def set_scan_info(self, number):
        op,params = 'set_scan_number',{'scan_number': [number]}
        for instr in self.connectors.values():
            instr.add_request((op,params))
        return {}

    def set_scan_number_reply(self,track,params):
        origin, track_id = track[-1]
        self.notify_connectors(([0],"Device {} received scan number setting instruction correctly.".format(origin)))

    @try_call
    def set_all_masses(self, mass):
        op, params = 'set_mass', {'mass': [mass]}
        for instr in self.connector.values():
            instr.add_request((op, params))
        return {}

    def set_mass_reply(self, track, params):
        origin, track_id = track[-1]
        self.notify_connectors(([0], "Device {} received mass setting instruction correctly.".format(origin)))

    @try_call
    def stop_scan(self,params):
        self.set_scan_info(-1)
        self.connectors[self.scanner_name].add_request(('stop_scan',{}))

        return {}

    def stop_scan_reply(self,track,params):
        origin, track_id = track[-1]
        self.notify_connectors(([0],"Device {} received stopping instruction correctly.".format(origin)))

    @try_call
    def go_to_setpoint(self, params):
        device_name = params['device'][0]
        parameter = params['parameter']
        setpoint = params['setpoint']

        self.set_device(device_name,parameter,setpoint)

        return {}

    def set_device(self,device_name,parameter,setpoint):
        device_to_set = self.connectors[device_name]
        device_to_set.add_request(('go_to_setpoint',{'parameter':parameter,
                                                     'setpoint':setpoint}))
        info_for_log =  {'Author': 'Automatic Entry',
                 'Tags': {"Setpoint":True},
                 'Text': lb.SET.format(device_name, parameter[0], setpoint[0])}
        self.add_to_logbook(info_for_log)

    def go_to_setpoint_reply(self,track,params):
        origin, track_id = track[-1]
        self.notify_connectors(([0],"Device {} received setpoint instruction correctly.".format(origin)))

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
        lb.saveEntry(LOG_PATH, self.logbook, number)
        self.log_edits.append(number) # number of the entry that was edited
        return {}

    @try_call
    def add_new_field(self,params):
        field_name = params['field_name']
        for number,entry in enumerate(self.logbook):
            new_info = {field_name:""}
            lb.editEntry(self.logbook,number,new_info)
            lb.saveEntry(LOG_PATH, self.logbook, number)
            self.log_edits.append(number) # number of the entry that was edited
        return {}

    @try_call
    def add_new_tag(self,params):
        tag_name = params['tag_name']
        number = params['number']
        new_info = {'Tags':{tag_name:True}}
        lb.editEntry(self.logbook,number,new_info)
        lb.saveEntry(LOG_PATH, self.logbook, number)
        self.log_edits.append(number) # number of the entry that was edited
        return {'tag_name':tag_name}

    def status_reply(self, track, params):
        origin, track_id = track[-1]
        self.format[origin] = params['format']
        self.write_params[origin] = params['write_params']
        if origin == self.scanner_name:
            if self.scanning[origin] and not params['scanning']:
                self.set_scan_info(-1)
        self.scanning[origin] = params['scanning']
        self.progress[origin] = params['progress']
        self.on_setpoint[origin] = params['on_setpoint']
        if not params['mass'] in self.masses:
            self.masses.append(params['mass'])
        self.status_data[origin] = params['status_data']

        self.scan_parser['scan_number'] = {'scan_number': self.scan_number}
        self.scan_parser['progress'] = {'progress': params['progress'],
                                        'origin': origin}
        with open(INI_PATH, 'w') as scanfile:
            self.scan_parser.write(scanfile)

    def add_to_logbook(self,info_for_log):
        lb.addEntryFromCopy(self.logbook,info_for_log)
        lb.saveEntry(LOG_PATH, self.logbook, -1)
        self.log_edits.append(len(self.logbook)-1) # number of the entry that was added

def makeController(PORT=5007):
    return Controller(PORT=PORT)

