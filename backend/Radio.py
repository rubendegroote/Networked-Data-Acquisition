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


class Radio(asynchat.async_chat):
    def __init__(self,IP,PORT):
        super(Radio, self).__init__()
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        # self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self.connect((IP, PORT))
        
        self._buffer = b''
        self.format = tuple()
        self.set_terminator('STOP_DATA'.encode('UTF-8'))
        self.xy = ['time','Rubeny']
        self.push(pickle.dumps(self.xy))
        self.push('END_MESSAGE'.encode('UTF-8'))

        self.data = pd.DataFrame()

        self.looping = True
        t = th.Thread(target = self.start).start()

    def collect_incoming_data(self, data):
        self._buffer += data

    def found_terminator(self):
        buff = self._buffer
        self._buffer = b''
        data = pickle.loads(buff)
        if type(data) == tuple:
            self.format = data
        else:
            if not len(data) == 0:
                self.data = data
            self.push(pickle.dumps(self.xy))
            self.push('END_MESSAGE'.encode('UTF-8'))

    def stop(self):
        self.looping = False

    def start(self):
        while self.looping:
            asyncore.loop(count=1)
            time.sleep(0.01)