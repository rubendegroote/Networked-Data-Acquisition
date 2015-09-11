import sys
from Helpers import *
from save import *
from connectors import Connector, Acceptor
import logbook as lb
from dispatcher import Dispatcher
import multiprocessing as mp
from collections import deque
import threading as th

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
    stopFlag: multiprocessing Event
        An event that is set when the DAQ process should stop
    running: bool
        A boolean that indicates if the DAQ process is running

    data: dict
        A dictionary with the data
    """

    def __init__(self, name='', PORT=5005, acquireFunction=None,
            save_data=True,format = tuple()):
        super(Artist, self).__init__(PORT, name)
        # self._data = []
        self.saveDir = "C:\\Data\\"

        self.acquireFunction = acquireFunction

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
        self.ns.on_setpoint = False
        self.ns.scanning = False
        self.ns.current_position = 0
        self.ns.progress = 0
        self.ns.parameter = ''
        self.ns.setpoint = 0
        self.format = format
        self.ns.format = self.format

        self.data_deque = deque()

        self.start_daq()

        self.save_data = save_data
        if save_data:
            # save pipe: send data to be saved
            self.save_output,self.save_input = mp.Pipe(duplex=False)
            self.start_saving()

    def InitializeScanning(self):
        self.ns.scanning = False

    @try_call
    def status(self, params):
        return {'format': self.format,
                'scanning': self.ns.scanning,
                'on_setpoint': self.ns.on_setpoint,
                'progress': self.ns.progress,
                'scan_number': self.ns.scan_number}

    @try_call
    def data(self, params):
        # Recall there is only one data server, so this works
        l = len(self.data_deque)
        data = [self.data_deque.popleft() for _i in range(l)]
        return {'data': data, 'format': self.format}

    @try_call
    def set_scan_number(self, params):
        self.ns.scan_number = params['scan_number'][0]
        return {}

    @try_call
    def start_scan(self,params):
        self.ns.scan_parameter = params['scan_parameter'][0]
        self.ns.scan_array = params['scan_array']
        self.ns.time_per_step = params['time_per_step'][0]
        self.iQ.put('scan')

        return {}

    @try_call
    def go_to_setpoint(self,params):
        self.ns.on_setpoint = False
        self.ns.parameter = params['parameter'][0]
        self.ns.setpoint = params['setpoint'][0]
        self.iQ.put('go_to_setpoint')
        return {}

    @try_call
    def stop_scan(self,params):
        self.ns.scanning = False
        return {}

    def start_daq(self):
        self.stopFlag.clear()

        self.InitializeScanning()
        self.DAQProcess = mp.Process(name = 'daq' + self.name,
                                      target=self.acquireFunction,
                                      args=(self.name,
                                           self.data_input, self.iQ, self.mQ, 
                                           self.stopFlag,
                                           self.IStoppedFlag, self.ns))
        self.DAQProcess.start()

        self.readThread = th.Timer(0, self.read_data).start()

    def stop_daq(self):
        self.stopFlag.set()
        # wait for the process to stop
        self.IStoppedFlag.clear()
        self.DAQProcess.terminate()

    def restart_daq(self):
        self.stop_daq()
        self.start_daq()

    def read_data(self):
        while not self.stopFlag.is_set():
            self.handle_messages()
            ret = emptyPipe(self.data_output)
            if not ret == []:
                self.data_deque.extend(ret)
                if self.save_data:
                    self.save_input.send(ret)

            time.sleep(0.01)

    def handle_messages(self):
        message = GetFromQueue(self.mQ)
        if not message == None:
            self.notify_connectors(message)

    def start_saving(self):
        self.saveProcess = mp.Process(name = 'save_' + self.name,
                                      target = save_continuously,
                                      args = (self.save_output,self.saveDir,
                                              self.name,self.format))
        self.saveProcess.start()

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
        from acquire_files.acquisition import hardware_map,acquire
        PORT = 6002
        FORMAT = hardware_map['M2'].format
        aq = acquire

    # elif name == 'M2':
    #     from acquire_files.acquireM2 import acquireM2 as aq
    #     from acquire_files.acquireM2 import FORMAT
    #     settings = dict()
    #     PORT = 6002

    artist = Artist(name=name,PORT=PORT,acquireFunction=aq,
        save_data=True,format=FORMAT)
    
    return artist
