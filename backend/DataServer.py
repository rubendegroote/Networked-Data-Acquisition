import asynchat
import asyncore
from collections import deque
from datetime import datetime
from copy import deepcopy
import logging
import os
import pickle
import socket
import threading as th
import multiprocessing as mp
import time
import numpy as np
import pandas as pd
from bokeh.embed import autoload_server
try:
    from Helpers import *
    from connectors import Connector, Acceptor
except:
    from backend.Helpers import *
    from backend.connectors import Connector, Acceptor
logging.basicConfig(filename='DataServer.log',
                    format='%(asctime)s: %(message)s',
                    level=logging.INFO)

GET_INTERVAL = 0.05
SAVE_INTERVAL = 2
SHARED = ['scan', 'time']


class DataServer(asyncore.dispatcher):

    def __init__(self, artists=[], PORT=5006, save_data=False, remember=True):
        super(DataServer, self).__init__()
        self.port = PORT
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.bind(('', self.port))
        self.listen(5)
        logging.info('Listening on port {}'.format(self.port))

        self.memory = 50000
        self.savedScan = -np.inf
        self._readers = {}
        self._readerInfo = {}
        self.bitrates = []
        self.saveDir = "Server"
        self.dQs = {}
        self.acceptors = []
        self.transmitters = []
        for address in artists:
            self.addReader(address)
        self._getThread = th.Timer(1, self.getFromReader).start()
        self.save_data = save_data
        if save_data:
            self.lock = th.Lock()
            self.lastSaveTime = time.time()
            self.toSave = {}

        self.remember = remember
        self.previous_scan_lock = th.Lock()
        self.current_scan_lock = th.Lock()
        self.stream_lock = th.Lock()
        if remember:
            self._data_previous_scan = pd.DataFrame()
            self._data_current_scan = pd.DataFrame()
            self._data_current_stream = pd.DataFrame()
        self._clear_memory = False

        self.looping = True
        t = th.Thread(target=self.start).start()

    def start(self):
        while self.looping:
            asyncore.loop(count=1)
            time.sleep(0.1)

    def stop(self):
        self.looping = False

    def addReader(self, address=None):
        if address is None:
            logging.warning('provide IP address and PORT')
            return
        for name, add in self._readers.items():
            if address == (add.chan[0], str(add.chan[1])):
                if self._readerInfo[name][0]:
                    return
        try:
            reader = ArtistReader(chan=(address[0], int(address[1])),
                                  callback=None,
                                  onCloseCallback=self.readerClosed)
            self._readers[reader.artistName] = reader
            self.dQs[reader.artistName] = reader.dQ
            self._readerInfo[reader.artistName] = (
                True, reader.chan[0], reader.chan[1])
            for c in self.acceptors:
                c.commQ.put(self._readerInfo)
            logging.info('Connected to ' + reader.artistName)
        except Exception as e:
            logging.info('Connection failed')

    def removeReader(self, address=None):
        toRemove = []
        for name, prop in self._readerInfo.items():
            if address == (prop[1], str(prop[2])):
                self._readers[name].close()
                toRemove.append(name)

        for name in toRemove:
            del self._readers[name]
            del self._readerInfo[name]

        for c in self.acceptors:
            c.commQ.put(self._readerInfo)

    def processRequests(self, sender, data):
        if data[0] == 'data':
            perScan, latest, columns = data[1]
            return {'data': self.getData(perScan, latest, columns), 'format': tuple(self._data_current_stream.columns.values)}
        elif data[0] == 'Add Artist':
            self.addReader(data[1])
            return None
        elif data[0] == 'Remove Artist':
            self.removeReader(data[1])
            return None
        elif data[0] == 'Clear Memory':
            logging.info('Memory cleared')
            self._clear_memory = True
            return None
        elif data[0] == 'Set Memory Size':
            try:
                mem = np.abs(int(data[1]))
                logging.info('Memory size changed from {} to {}'.format(self.memory, mem))
                self.memory = mem
            except:
                logging.warn('Tried setting memory to invalid value {}'.format(data[1]))
            return None
        elif data == 'info':
            try:
                return sender.commQ.get_nowait()
            except:
                return (self._readerInfo, self.bitrates)

    def readerClosed(self, reader):
        self._readerInfo[reader.artistName] = (
            False, reader.chan[0], reader.chan[1])
        for c in self.acceptors:
            c.commQ.put(self._readerInfo)

    def accClosed(self, acceptor):
        self.acceptors.remove(acceptor)

    def getFromReader(self):
        now = time.time()
        new_data = pd.DataFrame()
        for name, reader in self._readers.items():
            dQ = self.dQs[name]
            l = len(dQ)
            if not l == 0:
                data = flatten([dQ.popleft() for i in range(l)])
                data = convert(flatten(data), format=reader._format)
                new_data = new_data.append(data)
                if self.save_data:
                    self.lock.acquire()
                    try:
                        self.toSave[name] = self.toSave[name].append(data)
                    except KeyError:
                        self.toSave[name] = data
                    finally:
                        self.lock.release()

        if not len(new_data) == 0:
            if self.remember:
                self.extractMemory(new_data)

        if self.save_data and time.time() - self.lastSaveTime > SAVE_INTERVAL:
            th.Thread(target=self.save).start()
            self.lastSaveTime = time.time()

        wait = abs(min(0, time.time() - now - GET_INTERVAL))
        if self.looping:
            self._getThread = th.Timer(wait, self.getFromReader).start()

    def save(self):
        self.lock.acquire()
        toSave = deepcopy(self.toSave)
        self.toSave = {}
        self.lock.release()
        for key, val in toSave.items():
            save(val, self.saveDir, key)

    def extractMemory(self, new_data):
        m = new_data['scan'].max()
        self.stream_lock.acquire()
        try:
            self._data_current_stream = self._data_current_stream.append(new_data)
        finally:
            self.stream_lock.release()
        if m > -1:
            if self._data_current_scan.empty:
                self.current_scan_lock.acquire()
                try:
                    self._data_current_scan = new_data[new_data['scan'] == m]
                finally:
                    self.current_scan_lock.release()
            else:
                if m > self._data_current_scan['scan'][-1]:
                    self.previous_scan_lock.acquire()
                    self.current_scan_lock.acquire()
                    try:
                        self._data_previous_scan, self._data_current_scan = self._data_current_scan, new_data[new_data['scan'] == m]
                    finally:
                        self.previous_scan_lock.release()
                        self.current_scan_lock.release()
                else:
                    self.current_scan_lock.acquire()
                    try:
                        self._data_current_scan = self._data_current_scan.append(new_data[new_data['scan'] == m])
                    finally:
                        self.current_scan_lock.release()

        # save the current scan in memory
        # m = self._data['scan'].max()
        # self._data_current_scan = self._data[self._data['scan'] == m]

        # save last 5000 data points
        self.stream_lock.acquire()
        try:
            if not self._clear_memory:
                self._data_current_stream = self._data_current_stream[-self.memory:]
            else:
                self._clear_memory = False
                self._data_current_stream = self._data_current_stream[-10:]
        finally:
            self.stream_lock.release()

    def getData(self, perScan, latest, columns):
        try:
            if perScan[0]:
                if perScan[1]:
                    if latest is None:
                        return self._data_current_scan[columns]
                    else:
                        return self._data_current_scan.loc[latest:, columns][1:]
                else:
                    if latest is None:
                        return self._data_previous_scan[columns]
                    else:
                        return self._data_previous_scan.loc[latest:, columns][1:]
            else:
                if latest is None:
                    return self._data_current_stream[columns]
                else:
                    return self._data_current_stream.loc[latest:, columns][1:]
        except:
            return pd.DataFrame()

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
            if sender == 'R_to_DS':
                self.acceptors.append(Acceptor(sock,
                                               callback=self.processRequests,
                                               onCloseCallback=self.accClosed,
                                               t='R_to_DS'))
            elif sender == 'MGui_to_DS':
                self.acceptors.append(Acceptor(sock,
                                               callback=self.processRequests,
                                               onCloseCallback=self.accClosed,
                                               t='MGui_to_DS'))
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
        logging.info('Closing DataServer')
        super(DataServer, self).handle_close()


class ArtistReader(Connector):

    def __init__(self, chan, callback, onCloseCallback):
        super(ArtistReader, self).__init__(
            chan, callback, onCloseCallback, t='DS_to_A')
        self.dQ = deque()

        self.artistName = self.acceptorName

        self.send_next()

    def found_terminator(self):
        data = pickle.loads(self.buff)
        self.buff = b''
        if type(data) == dict:
            self._format = tuple([self.artistName + ': ' + f
                                  if f not in SHARED else f for f in data['format']])
            d = data['data']
            if not data == []:
                self.dQ.append(d)

        self.send_next()

    def send_next(self):
        self.push(pickle.dumps('data'))
        self.push('END_MESSAGE'.encode('UTF-8'))


def makeServer(PORT=5006, save=True, remember=True):
    return DataServer([], PORT, save, remember)

def main():
    PORT = input('PORT?')
    save = int(input('save?')) == 1
    rem = int(input('remember?')) == 1
    d = makeServer(int(PORT), save=save, remember=rem)

if __name__ == '__main__':
    main()
