import os
import sys
import multiprocessing as mp
import numpy as np
import pandas as pd
import configparser

from backend.Helpers import *
from backend.connectors import Connector, Acceptor
import backend.logbook as lb
from backend.dispatcher import Dispatcher
import threading as th

CONFIG_PATH = os.getcwd() + "\\config.ini"
CHUNK_SIZE = 10**4
class FileServer(Dispatcher):
    config_parser = configparser.ConfigParser()
    config_parser.read(CONFIG_PATH)
    save_path = config_parser['paths']['data_path']
    PORT = int(config_parser['ports']['file_server'])
    def __init__(self,PORT=PORT, name='FileServer'):
        super(FileServer, self).__init__(PORT, name)
        self.started_calulations = False
        self.progress = 0
        self.done = False

    @try_call
    def request_processed_data(self,params):
        scan_numbers = params['scan_numbers']
        bin_size = params['bin_size']
        error_mode = params['error_mode']
        x,y = params['x'],params['y']

        if x == [] and y == []:
            return {'data':[[],[],[],[]],'chunk':0}

        if not self.started_calulations:
            path = self.save_path+'server_data.h5'
            self.calculation_thread = th.Thread(target = self.calcHist_chunked,
                    args = (path,scan_numbers,x,y,bin_size,error_mode))
            self.calculation_thread.start()
            self.started_calulations = True

        if not self.done:
            return {'done':[False],'progress':[self.progress]}
        else:
            self.started_calulations = False
            self.done = False
            self.progress = 0
            bin_centers,center_err,bin_means,err = self.ret

            return {'done':[True],
                'centers':list(bin_centers), 
                'center_err':list(center_err),
                'bin_means':list(bin_means),
                'err':list(err)}

    @try_call
    def get_status(self,params):
        formats = {}
        with h5py.File(self.save_path+'server_data.h5','r') as store:
            for g in store.keys():
                formats[g] = list(store[g]["-1"].attrs['format'])
                formats[g] = [f.decode('utf-8') for f in formats[g]]
        
        available_scans = []
        info = np.loadtxt(self.save_path+'server_scans.txt',delimiter = ';')
        available_scans = list(info.T[0])
        masses = list(info.T[1])
        available_scans,masses = zip(*set(zip(available_scans,masses)))
        
        return {'data_format':formats,'available_scans':available_scans,
                'masses':masses}


    def calcHist_chunked(self,file_name,scans,x_name,y_name,binsize,errormode):
        all_data = pd.DataFrame()
        # x_name = ('wavemeter','wavenumber_1')
        # y_name = ('CRIS','counts')

        with h5py.File(file_name,'r') as store:
            x_origin,x_par_name = x_name
            y_origin,y_par_name = y_name
            #define bins
            minimum = 10**20
            maximum = -10**20
            total_chunks = 0
            for scan_number in scans:
                x_data_set = store[x_origin][str(scan_number)]
                y_data_set = store[y_origin][str(scan_number)]

                format = list(x_data_set.attrs['format'])
                format = [f.decode('utf-8') for f in format]
                x_col = format.index(x_par_name)
                
                stops = np.linspace(0,len(x_data_set),
                   int(len(x_data_set)/(CHUNK_SIZE))+2,dtype=int)
                start = 0
                for stop in stops[1:]:
                    x = x_data_set[start:stop,x_col]
                    if 'wavenumber' in x_par_name:
                        x = x[np.logical_and(x>13370, x<13390)]
                    if len(x) > 0:
                        minimum = min(minimum,np.min(x))
                        maximum = max(maximum,np.max(x))

                    start = stop

                total_chunks += int(max(len(y_data_set),len(x_data_set)) / CHUNK_SIZE) + 1

            chunks = 0

            bins = np.arange(minimum,maximum+binsize,binsize)
            mean_xs = np.zeros(len(bins))
            noes = np.zeros(len(bins))
            err_xs = np.zeros(len(bins))
            mean_ys = np.zeros(len(bins))
            err_ys = np.zeros(len(bins))
            for scan_number in scans:
                x_data_set = store[x_origin][str(scan_number)]
                y_data_set = store[y_origin][str(scan_number)]

                format = list(x_data_set.attrs['format'])
                format = [f.decode('utf-8') for f in format]
                x_col = format.index(x_par_name)
                format = list(y_data_set.attrs['format'])
                format = [f.decode('utf-8') for f in format]
                y_col = format.index(y_par_name)

                prev_x_index = 0
                prev_y_index = 0

                x_index = CHUNK_SIZE
                y_index = CHUNK_SIZE

                chunks_for_this_scan = int(max(len(y_data_set),len(x_data_set)) / CHUNK_SIZE) + 1
                chunks_this_scan = 0
                while chunks_this_scan < chunks_for_this_scan:
                    chunks += 1
                    chunks_this_scan += 1
                    self.progress = int(chunks/total_chunks * 100)
                    x_time = x_data_set[prev_x_index:x_index,0]
                    y_time = y_data_set[prev_y_index:y_index,0]
                    if x_time[-1] < y_time[-1]:
                        x_chunk = x_data_set[prev_x_index:x_index,x_col]
                        
                        y_chunk = y_data_set[prev_y_index:y_index,y_col]
                        slicer = y_time<x_time[-1]
                        y_time,y_chunk = y_time[slicer],y_chunk[slicer]

                        prev_x_index = x_index
                        prev_y_index = prev_y_index + len(y_chunk)

                    else:
                        x_chunk = x_data_set[prev_x_index:x_index,x_col]
                        slicer = x_time<y_time[-1]
                        x_time,x_chunk = x_time[slicer], x_chunk[slicer]
                        
                        y_chunk = y_data_set[prev_y_index:y_index,y_col]

                        prev_x_index = prev_x_index + len(x_chunk)
                        prev_y_index = y_index

                    x_index = prev_x_index + CHUNK_SIZE
                    y_index = prev_y_index + CHUNK_SIZE

                    # so now we have two chunks of unequal length, but to equal 
                    # moment in time!
                    x_frame = pd.DataFrame({'time':x_time,'x':x_chunk})
                    y_frame = pd.DataFrame({'time':y_time,'y':y_chunk})

                    data_frame = pd.concat([x_frame,y_frame])
                    data_frame.set_index(['time'],inplace=True)
                    data_frame.sort_index(inplace=True)
                    data_frame['x'].fillna(method='ffill', inplace=True)
                    data_frame.dropna(inplace=True)

                    if 'wavenumber' in x_par_name:
                        data_frame = data_frame[np.logical_and(data_frame['x']>13370, data_frame['x']<13390)]

                    if 'wavenumber' in y_par_name:
                        data_frame = data_frame[np.logical_and(data_frame['y']>13370, data_frame['y']<13390)]


                    if len(data_frame['x'])>0:
                        noe,mean_x,err_x,mean_y,err_y = calcHist(data_frame,bins,errormode)

                        s = noes+noe>0

                        mean_xs[s] = (mean_xs * noes + noe*mean_x)[s]/(noes + noe)[s]
                        err_xs[s] = np.sqrt( (err_xs**2 * noes + err_x**2 * noe)[s] / (noes + noe)[s])

                        mean_ys[s] = (mean_ys * noes + noe*mean_y)[s]/(noes + noe)[s]
                        if errormode == 'std dev':
                            err_ys[s] = np.sqrt( (err_ys**2 * noes + err_y**2 * noe)[s] / (noes + noe)[s])
                        elif errormode == 'sqrt':
                            err_ys[s] = np.sqrt(err_ys**2*noes**2 + err_y**2*noe**2)[s] / (noes + noe)[s]
                        noes[s] += noe[s]

        s = noes>0

        self.ret = mean_xs[s],err_xs[s],mean_ys[s],err_ys[s]
        self.done = True
        


    # def calcHist_chunked(self,file_name,scans,binsize,error_mode):
    #     time_bin = 1
    #     all_data = pd.DataFrame()
    #     x_name = ('wavemeter','wavenumber_1')
    #     y_name = ('CRIS','counts')
    #     with h5py.File(file_name,'r') as store:
    #         # estimation required for progress report
    #         total_len = 0
    #         for i,scan_number in enumerate(scans):
    #             origin,par_name = x_name
    #             total_len+=len(store[origin][str(scan_number)])
    #             origin,par_name = y_name
    #             total_len+=len(store[origin][str(scan_number)])
    #         total_chunks = total_len/CHUNK_SIZE

    #         chunks = 0
    #         for i,scan_number in enumerate(scans):
    #             origin,par_name = x_name
    #             data_set = store[origin][str(scan_number)]

    #             means = np.array([])
    #             errors = np.array([])
    #             nos = np.array([])

    #             format = list(data_set.attrs['format'])
    #             format = [f.decode('utf-8') for f in format]
    #             col = format.index(par_name)
    #             stops = np.linspace(0,len(data_set),
    #                            int(len(data_set)/(CHUNK_SIZE))+2,dtype=int)
    #             start=0
    #             offset = data_set[0,0]
    #             for stop in stops[1:]:
    #                 chunks += 1
    #                 self.progress = int(chunks/total_chunks*100)

    #                 time = data_set[start:stop,0]
    #                 time = time - offset
    #                 data = data_set[start:stop,col]

    #                 if len(data)>0:
    #                     mean,error,no = time_bin_count_data(time,data,time_bin,summing=False)
    #                     means = np.append(means,mean)
    #                     errors = np.append(errors,error)
    #                     nos = np.append(nos,no)

    #                 start=stop

    #             ### y data
    #             origin,par_name = y_name
    #             data_set = store[origin][str(scan_number)]

    #             sums = np.array([])
    #             nos = np.array([])

    #             format = list(data_set.attrs['format'])
    #             format = [f.decode('utf-8') for f in format]
    #             col = format.index(par_name)
    #             stops = np.linspace(0,len(data_set),
    #                            int(len(data_set)/(CHUNK_SIZE))+2,dtype=int)
    #             start=0
    #             offset = data_set[0,0]
    #             for stop in stops[1:]:
    #                 chunks += 1
    #                 self.progress = int(chunks/total_chunks*100)

    #                 time = data_set[start:stop,0]
    #                 time = time - offset
    #                 data = data_set[start:stop,col]
    
    #                 if len(data)>0:
    #                     s, no =  time_bin_count_data(time,data,time_bin, summing = True)
    #                     sums = np.append(sums,s)
    #                     nos = np.append(nos,no)

    #                 start=stop

    #             data_x = pd.DataFrame({'time':centers_x,'x':means_x})
    #             data_y = pd.DataFrame({'time':centers_y,'y':means_y})
            
    #             data_frame = pd.concat([data_x,data_y])
    #             data_frame.set_index(['time'],inplace=True)
    #             data_frame.sort_index(inplace=True)
    #             data_frame['x'].fillna(method='ffill', inplace=True)
    #             data_frame.dropna(inplace=True)

    #             all_data = pd.concat((all_data,data_frame))

    #             slicing = np.bitwise_and(all_data['x'] > 13370, all_data['x'] < 13390)
    #             all_data = all_data[slicing]

    #     if not len(all_data) == 0:
    #         self.ret = calcHist(all_data.index.values,all_data['x'],all_data['y'],binsize,error_mode)
    #     else:
    #         self.ret = [],[],[],[]
    #     self.done = True

def makeFileServer():
    return FileServer()
