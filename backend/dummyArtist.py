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
    from connectors import Connector, Acceptor
except:
    from backend.Helpers import *
    from backend.connectors import Connector, Acceptor
from dummyacquire import acquire

SAVE_INTERVAL = 2


# Some exploratory code to understand a bit better how to make the ARTIST
class Artist(asyncore.dispatcher):

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
        super(Artist, self).__init__()
        self.port = PORT
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        # self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self.bind(('', self.port))
        self.listen(5)
        logging.info('Listening on port {}'.format(self.port))

        self.name = name
        self._data = []
        self.saveDir = "Artist_" + name
        self.transmitters = []

        # dictionary holding the initial settings for the hardware
        self.settings = dict(counterChannel= "/Dev1/ctr1", # corresponds to PFI3
                             aoChannel="/Dev1/ao0",
                             aiChannel="/Dev1/ai1,/Dev1/ai2",
                             noOfAi=2,
                             clockChannel="/Dev1/PFI1",
                             timePerStep=1,
                             laser='CW Laser Voltage Scan',
                             cristalMode=True,
                             clearMode=True)
        self.format = ('',)
        self.data = pd.DataFrame()

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
        self.ns.measuring = False
        self.ns.format = ('time', 'scan', 'Counts', 'AOV', 'AIChannel1', 'AIChannel2')
        self.save_data = save_data
        self._saveThread = th.Timer(1, self.save).start()

    def InitializeScanning(self):
        self.ns.scanning = False

    def processRequests(self, sender, data):
        if data == 'info':
            info = {'format': self.format, 'measuring': self.ns.measuring}
            return info

        elif data == 'data':
            data = []
            l = len(sender.dataDQ)
            if not l == 0:
                data = [sender.dataDQ.popleft() for i in range(l)]
            return {'data':data, 'format': self.format, 'measuring': self.ns.measuring}

        else:
            logging.info('Got "{}" instruction'.format(data))
            if data[0] == 'STOP':
                self.StopDAQ()
            elif data[0] == 'START':
                self.StartDAQ()
            elif data[0] == 'RESTART':
                self.RestartDAQ()
            elif data[0] == 'PAUZE':
                self.PauzeDAQ()
            elif data[0] == 'RESUME':
                self.ResumeDAQ()
            elif data[0] == 'CHANGE SETTINGS':
                self.changeSet(data[1])
            elif data[0] == 'idling':
                self.ns.scanNo = -1
            elif data[0] == 'Measuring':
                self.ns.t0 = time.time()
                self.ns.scanNo = data[1]
            else:
                self.iQ.put(data)

            return None

    def StartDAQ(self):
        if not self.stopFlag.is_set():
            logging.warn('DAQ already running.')
            return
        logging.info('Starting DAQ')
        self.stopFlag.clear()

        self.InitializeScanning()
        self.DAQProcess = mp.Process(target=acquire,
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
                print('Got data')
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
            save(data, self.saveDir, self.name)

        # # slightly more stable if the save runs every 0.5 seconds,
        # # regardless of how long the previous saving took
        wait = abs(min(0, time.time() - now - SAVE_INTERVAL))
        if self.save:
            self._saveThread = th.Timer(wait, self.save).start()

    def writeable(self):
        return False

    def readable(self):
        return True

    def handle_accept(self):
        pair = self.accept()
        if pair is not None:
            sock, addr = pair
            try:
                sender = self.get_sender_ID(sock)
                logging.info(sender)
            except:
                logging.warn('Sender {} did not send proper ID'.format(addr))
                return
            if sender == 'M_to_A':
                self.receiver = Acceptor(sock,
                                         callback=self.processRequests,
                                         onCloseCallback=self.removeReceiver,
                                         t=self.name)
            elif sender == 'DS_to_A':
                self.transmitters.append(Acceptor(sock,
                                                  callback=self.processRequests,
                                                  onCloseCallback=self.removeTransmitter,
                                                  t=self.name))
            else:
                logging.error('Sender {} named {} not understood'
                              .format(addr, sender))
                return
            logging.info('Accepted {} as {}'.format(addr, sender))

    def removeReceiver(self, receiver):
        self.receiver = None

    def removeTransmitter(self, transmitter):
        self.transmitters.remove(transmitter)

    def get_sender_ID(self, sock):
        now = time.time()
        while time.time() - now < 5:  # Tested; raises RunTimeError after 5 s
            try:
                sender = sock.recv(1024).decode('UTF-8')
                break
            except:
                pass
        else:
            raise
        return sender

    def handle_close(self):
        logging.info('Closing Artist')
        super(Artist, self).handle_close()

def makeArtist(name='test1', PORT=5005, save_data=True):
    return Artist(name=name, PORT=PORT, save_data=save_data)


def start():
    while True:
        asyncore.loop(count=1)
        time.sleep(0.01)


def main(port,name):
    a = makeArtist(name=name, PORT=port, save_data=True)
    t0 = th.Timer(1, a.StartDAQ).start()
    asyncore.loop(0.001)


if __name__ == '__main__':
    main(5005,'ABU')
