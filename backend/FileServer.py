import os
import sys
import multiprocessing as mp
import numpy as np

from backend.Helpers import *
from backend.connectors import Connector, Acceptor
import backend.logbook as lb
from backend.dispatcher import Dispatcher


FILE_SERVER_PORT = 5009
HTTP_SERVER_PORT = 5010
DATA_PATH = 'C:\\Data\\Gallium Run\\'

class FileServer(Dispatcher):
    def __init__(self, PORT=5007, name='FileServer'):
        super(FileServer, self).__init__(PORT, name)
        
    @try_call
    def request_data(self,params):
        scan_number = params['scan_number'][0]
        x,y = params['x'],params['y']

        if x == [] and y == []:
            return {'data':[[],[],[],[]]}

        return_list = []
        with h5py.File('C:\\Data\\Gallium Run\\server_data.h5','r') as store:
            for name_info in [x,y]:
                origin,par_name = name_info
                data_set = store[origin][str(scan_number)]
                try:
                    format = list(data_set.attrs['format'])
                    format = [f.decode('utf-8') for f in format]
                    col = format.index(par_name)
                    return_list.append(list(data_set[:,0])) #timestamp as well
                    return_list.append(list(data_set[:,col]))
                except Exception as e:
                    print(e)
                    return_list.append([])
                    return_list.append([])
        return {'data':return_list}
    
    @try_call
    def data_format(self,params):
        scan_number = params['scan_number'][0]
        formats = {}
        with h5py.File('C:\\Data\\Gallium Run\\server_data.h5','r') as store:
            for g in store.keys():
                data_set = store[g][str(scan_number)]
                formats[g] = list(data_set.attrs['format'])
                formats[g] = [f.decode('utf-8') for f in formats[g]]
        return {'data_format':formats}


    @try_call
    def file_status(self,params):
        available_scans = []
        info = np.loadtxt('C:\\Data\\Gallium Run\\server_scans.txt',delimiter = ';')
        available_scans = list(info.T[0])
        masses = list(info.T[1])
        return {'available_scans':available_scans,
                'masses':masses}

def makeFileServer(PORT=5006):
    print('here')
    return FileServer(PORT=PORT)
