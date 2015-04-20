import asynchat
import asyncore
from collections import deque
from datetime import datetime
from copy import deepcopy
import logging
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
    from connectors import Connector,Acceptor
except:
    from backend.Helpers import *
    from backend.connectors import Connector,Acceptor



logging.basicConfig(format='%(asctime)s: %(message)s',
                    level=logging.INFO)

GET_INTERVAL = 0.05
SAVE_INTERVAL = 2
SHARED = ['scan','time']

class DataServer(asyncore.dispatcher):
    def __init__(self,artists=[],PORT=5006,save_data=False, remember=True):
        super(DataServer, self).__init__()
        self.port = PORT
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        # self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self.bind(('', self.port))
        self.listen(5)
        logging.info('Listening on port {}'.format(self.port))

        self._readers = {}
        self._readerInfo = {}
        self.bitrates = []
        self.saveDir = "Server"
        self.dQs = {}
        self.acceptors = []
        self.transmitters = []
        # self.plot = render_plot()
        for address in artists:
            self.addReader(address)
        self._getThread = th.Timer(1, self.getFromReader).start()
        self.save_data = save_data
        if save_data:
            self.lock = th.Lock()
            self.lastSaveTime = time.time()
            self.toSave={}

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
        for name,add in self._readers.items():
            if address == (add.IP,str(add.PORT)):
                if self._readerInfo[name][0]:
                    return
        try:
            reader = ArtistReader(chan=(address[0],int(address[1])),
                callback=None,onCloseCallback=readerClosed, t='DS_to_artist')
            self._readers[reader.artistName] = reader
            self.dQs[reader.artistName] = reader.dQ
            self._readerInfo[reader.artistName] = (True,reader.IP,reader.PORT)
            for c in self.acceptors:
                c.commQ.put(self._readerInfo)
            logging.info('Connected to ' + reader.artistName)
        except Exception as e:
            logging.info('Connection failed')

    def removeReader(self,address=None):
        toRemove = []
        for name,prop in self._readerInfo.items():
            if address == (prop[1],str(prop[2])):
                self._readers[name].close()
                toRemove.append(name)

        for name in toRemove:
            del self._readers[name]
            del self._readerInfo[name]

        for c in self.acceptors:
            c.commQ.put(self._readerInfo)

    def processRequests(self,sender,data):
        if data[0] == 'ARTISTS?':
            return self._readerInfo
        elif data[0] == 'Data':
            perScan,columns = data[1]
            return self.getData(perScan,columns),tuple(self._data.columns.values)
        elif data[0] == 'Add Artist':
            self.addReader(data[1])
            return None
        elif data[0] == 'Remove Artist':
            self.removeReader(data[1])
            return None
        elif data == 'info':
            try:
                return sender.commQ.get_nowait()
            except:
                pass
        
        return self.bitrates

    def readerClosed(self,reader):
        self._readerInfo[reader.artistName] = (False,reader.IP,reader.PORT)
        for c in self.acceptors:
            c.commQ.put(self._readerInfo)

    def accClosed(self,acceptor):
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
                    self.lock.release()
                    

        if not len(new_data) == 0:
            if self.remember:
                self.extractMemory(new_data)

        if self.save_data and time.time() - self.lastSaveTime > SAVE_INTERVAL:
            th.Thread(target = self.save).start()
            self.lastSaveTime = time.time()

        wait = abs(min(0, time.time() - now - GET_INTERVAL))
        if self.looping:
            self._getThread = th.Timer(wait, self.getFromReader).start()

    def save(self):
        self.lock.acquire()
        toSave = deepcopy(self.toSave)
        self.toSave = {}
        self.lock.release()
        for key,val in toSave.items():
            save(val,self.saveDir,key)

    def extractMemory(self, new_data):
        self._data = self._data.append(new_data)
        
        # save the current scan in memory
        m=self._data['scan'].max()
        self._data_current_scan = self._data[self._data['scan']==m]
                
        # save last 5000 data points
        self._data = self._data[-5000:]

    def getData(self,perScan,columns):
        try:
            if perScan:
                return self._data_current_scan[columns]
            else:
                return self._data[columns] 
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
            if sender == 'Radio':
                self.transmitters.append(Acceptor(sock, callback = self.processRequests,
                    onCloseCallback=self.accClosed,t='RGui_to_DS'))
            elif sender == 'Connector':
                self.acceptors.append(Acceptor(sock, callback = self.processRequests,
                    onCloseCallback=self.accClosed,t='MGui_to_DS'))
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
    def __init__(self,chan,callback):
        super(ArtistReader, self).__init__(chan,callback,t='DS_to_artist')

        self.artistName = self.wait_for_connection()
        self.dQ = deque()
        self._data = pd.DataFrame()
        self.total = 0

        self.send_next()

    def found_terminator(self):
        buff = self._buffer
        self.total += len(self._buffer)

        self._buffer = b''
        data = pickle.loads(buff)
        if type(data) == tuple:
            self._format = tuple([self.artistName + ': ' + d if d not in SHARED else d for d in data])
        else:
            if not data == []:
                self.dQ.append(data)
            self.send_next()

def makeServer(channel=[('KSF402', 5005)],PORT=5004,save=True,remember=True):
    return DataServer(channel,PORT,save,remember)

def main():
    channels = input('Artist IP,PORTS?').split(";")
    channels = [c.split(",") for c in channels]
    PORT = input('PORT?')
    save = int(input('save?'))==1
    rem = int(input('remember?'))==1
    d = makeServer(channels,int(PORT),save=save, remember=rem)

if __name__ == '__main__':
    main()
