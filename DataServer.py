import asyncore
import asynchat
import socket
import multiprocessing as mp
import threading as th
import pickle
import numpy as np
import pandas as pd
from Helpers import *
from collections import deque

SAVE_INTERVAL = 0.1

class DataServer():
    def __init__(self,artists=[],save=True,remember=True):
        self._readers = {}
        self.saveDir = "Server"
        self.dQs = {}
        for address in artists:
            self.addReader(address)
        self._saveThread = th.Timer(1,self.save).start()
        self.save_data = save
        self.remember = remember
        if remember:
            self._data = pd.DataFrame()
            self._data_current_scan = pd.DataFrame()

    def addReader(self,address = None):
        if address is None:
            print ('provide IP address and PORT')
            return
        print('Adding reader')
        # try:
        reader = ArtistReader(IP=address[0],PORT=address[1])
        self._readers[reader.artistName] = reader
        self.dQs[reader.artistName] = deque()
        self._readers[reader.artistName].dQ = self.dQs[reader.artistName]
        # except Exception as e:
            # print('Connection failed')

    def save(self):
        ## This is not doing it right! Data files of all receivers
        ## should be merged before saving!
        # should be better now, but never run before!!!
        now = time.time()
        new_data = []
        for name,reader in self._readers.items():
            dQ = self.dQs[name]
            l = len(dQ)
            if not l == 0:
                data = [dQ.popleft() for i in range(l)]
                data = flatten(data)
                new_data.append(data)
        if not len(new_data) == 0:
            new_data = mass_concat(flatten(new_data),format = reader._format)
            if self.save_data:
                save(new_data,self.saveDir)
            if self.remember:
                self.extractMemory(new_data)

        # slightly more stable if the save runs every 0.5 seconds,
        # regardless of how long the previous saving took
        wait = abs(min(0, time.time() - now - SAVE_INTERVAL))
        # print(wait)
        self._saveThread = th.Timer(wait,self.save).start()

    def extractMemory(self,new_data):
        self._data = self._data.append(new_data)
        # save the current scan in memory!
        groups = self._data.groupby('scan')
        ## not sure this works - is groups a dictionary?
        # self._data_current_scan = groups[max(groups.keys)]
        # save last 10.000 data points
        self._data = self._data[-2500:]

        # self.bin_current()

        print(self._data)

    def bin_current(self):
        ## some stuff about binning the current data in some
        ## XY format with certain X steps 'n stuff
        pass

class ArtistReader(asynchat.async_chat):
    def __init__(self,IP='KSF402', PORT=5005):
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
        while time.time()-now < 5:
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
            self._format = data
        else:
            if not data == []:
                self.dQ.append(data)
            self.push('Next'.encode('UTF-8') + 'END_MESSAGE'.encode('UTF-8'))

def makeServer(channel = [('KSF402',5005)], save = True,remember = True):
    return DataServer(channel,save,remember)

def start():
    while True:
        asyncore.loop(count = 1)
        time.sleep(0.01)

def main():
    d = makeServer([('10.33.62.98',5005)],save = False,remember = True)
    asyncore.loop(0.001)

if __name__ == '__main__':
    main()