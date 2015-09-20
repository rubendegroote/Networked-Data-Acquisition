import sys

from backend.Helpers import *
from backend.connectors import Connector, Acceptor
import backend.logbook as lb
from backend.dispatcher import Dispatcher

LOG_PATH = 'C:\\Logbook\\Gallium Run\\logbook'

class Manager(Dispatcher):
    def __init__(self, PORT=5007, name='Manager'):
        super(Manager, self).__init__(PORT, name)

        self.scanner_name = ""
        self.scan_number = -1
        self.progress = {}
        self.scanning = {}
        self.format = {}
        self.write_params = {}
        self.on_setpoint = {}
        self.masses = []
        self.status_data = {}

        try:
            self.logbook = lb.loadLogbook(LOG_PATH)
            self.log_edits = list(range(len(self.logbook)))
        except Exception as e:
            print(e)
            self.logbook = []
            lb.saveLogbook(LOG_PATH, self.logbook)
            self.log_edits = []

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
    def change_artist_refresh(self, params):
        artist_name = params['artist'][0]
        time = params['time']        
        self.change_refresh(artist_name,time)
        return {}

    def change_refresh(self,artist_name,time):
        artist = self.connectors[artist_name]
        artist.add_request(('change_refresh_time',{'time':time}))

    def change_refresh_time_reply(self,track,params):
        origin, track_id = track[-1]
        self.notify_connectors(([0],"Artist {} received change refresh time instruction correctly.".format(origin)))

    @try_call
    def change_artist_prop(self, params):
        artist_name = params['artist'][0]
        prop = params['prop']        
        self.change_prop(artist_name,prop)
        return {}

    def change_prop(self,artist_name,prop):
        artist = self.connectors[artist_name]
        artist.add_request(('change_prop',{'prop':prop}))

    def change_prop_reply(self,track,params):
        origin, track_id = track[-1]
        self.notify_connectors(([0],"Artist {} received change proportionality instruction correctly.".format(origin)))

    @try_call
    def lock_artist_etalon(self, params):
        artist_name = params['artist'][0]
        lock = params['lock']        
        self.lock_etalon(artist_name,lock)
        return {}

    def lock_etalon(self,artist_name,lock):
        artist = self.connectors[artist_name]
        artist.add_request(('lock_etalon',{'lock':lock}))

    def lock_etalon_reply(self,track,params):
        origin, track_id = track[-1]
        self.notify_connectors(([0],"Artist {} received lock etalon instruction correctly.".format(origin)))

    @try_call
    def set_artist_etalon(self, params):
        artist_name = params['artist'][0]
        etalon_value = params['etalon_value']        
        self.set_etalon(artist_name,etalon_value)
        return {}

    def set_etalon(self,artist_name,etalon_value):
        artist = self.connectors[artist_name]
        artist.add_request(('set_etalon',{'etalon_value':etalon_value}))

    def set_etalon_reply(self,track,params):
        origin, track_id = track[-1]
        self.notify_connectors(([0],"Artist {} received set etalon instruction correctly.".format(origin)))

    @try_call
    def lock_artist_cavity(self, params):
        artist_name = params['artist'][0]
        lock = params['lock']        
        self.lock_cavity(artist_name,lock)
        return {}

    def lock_cavity(self,artist_name,lock):
        artist = self.connectors[artist_name]
        artist.add_request(('lock_cavity',{'lock':lock}))

    def lock_cavity_reply(self,track,params):
        origin, track_id = track[-1]
        self.notify_connectors(([0],"Artist {} received lock cavity instruction correctly.".format(origin)))

    @try_call
    def set_artist_cavity(self, params):
        artist_name = params['artist'][0]
        cavity_value = params['cavity_value']
        self.set_cavity(artist_name,cavity_value)
        return {}

    def set_cavity(self,artist_name,cavity_value):
        artist = self.connectors[artist_name]
        artist.add_request(('set_cavity',{'cavity_value':cavity_value}))

    def set_cavity_reply(self,track,params):
        origin, track_id = track[-1]
        self.notify_connectors(([0],"Artist {} received set cavity instruction correctly.".format(origin)))

    @try_call
    def lock_artist_wavelength(self, params):
        artist_name = params['artist'][0]
        lock = params['lock']
        self.lock_wavelength(artist_name,lock)
        return {}

    def lock_wavelength(self,artist_name,lock):
        artist = self.connectors[artist_name]
        artist.add_request(('lock_wavelength',{'lock':lock}))

    def lock_wavelength_reply(self,track,params):
        origin, track_id = track[-1]
        self.notify_connectors(([0],"Artist {} received lock wavelength instruction correctly.".format(origin)))

    @try_call
    def lock_artist_ecd(self, params):
        artist_name = params['artist'][0]
        lock = params['lock']
        self.lock_ecd(artist_name,lock)
        return {}

    def lock_ecd(self,artist_name,lock):
        artist = self.connectors[artist_name]
        artist.add_request(('lock_ecd',{'lock':lock}))

    def lock_ecd_reply(self,track,params):
        origin, track_id = track[-1]
        self.notify_connectors(([0],"Artist {} received lock doubler instruction correctly.".format(origin)))

    @try_call
    def start_scan(self, params):
        artist_name = params['artist'][0]
        scan_parameter = params['scan_parameter']
        scan_array = params['scan_array']
        time_per_step = params['time_per_step']
        mass = params['mass']
        
        self.scan_artist(artist_name,scan_parameter,
                         scan_array,time_per_step,mass)

        return {}

    def scan_artist(self,artist_name,scan_parameter,
                         scan_array,time_per_step,
                         mass):
        self.scanner_name = artist_name
        scanner = self.connectors[artist_name]
        self.scan_number += 1
        self.set_all_scan_numbers(self.scan_number)
        scanner.add_request(('start_scan',{'scan_parameter':scan_parameter,
                                     'scan_array':scan_array,
                                     'time_per_step':time_per_step,
                                     'mass':mass}))
        
        info_for_log = {'Scan Number': self.scan_number,
             'Author': 'Automatic Entry',
             'Mass':mass[0],
             'Tags': {"Scan":True},
             'Text': lb.START.format(artist_name,scan_array[0],
                                     scan_array[-1],
                                     len(scan_array),
                                     time_per_step[0])}
        self.add_to_logbook(info_for_log)
        self.current_scan_log_number = len(self.logbook)-1

    def start_scan_reply(self,track,params):
        origin, track_id = track[-1]
        self.notify_connectors(([0],"Artist {} received scanning instruction correctly.".format(origin)))

    @try_call
    def set_all_scan_numbers(self, number):
        op,params = 'set_scan_number',{'scan_number': [number]}
        for instr in self.connectors.values():
            instr.add_request((op,params))
        return {}

    def set_scan_number_reply(self,track,params):
        origin, track_id = track[-1]
        self.notify_connectors(([0],"Artist {} received scan number setting instruction correctly.".format(origin)))

    @try_call
    def stop_scan(self,params):
        self.set_all_scan_numbers(-1)
        self.connectors[self.scanner_name].add_request(('stop_scan',{}))

        return {}

    def stop_scan_reply(self,track,params):
        origin, track_id = track[-1]
        self.notify_connectors(([0],"Artist {} received stopping instruction correctly.".format(origin)))

    @try_call
    def go_to_setpoint(self, params):
        artist_name = params['artist'][0]
        parameter = params['parameter']
        setpoint = params['setpoint']
        
        self.set_artist(artist_name,parameter,setpoint)

        return {}

    def set_artist(self,artist_name,parameter,setpoint):
        artist_to_set = self.connectors[artist_name]
        artist_to_set.add_request(('go_to_setpoint',{'parameter':parameter,
                                                     'setpoint':setpoint}))
        info_for_log =  {'Author': 'Automatic Entry',
                 'Tags': {"Setpoint":True},
                 'Text': lb.SET.format(artist_name, parameter[0], setpoint[0])}
        self.add_to_logbook(info_for_log)

    def go_to_setpoint_reply(self,track,params):
        origin, track_id = track[-1]
        self.notify_connectors(([0],"Artist {} received setpoint instruction correctly.".format(origin)))
        
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
                self.set_all_scan_numbers(-1)
        self.scanning[origin] = params['scanning']
        self.progress[origin] = params['progress']
        self.on_setpoint[origin] = params['on_setpoint']
        if not params['mass'] in self.masses:
            self.masses.append(params['mass'])
        self.status_data[origin] = params['status_data']

    def add_to_logbook(self,info_for_log):
        lb.addEntryFromCopy(self.logbook,info_for_log)
        lb.saveEntry(LOG_PATH, self.logbook, -1)
        self.log_edits.append(len(self.logbook)-1) # number of the entry that was added

def makeManager(PORT=5007):
    return Manager(PORT=PORT)

