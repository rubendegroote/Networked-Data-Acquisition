import asynchat
import asyncore
from collections import deque
from datetime import datetime
import logging
import pickle
import socket
import threading as th
import time
import numpy as np
import pandas as pd
from bokeh.embed import autoload_server
try:
    from Helpers import *
except:
    from backend.Helpers import *


logging.basicConfig(format='%(asctime)s: %(message)s',
                    level=logging.INFO)

SAVE_INTERVAL = 0.05
SHARED = ['scan','time']

class DataServer():
    def __init__(self, artists=[], save=False, remember=True):
        self._readers = {}
        self.saveDir = "Server"
        self.dQs = {}
        # self.plot = render_plot()
        for address in artists:
            self.addReader(address)
        self._saveThread = th.Timer(1, self.save).start()
        self.save_data = save
        self.remember = remember
        if remember:
            self._data = pd.DataFrame()
            self._data_current_scan = pd.DataFrame()

        self.looping = True
        t = th.Thread(target = self.start).start()

    def start(self):
        while self.looping:
            asyncore.loop(count=1)
            time.sleep(0.01)

    def stop(self):
        self.looping = False


    def addReader(self, address=None):
        if address is None:
            logging.warning('provide IP address and PORT')
            return
        logging.info('Adding reader')
        try:
            reader = ArtistReader(IP=address[0], PORT=int(address[1]))
            self._readers[reader.artistName] = reader
            self.dQs[reader.artistName] = deque()
            self._readers[reader.artistName].dQ = self.dQs[reader.artistName]
        except Exception as e:
            logging.info('Connection failed')

    def save(self):
        # This is not doing it right! Data files of all receivers
        # should be merged before saving!
        # should be better now, but never run before!!!
        now = time.time()
        new_data = pd.DataFrame()
        for name, reader in self._readers.items():
            dQ = self.dQs[name]
            l = len(dQ)
            if not l == 0:
                data = [dQ.popleft() for i in range(l)]
                data = mass_concat(flatten(data), format=reader._format)
                if self.save_data:
                    save(data,self.saveDir,reader.artistName)
                new_data = new_data.append(data)

        if not len(new_data) == 0:
            if self.remember:
                self.extractMemory(new_data)

        # slightly more stable if the save runs every 0.5 seconds,
        # regardless of how long the previous saving took
        wait = abs(min(0, time.time() - now - SAVE_INTERVAL))
        if self.looping:
            self._saveThread = th.Timer(wait, self.save).start()

    def extractMemory(self, new_data):
        self._data = self._data.append(new_data)
        # save the current scan in memory!
        groups = self._data.groupby('scan')
        # not sure this works - is groups a dictionary?
        # self._data_current_scan = groups[max(groups.keys)]
        # save last 10.000 data points
        self._data = self._data[-5000:]

        # self.bin_current()
        # print(self._data)

    def bin_current(self):
        # some stuff about binning the current data in some
        # XY format with certain X steps 'n stuff
        pass


class ArtistReader(asynchat.async_chat):

    def __init__(self, IP='KSF402', PORT=5005):
        super(ArtistReader, self).__init__()
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        # self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self.connect((IP, PORT))
        time.sleep(0.1)
        self.send('Server'.encode('UTF-8'))

        self.artistName = self.wait_for_connection()

        self._data = pd.DataFrame()
        self._buffer = b''
        self.set_terminator('STOP_DATA'.encode('UTF-8'))
        self.push('Next'.encode('UTF-8') + 'END_MESSAGE'.encode('UTF-8'))
        self.total = 0

    def wait_for_connection(self):
        # Wait for connection to be made with timeout
        success = False
        now = time.time()
        while time.time() - now < 5:  # Tested: raises RunTimeError after 5 s
            try:
                name = self.recv(1024).decode('UTF-8')
                success = True
                break
            except:
                pass
        if not success:
            raise

        return name

    def collect_incoming_data(self, data):
        self._buffer += data

    def found_terminator(self):
        buff = self._buffer
        self.total += len(self._buffer)
        # try:
        #     print(int(self.total/(time.time() - self.now))/1000000)
        # except:
        #     self.now = time.time()

        self._buffer = b''
        data = pickle.loads(buff)
        if type(data) == tuple:
            self._format = tuple([self.artistName + d if d not in SHARED else d for d in data])
        else:
            if not data == []:
                self.dQ.append(data)
            self.push('Next'.encode('UTF-8') + 'END_MESSAGE'.encode('UTF-8'))


def makeServer(channel=[('KSF402', 5005)], save=True, remember=True):
    return DataServer(channel, save, remember)


def main():
    channels = input('IP,PORTS?').split(";")
    channels = [c.split(",") for c in channels]
    d = makeServer(channels, save=int(input('save?'))==1, remember=int(input('remember?'))==1)

    t = th.Thread(target = start).start()

if __name__ == '__main__':
    main()
