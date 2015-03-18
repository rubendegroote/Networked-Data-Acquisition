import asynchat
import asyncore
import socket
import multiprocessing as mp
import logging
import threading as th
import pickle
import pandas as pd
import time
from acquire import acquire
from Helpers import *
from collections import deque

# logging.basicConfig(filename='example.log', level=logging.DEBUG)
logging.basicConfig(format='%(asctime)s: %(message)s',
                    level=logging.INFO)

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

    def __init__(self, name='', settings={}, PORT=5005, save=True):
        super(Artist, self).__init__()
        self.port = PORT
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        # self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self.bind(('', self.port))
        self.listen(100)
        logging.info('Listening on port {}'.format(self.port))

        self.name = name
        self._data = []
        self.saveDir = "Artist_" + name
        self.transmitters = []

        # dictionary holding the initial settings for the hardware
        self.settings = settings
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
        self.ns.scanNo = 0

        # are we scanning?
        self.ns.scanning = False
        self.ns.format = ('time', 'scan', 'x', 'y', 'z')

        self.save_data = save
        self._saveThread = th.Timer(1, self.save).start()

    def InitializeScanning(self):
        self.ns.scanning = False

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
        self.contFlag.set()
        for t in self.transmitters:
            t.format = self.format
            logging.info(t.format)
        print(self.format)
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
                if self.save_data:
                    self.saveQ.append(ret)
                for t in self.transmitters:
                    t.chunkQ.append(ret)
            time.sleep(0.01)
            # print('starting')
            # self.readThread = th.Timer(0.01, self.ReadData).start()
        logging.info('Stoppped reading the data')

    def save(self):
        now = time.time()
        l = len(self.saveQ)
        if not l == 0:
            data = [self.saveQ.popleft() for i in range(l)]
            data = flatten(data)
            data = mass_concat(data, self.format)
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
            if sender == 'Manager':
                self.receiver = InstructionReceiver(sock, self)
                sock.send(self.name.encode('UTF-8'))
            elif sender == 'Server':
                self.transmitters.append(DataTransmitter(sock, self.format))
                sock.send(self.name.encode('UTF-8'))
            else:
                logging.error('Sender {} named {} not understood'
                              .format(addr, sender))
                return
            logging.info('Accepted {} as {}'.format(addr, sender))

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


class InstructionReceiver(asynchat.async_chat):

    def __init__(self, sock, artist, *args, **kwargs):
        super(InstructionReceiver, self).__init__(sock=sock, *args, **kwargs)
        self.instruction = b""
        self.set_terminator('END_MESSAGE'.encode('UTF-8'))

        # is this the proper way to do it?
        self.iQ = artist.iQ
        self.StopDAQ = artist.StopDAQ
        self.StartDAQ = artist.StartDAQ
        self.RestartDAQ = artist.RestartDAQ
        self.PauzeDAQ = artist.PauzeDAQ
        self.ResumeDAQ = artist.ResumeDAQ
        self.changeSet = artist.changeSet

    def found_terminator(self):
        instruction = self.decode_instruction()
        logging.info('Got "{}" instruction'.format(instruction))
        if instruction[0] == 'STOP':
            self.StopDAQ()
        elif instruction[0] == 'START':
            self.StartDAQ()
        elif instruction[0] == 'RESTART':
            self.RestartDAQ()
        elif instruction[0] == 'PAUZE':
            self.PauzeDAQ()
        elif instruction[0] == 'RESUME':
            self.ResumeDAQ()
        elif instruction[0] == 'CHANGE SETTINGS':
            self.changeSet(instructions[1])
        else:
            self.iQ.put(instruction)

    def decode_instruction(self):
        instr = pickle.loads(self.instruction)
        self.instruction = b""
        return instr

    def collect_incoming_data(self, instruction):
        self.instruction += instruction

    def handle_close(self):
        logging.info('Closing InstructionReceiver')
        super(InstructionReceiver, self).handle_close()


class DataTransmitter(asynchat.async_chat):

    def __init__(self, sock, format, *args, **kwargs):
        super(DataTransmitter, self).__init__(sock=sock, *args, **kwargs)
        self.set_terminator('END_MESSAGE'.encode('UTF-8'))
        self.format = format

        self.chunkQ = deque()

    def found_terminator(self):
        data = []
        # while len(data) == 0:
        l = len(self.chunkQ)
        if not l == 0:
            data = [self.chunkQ.popleft() for i in range(l)]
            data = flatten(data)
        self.transmit(pickle.dumps(data))

    def transmit(self, data):
        self.push(pickle.dumps(self.format))
        self.push('STOP_DATA'.encode('UTF-8'))
        self.push(data)
        self.push('STOP_DATA'.encode('UTF-8'))

    def collect_incoming_data(self, message):
        pass

    def handle_close(self):
        logging.info('Closing DataTransmitter')
        super(DataTransmitter, self).handle_close()


def makeArtist(name='test1', PORT=5005, save=True):
    return Artist(name=name, PORT=PORT, save=save)


def start():
    while True:
        asyncore.loop(count=1)
        time.sleep(0.02)


def main():
    port = int(input('PORT?'))
    name = input('Name?')
    a = makeArtist(name=name, PORT=port, save=True)
    t0 = th.Timer(1, a.StartDAQ).start()
    asyncore.loop(0.001)


if __name__ == '__main__':
    main()
