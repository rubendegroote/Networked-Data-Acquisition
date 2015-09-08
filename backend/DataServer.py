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

class DataServer(Dispatcher):
    def __init__(self, PORT=5006, save_data=False, remember=True, name='DataServer'):
        super(DataServer, self).__init__(PORT, name, defaultRequest=('data',{}))
        self.save_data = save_data
        if save_data:
            self.savedScan = -np.inf
            self.saveDir = "C:\\Data\\"
            self.save_output,self.save_input = mp.Pipe(duplex=False)


        self.start_saving()

    def default_cb(self):
        return 'data', {}

    def start_saving(self):
        self.saveProcess = mp.Process(target = save_continuously_dataserver,
                                      args = (self.save_output,
                                              self.saveDir))
        self.saveProcess.start()

    @try_call
    def data(self, params):
        # find a clever way to compress all the data so far and 
        # to send it
        return {'data': data_list}

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
        return {'connector_info': self.connInfo}

    def data_reply(self,track,params):
        data,format = params['data'],params['format']
        origin, track_id = track[-1]
        if data == []:
            return

        ### find a clever way to save/extend/whatever the data

        self.save_input.send((origin,format,data))

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
