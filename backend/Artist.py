import asyncore
import socket
import multiprocessing as mp
import logging
logging.basicConfig(filename='Artist.log',
                    format='%(asctime)s: %(message)s',
                    level=logging.INFO)
import threading as th
import pandas as pd
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

    def __init__(self, name='', settings={}, PORT=5005, save_data=True):
        super(Artist, self).__init__(PORT, name)
        # self._data = []
        self.saveDir = "Artist_" + self.name
        self.transmitters = []

        # self.data = pd.DataFrame()

        self.settings = dict(counterChannel="/Dev1/ctr1",  # corresponds to PFI3
                             aoChannel="/Dev1/ao0",
                             aiChannel="/Dev1/ai1,/Dev1/ai2",
                             noOfAi=2,
                             clockChannel="/Dev1/PFI1")

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

        # I just realized none of these are actually used outside
        # of the acquire loop at the moment... I don't even see
        # how they should be used given the current 'agnostic'
        # ARTIST architecture

        # Shared memory values: manager
        self.mgr = mp.Manager()
        # Shared scan number
        self.ns = self.mgr.Namespace()
        self.ns.t0 = time.time()
        self.ns.scanNo = -1
        self.ns.on_setpoint = False
        self.ns.scanning = False
        self.save_data = save_data
        self._saveThread = th.Timer(1, self.save).start()

    def InitializeScanning(self):
        self.ns.scanning = False

    @try_call
    def status(self, params):
        return {'format': self.format, 'scanning': self.ns.scanning, 'on_setpoint': self.ns.on_setpoint}

    @try_call
    def data(self, params):
        data = [1] * len(self.ns.format)
        return {'data': data, 'format': self.format, 'scanning': self.ns.scanning, 'on_setpoint': self.ns.on_setpoint}

    @try_call
    def set_scan_number(self, params):
        self.ns.scanNo = params['scan_number'][0]
        return {}

    # def processRequests(self, message):
    #     if message['message']['op'] == 'info':
    #         params = {'format': self.format, 'measuring': self.ns.measuring}
    #     elif message['message']['op'] == 'data':
    #         data = [1] * len(self.ns.format)
    #         params = {'data': data, 'format': self.format, 'measuring': self.ns.measuring}
    #     return add_reply(message, params)
        # else:
        #     print(message['message'])


        # if data == 'info':
        #     info = {'format': self.format, 'measuring': self.ns.measuring}
        #     return info


        # else:
        #     logging.info('Got "{}" instruction from "{}"'.format(data, sender))
        #     if data[0] == 'STOP':
        #         self.StopDAQ()
        #     elif data[0] == 'START':
        #         self.StartDAQ()
        #     elif data[0] == 'RESTART':
        #         self.RestartDAQ()
        #     elif data[0] == 'PAUZE':
        #         self.PauzeDAQ()
        #     elif data[0] == 'RESUME':
        #         self.ResumeDAQ()
        #     elif data[0] == 'CHANGE SETTINGS':
        #         self.changeSet(data[1])
        #     elif data[0] == 'idling':
        #         self.ns.scanNo = -1
        #     elif data[0] == 'Measuring':
        #         self.ns.t0 = time.time()
        #         self.ns.scanNo = data[1]
        #     else:
        #         self.iQ.put(data)

        #     return None

    def StartDAQ(self):
        if not self.stopFlag.is_set():
            logging.warn('DAQ already running.')
            return
        logging.info('Starting DAQ')
        self.stopFlag.clear()

        self.InitializeScanning()
        self.DAQProcess = mp.Process(target=self.acquireFunction,
                                     args=(self.settings,
                                           self.acquire_dQ, self.iQ, self.mQ,
                                           self.contFlag, self.stopFlag,
                                           self.IStoppedFlag, self.ns))
        self.DAQProcess.start()
        time.sleep(1)
        self.format = self.ns.format
        logging.info(self.format)
        self.contFlag.set()
        self.readThread = th.Timer(0, self.ReadData).start()
        logging.info('DAQ Started.')

    def PauzeDAQ(self):
        self.contFlag.clear()

    def ResumeDAQ(self):
        self.contFlag.set()

    def StopDAQ(self):
        if self.stopFlag.is_set():
            logging.warn('DAQ not running.')
            return
        logging.info('Stopping DAQ')
        self.stopFlag.set()
        self.contFlag.clear()
        # wait for the process to stop
        while not self.IStoppedFlag.is_set():
            time.sleep(0.05)
        self.IStoppedFlag.clear()
        self.DAQProcess.terminate()
        logging.info('Stopped DAQ')

    def RestartDAQ(self):
        self.StopDAQ()
        self.StartDAQ()

    def changeSet(self, settings):
        # figure out how to do this later on
        self.settings = settings
        self.RestartDAQ()

    def ReadData(self):
        while not self.stopFlag.is_set():
            message = GetFromQueue(self.mQ, 'message')
            if message is not None:
                logging.warn("Received message \"{}\" from acquire."
                             .format(message))
            ret = emptyPipe(self.dQ)
            if not ret == []:
                print(len(ret))
                if self.save_data:
                    self.saveQ.append(ret)
                for t in self.transmitters:
                    t.dataDQ.append(ret)
            time.sleep(0.01)
            # print('starting')
            # self.readThread = th.Timer(0.01, self.ReadData).start()
        logging.info('Stoppped reading the data')

    def save(self):
        now = time.time()
        l = len(self.saveQ)
        if not l == 0:
            data = [self.saveQ.popleft() for i in range(l)]
            data = convert(data, self.format)
            print(self.name)
            save(data, self.saveDir, self.name)

        # slightly more stable if the save runs every 0.5 seconds,
        # regardless of how long the previous saving took
        wait = abs(min(0, time.time() - now - SAVE_INTERVAL))
        if self.save:
            self._saveThread = th.Timer(wait, self.save).start()


def makeArtist(name='test'):
    if name == 'ABU':
        from acquire.acquire import acquire
        artist = Artist(PORT=5005, name='ABU', save_data=True)
        artist.ns.format = (
            'time', 'scan', 'Counts', 'AOV', 'AIChannel1', 'AIChannel2')
        artist.acquireFunction = acquire
        artist.settings = dict(counterChannel="/Dev1/ctr1",  # corresponds to PFI3
                               aoChannel="/Dev1/ao0",
                               aiChannel="/Dev1/ai1,/Dev1/ai2",
                               noOfAi=2,
                               clockChannel="/Dev1/PFI1")
    elif name == 'CRIS':
        from acquire.acquire import acquire
        artist = Artist(PORT=5005, name='CRIS', save_data=True)
        artist.ns.format = (
            'time', 'scan', 'Counts', 'AOV', 'AIChannel1', 'AIChannel2')
        artist.acquireFunction = acquire
        artist.settings = dict(counterChannel="/Dev1/ctr1",  # corresponds to PFI3
                               aoChannel="/Dev1/ao0",
                               aiChannel="/Dev1/ai1,/Dev1/ai2",
                               noOfAi=2,
                               clockChannel="/Dev1/PFI1")
    elif name == 'laser':
        from acquire.acquireMatisse import acquireMatisse
        artist = Artist(PORT=5004, name='laser', save_data=True)
        artist.ns.format = (
            'time', 'scan', 'setpoint', 'wavenumber', 'wavenumber HeNe')
        artist.acquireFunction = acquireMatisse
    elif name == 'diodes':
        from acquire.acquireDiodes import acquireDiodes
        artist = Artist(PORT=5003, name='diodes', save_data=True)
        artist.ns.format = (
            'time', 'scan', 'AIChannel1', 'AIChannel2', 'AIChannel3')
        artist.acquireFunction = acquireDiodes
        artist.settings = dict(aiChannel="/Dev1/ai1,/Dev1/ai2,/Dev1/ai3",
                               noOfAi=3)
    elif name == 'M2':
        from acquire_files.acquireM2 import acquireM2
        artist = Artist(PORT=5002, name='M2', save_data=True)
        artist.ns.format = ()
        artist.acquireFunction = acquireM2
    return artist

if __name__ == '__main__':

    name = input('Name?')
    artist = makeArtist(name=name)
    t0 = th.Timer(1, artist.StartDAQ).start()
    asyncore.loop(0.001)
