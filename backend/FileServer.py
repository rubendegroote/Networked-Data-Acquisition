import os
import sys
import multiprocessing as mp
import numpy as np
import pandas as pd
import configparser

from backend.helpers import *
from backend.connectors import Connector, Acceptor
import backend.logbook as lb
from backend.dispatcher import Dispatcher
import threading as th

CONFIG_PATH = os.getcwd() + "\\Config files\\config.ini"
CHUNK_SIZE = 5*10**4
class FileServer(Dispatcher):
    config_parser = configparser.ConfigParser()
    config_parser.read(CONFIG_PATH)
    save_path = config_parser['paths']['data_path']
    PORT = int(config_parser['ports']['file_server'])
    def __init__(self,PORT=PORT, name='FileServer'):
        super(FileServer, self).__init__(PORT, name)
        self.row = 0

    @try_call
    def request_data(self,params):
        scan_numbers = params['scan_numbers']
        x,y = params['x'],params['y']

        if self.row == 0:
            self.data = extract_scan(self.save_path+'server_data.h5',scan_numbers,[x,y],filename=None)

        stop = self.row+CHUNK_SIZE
        data = [self.data['time'][self.row:stop],self.data[x.split(': ')[-1]][self.row:stop],self.data[y.split(': ')[-1]][self.row:stop]]
        chunk = [list(d.values) for d in data]
        print(stop)
        if stop >= len(self.data):
            self.row = 0
            return {'data': chunk,'done':True}
        else:
            self.row = stop
            return {'data': chunk,'done':False}

    @try_call
    def get_status(self,params):
        available_scans = []
        info = np.atleast_2d(np.loadtxt(self.save_path+'server_scans.txt',delimiter = ';'))
        available_scans = list(info.T[0])
        masses = list(info.T[1])
        available_scans,masses = zip(*set(zip(available_scans,masses)))
        
        return {'available_scans':available_scans,
                'masses':masses}

    @try_call
    def scan_format(self,params):
        self.row = 0
        scans = params['scans']

        format = []
        with h5py.File(self.save_path+'server_data.h5') as store:
            for dev in store.keys():
                for scan in scans:
                    scanno = str(int(scan))+'_0'
                    if scanno in list(store[dev].keys()):
                        forms = list(store[dev][scanno].keys())
                        forms = [dev + ': ' + f for f in forms]
                        format.extend(forms)

        format = list(set(format))

        return {'format': format}

def makeFileServer():
    return FileServer()
