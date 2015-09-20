import backend.Helpers as hp
from backend.save import *
from backend.connectors import Connector, Acceptor
import backend.logbook as lb
from backend.dispatcher import Dispatcher

import sys
import multiprocessing as mp
from collections import deque
import threading as th

from backend.acquire_files.acquisition import format_map,write_params_map,acquire

SAVE_DIR = "C:\\Data\\Gallium Run\\"

# Some exploratory code to understand a bit better how to make the ARTIST
class Artist(Dispatcher):
    def __init__(self, name='', PORT=5005):
        super(Artist, self).__init__(PORT, name)
        self.acquire = acquire

        # instructions queue:
        # Manager -> InstructionReceiver -> acquire
        self.iQ = mp.Queue()
        # message queue: acquire -> ARTIST
        self.mQ = mp.Queue()
        # data pipe: acquire -> ARTIST
        self.data_output,self.data_input = mp.Pipe(duplex=False)

        # stop flag for the acquisition
        self.stopFlag = mp.Event()
        self.stopFlag.set()
        # stop flag for the acquisition
        self.IStoppedFlag = mp.Event()
        self.IStoppedFlag.clear()

        # Shared memory values: manager
        self.mgr = mp.Manager()
        # Shared scan number
        self.ns = self.mgr.Namespace()
        self.ns.start_of_setpoint = time.time()
        self.ns.scan_number = -1
        self.ns.mass = 0
        self.ns.on_setpoint = False
        self.ns.scanning = False
        self.ns.current_position = 0
        self.ns.progress = 0
        self.ns.parameter = ''
        self.ns.scan_parameter = ''
        self.ns.setpoint = 11997.442
        self.ns.refresh_time = 1
        self.ns.status_data = []

        self.format = format_map[name]
        self.ns.format = self.format

        self.write_params = write_params_map[name]

        self.data_deque = deque()

        self.start_daq()

        # save pipe: send data to be saved
        self.save_output,self.save_input = mp.Pipe(duplex=False)
        self.start_saving()

    def stop():
        self.saveProcess.terminate()
        self.DAQProcess.terminate()
        super(Artist.stop())
        
    @hp.try_call
    def status(self, params):
        return {'format': self.format,
                'write_params':self.write_params,
                'scanning': self.ns.scanning,
                'on_setpoint': self.ns.on_setpoint,
                'progress': self.ns.progress,
                'scan_number': self.ns.scan_number,
                'mass':self.ns.mass,
                'status_data':self.ns.status_data}

    @hp.try_call
    def data(self, params):
        # Recall there is only one data server, so this works
        l = len(self.data_deque)
        data = [self.data_deque.popleft() for _i in range(l)]
        return {'data': data,
                'format': self.format}

    @hp.try_call
    def set_scan_number(self, params):
        self.ns.scan_number = params['scan_number'][0]
        return {}

    @hp.try_call
    def change_refresh_time(self,params):
        time = params['time'][0]
        self.ns.refresh_time = time

        return {}

    @hp.try_call
    def change_prop(self,params):
        prop = params['prop'][0]

        self.iQ.put(['change_prop',prop])

        return {}

    @hp.try_call
    def lock_etalon(self,params):
        lock = params['lock']
        if lock:
            lock = "on"
        else:
            lock = "off"

        self.iQ.put(['Lock Etalon',lock])
        
        return {}

    @hp.try_call
    def set_etalon(self,params):
        etalon_value = params['etalon_value']
        self.iQ.put(['set_etalon',etalon_value])
        
        return {}

    @hp.try_call
    def lock_cavity(self,params):
        lock = params['lock']
        if lock:
            lock = "on"
        else:
            lock = "off"
        self.iQ.put(['Lock Reference Cavity',lock])
        
        return {}

    @hp.try_call
    def set_cavity(self,params):
        cavity_value = params['cavity_value']
        self.iQ.put(['set_cavity',cavity_value])
        
        return {}

    @hp.try_call
    def lock_wavelength(self,params):
        lock = params['lock']
        self.iQ.put(['lock_wavelength',lock])
        
        return {}

    @hp.try_call
    def lock_ecd(self,params):
        lock = params['lock']
        if lock:
            lock = "on"
        else:
            lock = "off"
        self.iQ.put(['Lock ECD',lock])
        
        return {}

    @hp.try_call
    def start_scan(self,params):
        self.ns.scan_parameter = params['scan_parameter'][0]
        self.ns.scan_array = params['scan_array']
        self.ns.time_per_step = params['time_per_step'][0]
        self.ns.mass = params['mass'][0]

        self.iQ.put(['scan',()])

        return {}

    @hp.try_call
    def go_to_setpoint(self,params):
        self.ns.parameter = params['parameter'][0]
        self.ns.setpoint = params['setpoint'][0]
        self.iQ.put(['go_to_setpoint',None])
        return {}

    @hp.try_call
    def stop_scan(self,params):
        self.ns.scanning = False
        return {}

    def start_daq(self):
        self.stopFlag.clear()

        args = (self.name,self.data_input, 
                self.iQ, self.mQ,self.stopFlag,
                self.IStoppedFlag, self.ns)
        self.DAQProcess = mp.Process(name = 'daq' + self.name,
                  target=self.acquire,
                  args=args)
        self.DAQProcess.start()

        self.readThread = th.Timer(0, self.read_data).start()

    def read_data(self):
        while not self.stopFlag.is_set():
            self.handle_messages()
            
            data_packet = hp.emptyPipe(self.data_output)
            if not data_packet == []:
                self.data_deque.extend(data_packet)
                self.save_input.send(data_packet)
            
            time.sleep(0.01)

    def handle_messages(self):
        message = hp.GetFromQueue(self.mQ)
        if not message == None:
            self.notify_connectors(message)

    def start_saving(self):
        args = (self.save_output,SAVE_DIR,
                  self.name,self.format)
        self.saveProcess = mp.Process(name = 'save_' + self.name,
                                      target = save_continuously,
                                      args = args)
        self.saveProcess.start()

    def handle_accept(self):
        # we want only one data server or manager
        # to be active at a time
        if len(self.acceptors) == 2:
            print('Data Server and Manager already present! Aborting.')
        super(Artist,self).handle_accept()

