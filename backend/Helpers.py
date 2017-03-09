import time
import copy
import h5py
import traceback
import numpy as np
from scipy import stats
import pandas as pd
import os,psutil
from scipy import stats

def calcHist(data,bins,errormode,data_mode = 'mean'):
    noe,mean_x,err_x,mean_y,err = np.zeros(len(bins)),\
                                  np.zeros(len(bins)),\
                                  np.zeros(len(bins)),\
                                  np.zeros(len(bins)),\
                                  np.zeros(len(bins))

    bin_selection = np.digitize(data['x'], bins)

    data['bin_selection'] = bin_selection
    groups = data.groupby('bin_selection')

    binned = pd.DataFrame()
    
    binned['x'] = groups['x'].mean()
    binned['xerr'] = groups['x'].std()
    
    binned['noe'] = groups['bin_selection'].sum()/binned.index.values
    
    if data_mode == 'sum':
        binned['y'] = groups['y'].sum()
    else:
        binned['y'] = groups['y'].mean()

    if errormode == 'sqrt':
        binned['yerr'] = np.sqrt(groups['y'].sum()+1)
        if data_mode == 'mean':
            binned['yerr'] = binned['yerr'] / binned['noe']
    else:
        binned['yerr'] = groups['y'].std()
        if data_mode == 'mean':
            binned['yerr'] = binned['yerr'] / binned['noe']**0.5

    binned[['xerr','yerr']] = binned[['xerr','yerr']].fillna(value=0)

    return binned

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

