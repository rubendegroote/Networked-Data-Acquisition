import time
import copy
import h5py
import traceback
import numpy as np
from scipy import stats
import pandas as pd
import os,psutil
from scipy import stats
from scipy.stats import chi2
import zlib,pickle


def calcHist(data,bins,errormode,data_mode = 'mean'):
    bin_selection = np.digitize(data['x'], bins)

    data['bin_selection'] = bin_selection
    groups = data.groupby('bin_selection')

    binned = pd.DataFrame()
    
    binned[['x','xerr']] = groups['x'].agg([np.mean,np.std])
    
    binned['noe'] = groups['bin_selection'].sum()/binned.index.values
    
    s = groups['y'].sum()
    if data_mode == 'sum':
        binned['y'] = s
    else:
        binned['y'] = groups['y'].mean()

    if errormode == 'poisson':
        binned['yerr_b'] = s-poisson_interval_low(s)
        binned['yerr_t'] = poisson_interval_high(s)-s
        if data_mode == 'mean':
            binned['yerr_t'] = binned['yerr_t'] / binned['noe']
            binned['yerr_b'] = binned['yerr_b'] / binned['noe']
    else:
        binned['yerr_t'] = groups['y'].std()
        if data_mode == 'mean':
            binned['yerr_t'] = binned['yerr_t'] / binned['noe']**0.5
        binned['yerr_b'] = binned['yerr_t']

    binned[['xerr','yerr_t','yerr_b']] = binned[['xerr','yerr_t','yerr_b']].fillna(value=0)

    return binned

def poisson_interval_high(data, alpha=0.32):
    high = chi2.ppf(1 - alpha / 2, 2 * data + 2) / 2
    return high

def poisson_interval_low(data, alpha=0.32):
    low = chi2.ppf(alpha / 2, 2 * data) / 2
    low = np.nan_to_num(low)
    return low

def extract_scan(file_paths,columns,devices):
    frames = []
    for file_path in file_paths:
        for dev,col in zip(devices,columns):
            data_path = file_path + dev + '_ds.csv'
            with open(file_path + 'metadata_{}.txt'.format(dev), 'r') as mf:
                mass_info = mf.readline()
                scan_info = mf.readline()
                frmt = eval(mf.readline())
            col_index = frmt.index(col)

            data = np.loadtxt(data_path,delimiter = ';').T
            frames.append(pd.DataFrame({'time':data[0], col:data[col_index]}))

    dataframe = pd.concat(frames)
    dataframe = dataframe.sort_values(by='time')
    for col in columns:
        if not col == 'Counts' or col == 'counts':
            dataframe[col] = dataframe[col].fillna(method='ffill')
    dataframe = dataframe.dropna()

    return dataframe

def extract_scan_hdf(path,scan_numbers,columns,filename=None):
    scan_numbers = [str(int(s)) for s in scan_numbers]
   
    devices = [c.split(': ')[0] for c in columns]
    columns = [c.split(': ')[-1] for c in columns]

    dfs = []
    with h5py.File(path, 'r') as store:
        for dev,col in zip(devices,columns):
            try:
                for scanno in store[dev].keys():
                    if scanno.split('_')[0] in scan_numbers:
                        # start = time.time()
                        dfs.append(pd.DataFrame())
                        try:
                            dfs[-1][col] = store[dev][scanno][col].value
                            dfs[-1]['time'] = store[dev][scanno]['timestamp'].value
                        except:
                            pass
                        # print('extracted {} in {}s'.format(col,round(time.time() - start,1)))
            except:
                print('failed getting {} {}'.format(dev,col))

    dataframe = pd.concat(dfs)
    dataframe = dataframe.sort_values(by='time')
    for col in columns:
        if not col == 'Counts' or col == 'counts':
            dataframe[col] = dataframe[col].fillna(method='ffill')
    dataframe = dataframe.dropna()
    dataframe = dataframe.set_index('time')

    if filename is not None:
        dataframe.to_csv(filename)

    return dataframe

def GetFromQueue(q):
    if not q.empty():
        try:
            ret = q.get_nowait()
        except Exception as e:
            ret = None
    else:
        ret = None

    return ret

def emptyPipe(q):
    toSend = []
    now = time.time()
    while len(toSend) == 0 and time.time() - now < 1:
        while q.poll(0.0005):
            try:
                toSend.append(q.recv())
            except Exception as e:  # What to do here?
                pass
    return toSend

def group_per_scan(data,axis):
    scan_data = data[:,axis]
    changes_in_scan = scan_data[1:] - scan_data[:-1]
    index_of_changes =  np.nonzero(changes_in_scan)[0] + 1
    start = 0
    parts = {}
    for index in index_of_changes:
        parts[scan_data[start]] = data[start:index]
        start = index
    parts[scan_data[start]] = data[start:]
    return(parts)

def make_message(message):
    op,params = message
    return {'message': {'op': op, 'parameters': params}}

def track(func):
    def func_wrapper(self, message):
        try:
            track = message['track'] # if succeeds: message was already tracked
            track.append((self.name, self.counter))
            message['track'] = track
        except KeyError as e:
            message['track'] = [(self.name, self.counter)]
        self.counter += 1
        return func(self, message)
    return func_wrapper

def add_reply(message, params):
    new_message = copy.deepcopy(message)
    new_message['reply'] = {}
    new_message['reply']['op'] = new_message['message']['op'] + '_reply'
    new_message['reply']['parameters'] = params
    return new_message

def try_call(func):
    def func_wrapper(*args, **kwargs):
        try:
            reply_dict = func(*args, **kwargs)
            if reply_dict is None:
                reply_dict = {}
            reply_dict['status'] = [0]
        except:
            reply_dict = {'status': [1], 
                          'exception': traceback.format_exc()}
        return reply_dict
    return func_wrapper     

def try_deco(func):
    def func_wrapper(*args,**kwargs):
        try:
            reply = func(*args, **kwargs)
        except:
            print(traceback.format_exc())
            reply = ([1],traceback.format_exc())
        return reply
    return func_wrapper

def compress_data(func):
    def func_wrapper(*args,**kwargs):
        retval = func(*args,**kwargs)
        if 'data' in retval.keys():
            print(len(retval['data']))
            if len(retval['data']) > 0:
                compressed = True
                retval['data'] = zlib.compress(pickle.dumps(retval['data']))
            else:
                compressed = False

            retval['compressed'] = compressed
        return retval
    return func_wrapper
