import time
import copy
import logging
import h5py
import traceback
import numpy as np
from scipy import stats
import pandas as pd


def calcHist(data,bins,errormode,data_mode = 'mean'):
    noe,mean_x,err_x,mean_y,err = np.zeros(len(bins)),\
                                  np.zeros(len(bins)),\
                                  np.zeros(len(bins)),\
                                  np.zeros(len(bins)),\
                                  np.zeros(len(bins))
    bin_selection = np.digitize(data['x'], bins)
    for n in np.unique(bin_selection):
        x_data = data['x'][bin_selection == n]
        noe[n] = len(x_data)
        mean_x[n] = np.mean(x_data)
        err_x[n] = np.sqrt(np.mean((x_data - mean_x[n])**2))

        y_data = data['y'][bin_selection == n]    
        mean_y[n] = np.sum(y_data)
        if data_mode == 'mean':
            mean_y[n] = mean_y[n]/noe[n]
            
        if errormode == 'sqrt':
            err[n] = np.sqrt(np.sum(y_data)+1)
            if data_mode == 'mean':
                err[n] = err[n] / noe[n]
                
        elif errormode == 'std dev':
            err[n] = np.sqrt(np.mean((y_data - mean_y[n])**2))

    return noe,mean_x,err_x,mean_y,err


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

def log_message(func):
    logging.basicConfig(filename='message_log',
                    format='%(asctime)s: %(message)s',
                    level=logging.INFO)

    def func_wrapper(self,message):
        if not message['message']['op'] == 'status' and \
           not message['message']['op'] == 'data' and \
           not message['message']['op'] == 'logbook_status' and\
           not message['message']['op'] == 'get_data' and\
           not message['message']['op'] == 'request_data' and\
           not message['message']['op'] == 'data_format':
            logging.info(message)
        if 'reply' in message.keys():
            if not message['reply']['parameters']['status'][0] == 0:
                logging.info(message)
        func(self,message)
    
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
