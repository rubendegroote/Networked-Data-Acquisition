import asynchat
import asyncore
import sys
from collections import deque
from datetime import datetime
from copy import deepcopy
import logging
logging.basicConfig(filename='DataServer.log',
                    format='%(asctime)s: %(message)s',
                    level=logging.INFO)
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

        self.memory = 5000
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
        reader = Connector(chan=(address[0], int(address[1])),
                              callback=self.processData,
                              onCloseCallback=self.readerClosed,
                              t='DS_to_A',
                              defaultRequest='data')
        self._readers[reader.artistName] = reader
        self.dQs[reader.artistName] = reader.dQ
        self._readerInfo[reader.artistName] = (
            True, reader.chan[0], reader.chan[1])
        for c in self.acceptors:
            c.commQ.put(self._readerInfo)
        logging.info('Connected to ' + reader.artistName)

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

    def processData(self, sender, data):
        pass

    def processRequests(self, sender, message):
        if message['message']['op'] == 'data':
            perScan, latest, columns = data[1]
            dat = self.getData(perScan, latest, columns)
            try:
                print('Latest:      ', latest.index.values[0])
                print('Stream begin:', self._data_current_stream.index.values[0])
                print('Stream end:  ', self._data_current_stream.index.values[-1])
                print('Sent begin:', dat.index.values[0])
                print('Sent end:  ', dat.index.values[-1])
            except:
                pass
            form = tuple(self._data_current_stream.columns.values)
            # print(len(dat))
            # print(dat.head(1))
            return {'data': dat, 'format': form}
        elif message['message']['op'] == 'add_artist':
            try:
                self.addReader(message['message']['parameters']['address'])
                params = {'status': 0}
            except Exception as e:
                logging.info('Connection failed')
                params = {'status': 1, 'exception': e}
            message = add_reply(message, params)
            return message
        elif message['message']['op'] == 'Remove Artist':
            self.removeReader(data[1])
            return None
        elif message['message']['op'] == 'Remove All Artists':
            toRemove = []
            for name, prop in self._readerInfo.items():
                self._readers[name].close()
                toRemove.append(name)

            for name in toRemove:
                del self._readers[name]
                del self._readerInfo[name]

            for c in self.acceptors:
                c.commQ.pu(self._readerInfo)
            return None
        elif message['message']['op'] == 'Clear Memory':
            logging.info('Memory cleared')
            self._clear_memory = True
            return None
        elif message['message']['op'] == 'Set Memory Size':
            try:
                mem = np.abs(int(data[1]))
                logging.info(
                    'Memory size changed from {} to {}'.format(self.memory, mem))
                self.memory = mem
            except:
                logging.warn(
                    'Tried setting memory to invalid value {}'.format(data[1]))
            return None
        elif message['message']['op'] == 'info':
            params = {'reader_info': self._readerInfo,
                      'bit_rates': self.bitrates}

            message = add_reply(message, params)
            return message

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
        # try:
        #     a = sum([len(toSave[key]) for key in toSave.keys()])
        #     print('saving:', a)
        # except:
        #     print('saving:', len(toSave))
        for key, val in toSave.items():
            save(val, self.saveDir, key)

    def extractMemory(self, new_data):
        # print('extract:', len(new_data))
        new_data = new_data.sort_index()
        m = new_data['scan'].max()
        self.stream_lock.acquire()
        try:
            self._data_current_stream = self._data_current_stream.append(
                new_data)
        finally:
            pass
            self.stream_lock.release()
        # if m > -1:
        #     if self._data_current_scan.empty:
        #         # self.current_scan_lock.acquire()
        #         try:
        #             self._data_current_scan = new_data[new_data['scan'] == m]
        #         finally:
        #             pass
        #             # self.current_scan_lock.release()
        #     else:
        #         if m > self._data_current_scan['scan'][-1]:
        #             # self.previous_scan_lock.acquire()
        #             # self.current_scan_lock.acquire()
        #             try:
        #                 self._data_previous_scan, self._data_current_scan = self._data_current_scan, new_data[
        #                     new_data['scan'] == m]
        #             finally:
        #                 pass
        #                 # self.previous_scan_lock.release()
        #                 # self.current_scan_lock.release()
        #         else:
        #             # self.current_scan_lock.acquire()
        #             try:
        #                 self._data_current_scan = self._data_current_scan.append(
        #                     new_data[new_data['scan'] == m])
        #             finally:
        #                 pass
        #                 # self.current_scan_lock.release()

        # save the current scan in memory
        # m = self._data['scan'].max()
        # self._data_current_scan = self._data[self._data['scan'] == m]

        # save last 5000 data points
        self.stream_lock.acquire()
        try:
            if not self._clear_memory:
                self._data_current_stream = self._data_current_stream[
                    -self.memory:]
            else:
                self._clear_memory = False
                self._data_current_stream = self._data_current_stream[-1:]
        finally:
            pass
            self.stream_lock.release()

    def getData(self, perScan, latest, columns):
        try:
            if perScan[0]:
                if perScan[1]:
                    # self.current_scan_lock.acquire()
                    try:
                        if latest is None:
                            returnData = self._data_current_scan
                        else:
                            d = self._data_current_stream.index.values
                            indices = d > latest
                            returnData = self._data_current_scan[indices]
                    except:
                        raise
                    finally:
                        pass
                        # self.current_scan_lock.release()
                else:
                    # self.previous_scan_lock.acquire()
                    try:
                        if latest is None:
                            returnData = self._data_previous_scan
                        else:
                            d = self._data_current_stream.index.values
                            indices = d > latest
                            returnData = self._data_previous_scan[indices]
                    except:
                        raise
                    finally:
                        pass
                        # self.previous_scan_lock.release()
            else:
                self.stream_lock.acquire()
                try:
                    dummy = self._data_current_stream.copy()
                    if latest is None:
                        returnData = dummy
                    else:
                        dummy = dummy.fillna(method='ffill')
                        mask = dummy.isin(latest).all(1)
                        indices = np.cumsum(mask.values, dtype=bool)
                        returnData = self._data_current_stream[indices]
                except:
                    pass
                finally:
                    self.stream_lock.release()
            return returnData
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
                logging.error('Sender {} named {} on socket {} not understood'
                              .format(addr, sender, sock))
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


def makeServer(PORT=5006, save=True, remember=True):
    return DataServer([], PORT, save, remember)


def main():
    try:
        d = makeServer(5005, save=1, remember=1)
        style = "QLabel { background-color: green }"
        e = ''
    except Exception as error:
        e = str(error)
        style = "QLabel { background-color: red }"

    from PyQt4 import QtCore, QtGui
    # Small visual indicator that this is running
    app = QtGui.QApplication(sys.argv)
    w = QtGui.QWidget()

    w.setWindowTitle('Data Server')
    layout = QtGui.QGridLayout(w)
    label = QtGui.QLabel(e)
    label.setStyleSheet(style)
    layout.addWidget(label)
    w.show()

    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
