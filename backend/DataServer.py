import asynchat
import asyncore
import sys
from collections import deque
from datetime import datetime
from copy import deepcopy
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

try:
    from save import *
except:
    from backend.save import *


GET_INTERVAL = 0.05
SAVE_INTERVAL = 2
SHARED = ['scan', 'time']


class DataServer(Dispatcher):

    def __init__(self, PORT=5006, save_data=False, remember=True, name='DataServer'):
        super(DataServer, self).__init__(PORT, name, defaultRequest='data')
        self.memory = 5000
        self.savedScan = -np.inf
        self.bitrates = []
        self.saveDir = "C:\\Data\\"

        self.data_lists = {}

        self.save_data = save_data
        if save_data:
            self.save_output,self.save_input = mp.Pipe(duplex=False)
            self.lastSaveTime = time.time()
            self.toSave = {}

        self.remember = remember

        self._clear_memory = False
        self.start_saving()

    def start_saving(self):
        self.saveProcess = mp.Process(target = save_continuously_dataserver,
                                      args = (self.save_output,
                                              self.saveDir))
        self.saveProcess.start()


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
        return {'connector_info': self.connInfo, 
                'bit_rates': self.bitrates}

    def data_reply(self,origin,params):
        data,format = params['data'],params['format']
        if data == []:
            return

        try:
            self.data_lists[origin].extend(data)
        except KeyError as e:
            self.data_lists[origin] = data
        
        self.save_input.send((origin,format,data))

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
