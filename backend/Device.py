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

from backend.acquire_files.acquisition import format_map,write_params_map,acquire

CONFIG_PATH = os.getcwd() + "\\config.ini"

class Device(Dispatcher):
    ### get configuration details
    config_parser = configparser.ConfigParser()
    config_parser.read(CONFIG_PATH)
    save_path = config_parser['paths']['data_path']
    time_offset = int(config_parser['other']['time_offset'])
    def __init__(self, name='', save_data = True):
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
        self.ns.scan_number = -1
        self.ns.mass = 0
        self.ns.on_setpoint = True
        self.ns.scanning = False
        self.ns.calibrated = False
        self.ns.progress = 0
        self.ns.status_data = {}

        self.ns.clock_offset = 0

        self.format = format_map[name]
        self.ns.format = self.format
        
        self.write_params = write_params_map[name]

        self.data_deque = deque()

        self.start_daq()

        # save pipe: send data to be saved
        self.save_output,self.save_input = mp.Pipe(duplex=False)
        # self.start_saving()

    def stop(self):
        self.stopFlag.set()
        self.readThread.join()
        # self.saveProcess.terminate()
        self.DAQProcess.terminate()
        super(Device,self).stop()

    def start_daq(self):
        self.stopFlag.clear()

        args = (self.name,self.data_input,
                self.iQ, self.mQ,self.stopFlag,
                self.IStoppedFlag, self.ns)
        self.DAQProcess = mp.Process(name = 'daq' + self.name,
                  target=self.acquire,
                  args=args)
        self.DAQProcess.start()

        self.readThread = th.Timer(0, self.read_data)
        self.readThread.start()

    def read_data(self):
        while not self.stopFlag.is_set():
            self.handle_messages()

            data_packet = hp.emptyPipe(self.data_output)
            if not data_packet == []:
                self.data_deque.extend(data_packet)
                # self.save_input.send(data_packet)

            time.sleep(0.01)

    def handle_messages(self):
        message = hp.GetFromQueue(self.mQ)
        if not message == None:
            self.notify_connectors(message)
            
    def start_saving(self):
        args = (self.save_output,self.save_path,
                  self.name,self.format)
        self.saveProcess = mp.Process(name = 'save_' + self.name,
                                      target = save_continuously,
                                      args = args)
        self.saveProcess.start()

    @hp.try_call
    def status(self, params):
        self.ns.mass = params['mass'][0]
        if not params['scan_number'][0] == self.ns.scan_number and \
                 self.ns.scan_number == -1:
            self.ns.calibrated = False
        self.ns.scan_number = params['scan_number'][0]

        return {'format': self.format,
                'write_params':self.write_params,
                'scan_number': self.ns.scan_number,
                'scanning': self.ns.scanning,
                'calibrated': self.ns.calibrated,
                'on_setpoint': self.ns.on_setpoint,
                'progress': self.ns.progress,
                'mass':self.ns.mass,
                'status_data':self.ns.status_data}

    @hp.try_call
    def data(self, params):
        t0 = params['t0']
        self.ns.clock_offset = (time.time()-self.time_offset) - t0
        # Recall there is only one data server, so this works
        l = len(self.data_deque)
        data = [self.data_deque.popleft() for _i in range(l)]
        return {'data': data,
                'format': self.format}

    @hp.try_call
    def execute_instruction(self,params):
        instruction = params['instruction']
        self.iQ.put([instruction,params['arguments']])
        return {}

    def handle_accept(self):
        # we want only one data server or controller
        # to be active at a time
        if len(self.acceptors) == 2:
            print('Data Server and Controller already present! Aborting.')
        super(Device,self).handle_accept()
