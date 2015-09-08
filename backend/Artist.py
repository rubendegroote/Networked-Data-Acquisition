import asyncore
import socket
import multiprocessing as mp
import threading as th
import pandas as pd
import numpy as np
import time
from collections import deque

try:
    from Helpers import *
except:
    from backend.Helpers import *

try:
    from save import *
except:
    from backend.save import *

try:
    from connectors import Connector, Acceptor
except:
    from backend.connectors import Connector, Acceptor

from dispatcher import Dispatcher



# Some exploratory code to understand a bit better how to make the ARTIST
class Artist(Dispatcher):

    """
    Parameters
    ----------
    name: str
        The name of this ARTIST
    settings: dict
        The dictionary with initial config settings for
        the DAQ process

    Attributes
    ----------
    dQ: multiprocessing Queue
        A queue that is used for communicating data with the
        acquisition process
    iQ: multiprocessing Queue
        A queue that is used for communicating instructions with the
        acquisition process
    mQ: multiprocessing Queue
        A queue that is used for communicating error messages with the
        acquisition process
    contFlag: multiprocessing Event
        An event that is set when the DAQ process should continue,
        is cleared when it should pause
    stopFlag: multiprocessing Event
        An event that is set when the DAQ process should stop
    running: bool
        A boolean that indicates if the DAQ process is running

    data: dict
        A dictionary with the data
    """

    def __init__(self, name='', PORT=5005, acquireFunction=None,
            save_data=True,format = tuple(),settings={}):
        super(Artist, self).__init__(PORT, name)
        # self._data = []
        self.saveDir = "C:\\Data\\"

        self.settings = settings
        self.acquireFunction = acquireFunction

        # instructions queue:
        # Manager -> InstructionReceiver -> acquire
        self.iQ = mp.Queue()
        # message queue: acquire -> ARTIST
        self.mQ = mp.Queue()
        # data pipe: acquire -> ARTIST
        self.data_output,self.data_input = mp.Pipe(duplex=False)

        # save pipe: send data to be saved
        self.save_output,self.save_input = mp.Pipe(duplex=False)

        # holding flag for the acquisition
        self.contFlag = mp.Event()
        self.contFlag.clear()
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
        self.ns.t0 = time.time()
        self.ns.scanNo = -1
        self.ns.on_setpoint = False
        self.ns.scanning = False
        self.save_data = save_data
        self.format = format
        self.ns.format = self.format

        self.data_deque = deque()

        self.start_saving()
        self.start_daq()

    def InitializeScanning(self):
        self.ns.scanning = False

    @try_call
    def status(self, params):
        return {'format': self.format, 'scanning': self.ns.scanning, 'on_setpoint': self.ns.on_setpoint}

    @try_call
    def data(self, params):
        # Recall there is only one data server, so this works
        l = len(self.data_deque)
        data = [self.data_deque.popleft() for _i in range(l)]
        print('sent ', len(data))
        return {'data': data, 'format': self.format}

    @try_call
    def set_scan_number(self, params):
        self.ns.scanNo = params['scan_number'][0]
        return {}

    def start_daq(self):
        self.stopFlag.clear()

        self.InitializeScanning()
        self.DAQProcess = mp.Process(target=self.acquireFunction,
                                     args=(self.settings,
                                           self.data_input, self.iQ, self.mQ,
                                           self.contFlag, self.stopFlag,
                                           self.IStoppedFlag, self.ns))
        self.DAQProcess.start()
        self.contFlag.set()
        self.readThread = th.Timer(0, self.read_data).start()

    def start_saving(self):
        self.saveProcess = mp.Process(target = save_continuously,
                                      args = (self.save_output,self.saveDir,
                                              self.name,self.format))
        self.saveProcess.start()

    def pauze_daq(self):
        self.contFlag.clear()

    def resume_daq(self):
        self.contFlag.set()

    def stop_daq(self):
        self.stopFlag.set()
        self.contFlag.clear()
        # wait for the process to stop
        self.IStoppedFlag.clear()
        self.DAQProcess.terminate()

    def restart_daq(self):
        self.stop_daq()
        self.start_daq()

    def read_data(self):
        while not self.stopFlag.is_set():
            message = GetFromQueue(self.mQ)
            ret = emptyPipe(self.data_output)
            if not ret == []:
                self.data_deque.extend(ret)
                if self.save_data:
                    self.save_input.send(ret)
            time.sleep(0.01)

    def handle_accept(self):
        # we want only one data server or manager
        # to be active at a time
        if len(self.acceptors) == 2:
            print('Data Server and Manager already present! Aborting.')
        super(Artist,self).handle_accept()

def makeArtist(name='test'):
    if name == 'ABU' or name == 'CRIS':
        from acquire_files.acquire import acquire as aq
        from acquire_files.acquire import FORMAT
        settings = dict(counterChannel="/Dev1/ctr1",  # corresponds to PFI3
                               aoChannel="/Dev1/ao0",
                               aiChannel="/Dev1/ai1,/Dev1/ai2",
                               noOfAi=2,
                               clockChannel="/Dev1/PFI1")
        PORT = 6005
    
    elif name == 'laser':
        from acquire_files.acquireMatisse import acquireMatisse as aq
        from acquire_files.acquireMatisse import FORMAT
        settings = dict()
        PORT = 6004
    
    elif name == 'diodes':
        from acquire_files.acquireDiodes import acquireDiodes as aq
        from acquire_files.acquireDiodes import FORMAT
        settings = dict(aiChannel="/Dev1/ai1,/Dev1/ai2,/Dev1/ai3",
                               noOfAi=3)
        PORT = 6003
    
    elif name == 'M2':
        from acquire_files.acquireM2 import acquireM2 as aq
        from acquire_files.acquireM2 import FORMAT
        settings = dict()
        PORT = 6002

    artist = Artist(PORT=PORT, name=name, save_data=True,
        format=FORMAT,acquireFunction=aq,settings=settings)
    
    return artist
