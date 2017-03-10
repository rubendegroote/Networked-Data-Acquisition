import backend.Helpers as hp
from backend.save import *
from backend.connectors import Connector, Acceptor
import backend.logbook as lb
from backend.dispatcher import Dispatcher

import os,sys
import multiprocessing as mp
from collections import deque
import threading as th
import configparser

from backend.acquire_files.acquisition import acquire

CONFIG_PATH = os.getcwd() + "\\Config files\\config.ini"

class Device(Dispatcher):
    ### get configuration details
    config_parser = configparser.ConfigParser()
    config_parser.read(CONFIG_PATH)

    save_path = config_parser['paths']['data_path']
    time_offset = int(config_parser['other']['time_offset'])
    def __init__(self, name=''):
        PORT = int(self.config_parser['ports'][name])
        super(Device, self).__init__(PORT, name)
        self.acquire = acquire

        # instructions queue:
        # Controller -> InstructionReceiver -> acquire
        self.iQ = mp.Queue()
        # message queue
        self.mQ = mp.Queue()
        # data pipe
        self.data_output,self.data_input = mp.Pipe(duplex=False)

        # Shared memory values: manager
        self.mgr = mp.Manager()
        # Shared scan number
        self.ns = self.mgr.Namespace()
        self.ns.scan_number = -1
        self.ns.mass = 0
        self.ns.on_setpoint = True
        self.ns.scanning = False
        self.ns.progress = 0
        self.ns.status_data = {}
        self.ns.clock_offset = 0
        self.ns.format = ()
        self.ns.refresh_time = 100

        self.data_deque = deque()

        # stop flag for the acquisition
        self.stopFlag = mp.Event()
        self.stopFlag.set()

        # read data flag for the acquisition
        read = self.config_parser['read_data'][name] == 'yes'
        self.readDataFlag = mp.Event()
        self.readDataFlag.clear()
        if read:
            self.readDataFlag.set()

        # save flag for the device
        save = self.config_parser['save_data'][name] == 'yes'
        self.saveFlag = mp.Event()
        self.saveFlag.clear()
        if save:
            self.saveFlag.set()

        # save stream flag for the device
        save_stream = self.config_parser['save_stream'][name] == 'yes'
        self.saveStreamFlag = mp.Event()
        self.saveStreamFlag.clear()
        if save_stream:
            self.saveStreamFlag.set()

        self.start_daq()
        
        # save pipe: send data to be saved
        self.save_output,self.save_input = mp.Pipe(duplex=False)
        ## wait for the hardware to be initialized and for it to
        ## report the format
        while self.ns.format == tuple():
            time.sleep(1)

        self.start_saving()

    def stop(self):
        self.stopFlag.set()
        self.interfaceThread.join()
        if self.saveFlag.is_set():
            if not self.name == 'DSS':
                self.saveProcess.terminate()
        self.DAQProcess.terminate()
        super(Device,self).stop()

    def start_daq(self):
        self.stopFlag.clear()

        args = (self.name,self.data_input,
                self.iQ, self.mQ,self.stopFlag,
                self.readDataFlag,self.ns)
        self.DAQProcess = mp.Process(name = 'daq' + self.name,
                  target=self.acquire,
                  args=args)
        self.DAQProcess.start()

        self.interfaceThread = th.Timer(0, self.interface)
        self.interfaceThread.start()

    def interface(self):
        while not self.stopFlag.is_set():
            self.handle_messages()
            if self.readDataFlag.is_set():
                self.read_data()
            time.sleep(0.01)
            
    def read_data(self):
        data_packet = hp.emptyPipe(self.data_output)
        if not data_packet == []:
            for dp in data_packet:
                self.data_deque.extend(dp)
            if self.saveFlag.is_set():
                self.save_input.send(data_packet)

    def handle_messages(self):
        message = hp.GetFromQueue(self.mQ)
        if not message == None:
            self.notify_connectors(message)
            
    def start_saving(self):
        args = (self.save_output,self.save_path,
                  self.name,self.ns.format,
                  self.saveFlag,self.saveStreamFlag)
        self.saveProcess = mp.Process(name = 'save_' + self.name,
                                      target = save_continuously,
                                      args = args)
        self.saveProcess.start()

    @hp.try_call
    def change_save_mode(self,params):
        if params['save']:
            self.saveFlag.set()
        else:
            self.saveFlag.clear()
        
        if params['save_stream']:
            self.saveStreamFlag.set()
        else:
            self.saveStreamFlag.clear()

    @hp.try_call
    def status(self, params):
        self.ns.mass = params['mass'][0]
        self.ns.scan_number = params['scan_number'][0]
        self.ns.proton_info = params['proton_info']

        return {'scan_number': self.ns.scan_number,
                'scanning': self.ns.scanning,
                'on_setpoint': self.ns.on_setpoint,
                'progress': self.ns.progress,
                'mass':self.ns.mass,
                'status_data':self.ns.status_data,
                'refresh_time':self.ns.refresh_time}

    @hp.try_call
    def data(self, params):
        if self.readDataFlag.is_set():
            t0 = params['t0']
            self.ns.clock_offset = (time.time()-self.time_offset) - t0
            # Recall there is only one data server, so this works
            l = len(self.data_deque)
            data = [list(self.data_deque.popleft()) for _i in range(l)]
            return {'save':self.saveFlag.is_set(),
                    'save_stream':self.saveStreamFlag.is_set(),
                    'data': data,
                    'mass':self.ns.mass}
        else:
            return {}

    @hp.try_call
    def execute_instruction(self,params):
        instruction = params['instruction']
        self.iQ.put([instruction,params['arguments']])
        return {}

    @hp.try_call
    def initial_information(self,params):
        return {'format': self.ns.format,
                'write_params':self.ns.write_params}

    def handle_accept(self):
        super(Device,self).handle_accept()

