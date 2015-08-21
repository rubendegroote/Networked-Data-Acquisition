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
from dispatcher import Dispatcher

GET_INTERVAL = 0.05
SAVE_INTERVAL = 2
SHARED = ['scan', 'time']


class DataServer(Dispatcher):

    def __init__(self, PORT=5006, save_data=False, remember=True, name='DataServer'):
        super(DataServer, self).__init__(PORT, name, defaultRequest='data')
        self.memory = 5000
        self.savedScan = -np.inf
        self.bitrates = []
        self.saveDir = "Server"
        self.dQs = {}
        # self._getThread = th.Timer(1, self.getFromReader).start()
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

    @try_call
    def data(self, **kwargs):
        perScan,latest,columns = kwargs['per_scan'][0], kwargs['latest'][0], kwargs['columns'][0]
        dat = self.getData(perScan, latest, columns)
        form = tuple(self._data_current_stream.columns.values)
        return {'data': dat, 'format': form}

    @try_call
    def clear_memory(self, *args):
        self._clear_memory = True
        return {'status': [0]}

    @try_call
    def set_memory_size(self, **kwargs):
        mem = np.abs(int(kwargs['memory_size'][0]))
        self.memory = mem
        return {'status': 0}

    @try_call
    def status(self, *args):
        return {'connector_info': self.connInfo, 'bit_rates': self.bitrates}

    def connector_cb(self, message):
        with open(self.name + '_transmissionID.txt', 'a') as f:
            f.write(str(message['track']))

    def getFromReader(self):
        now = time.time()
        new_data = pd.DataFrame()
        for name, reader in self.connectors.items():
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


def makeServer(PORT=5006, save=True, remember=True):
    return DataServer(PORT, save, remember)


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
