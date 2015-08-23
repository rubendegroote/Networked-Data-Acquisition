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
    from connectors import Connector, Acceptor
except:
    from backend.connectors import Connector, Acceptor

from dispatcher import Dispatcher

SAVE_INTERVAL = 2


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
        self.saveDir = "Artist_" + self.name

        self.settings = settings
        self.acquireFunction = acquireFunction

        # instructions queue:
        # Manager -> InstructionReceiver -> acquire
        self.iQ = mp.Queue()
        # message queue: acquire -> ARTIST
        self.mQ = mp.Queue()
        # data queue: acquire -> ARTIST
        dQ = mp.Pipe(duplex=False)
        self.dQ = dQ[0]
        self.acquire_dQ = dQ[1]

        # save queue: send data to be saved
        self.saveQ = deque()

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

        self.data_list = []

        self._saveThread = th.Timer(1, self.save).start()

        self.start_daq()

    def InitializeScanning(self):
        self.ns.scanning = False

    @try_call
    def status(self, params):
        return {'format': self.format, 'scanning': self.ns.scanning, 'on_setpoint': self.ns.on_setpoint}

    @try_call
    def data(self, params):
        # only one data server allowed at the moment!
        l = len(self.data_list)
        data = self.data_list[:l]
        self.data = self.data[l:] ### should be replaced with e.g. deque
                                  ### popping to make thread-safe
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
                                           self.acquire_dQ, self.iQ, self.mQ,
                                           self.contFlag, self.stopFlag,
                                           self.IStoppedFlag, self.ns))
        self.DAQProcess.start()
        self.contFlag.set()
        self.readThread = th.Timer(0, self.read_data).start()

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
            ret = emptyPipe(self.dQ)
            if not ret == []:
                self.data_list.extend(ret)
            # if self.save_data:
            ##     save data!!
            time.sleep(0.01)

    def save(self):
        now = time.time()
        l = len(self.saveQ)
        if not l == 0:
            data = [self.saveQ.popleft() for i in range(l)]
            data = convert(data, self.format)
            save(data, self.saveDir, self.name)

        # slightly more stable if the save runs every 0.5 seconds,
        # regardless of how long the previous saving took
        wait = abs(min(0, time.time() - now - SAVE_INTERVAL))
        if self.save:
            self._saveThread = th.Timer(wait, self.save).start()

def makeArtist(name='test'):
    if name == 'ABU' or name == 'ABU':
        from acquire_files.acquire import acquire as aq
        from acquire_files.acquire import FORMAT
        settings = dict(counterChannel="/Dev1/ctr1",  # corresponds to PFI3
                               aoChannel="/Dev1/ao0",
                               aiChannel="/Dev1/ai1,/Dev1/ai2",
                               noOfAi=2,
                               clockChannel="/Dev1/PFI1")
    
    elif name == 'laser':
        from acquire_files.acquireMatisse import acquireMatisse as aq
        from acquire_files.acquireMatisse import FORMAT
        settings = dict()
    
    elif name == 'diodes':
        from acquire_files.acquireDiodes import acquireDiodes as aq
        from acquire_files.acquireDiodes import FORMAT
        settings = dict(aiChannel="/Dev1/ai1,/Dev1/ai2,/Dev1/ai3",
                               noOfAi=3)
    
    elif name == 'M2':
        from acquire_files.acquireM2 import acquireM2 as aq
        from acquire_files.acquireM2 import FORMAT
        settings = dict()

    artist = Artist(PORT=5002, name=name, save_data=True,
        format=FORMAT,acquireFunction=aq,settings=settings)
    
    return artist
