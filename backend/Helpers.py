import pandas as pd
import time
import numpy as np
import copy
import logging
import h5py

SAVE_PATH = 'C:/Data/'


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
        time.sleep(0.01)
        while q.poll(0.0005):
            try:
                toSend.append(q.recv())
            except Exception as e:  # What to do here?
                pass
    return toSend


def mass_concat(array, format):
    data = np.concatenate([d for d in array])
    data = pd.DataFrame(data, columns=format)
    return data

def flatten(array):
    return [l for sub in array for l in sub]

def convert(data_list, format):
    data = np.array([l for subl in data_list for l in subl]).reshape(
        (-1, len(format)))
    data = pd.DataFrame(data, columns=format).set_index('time')
    return data


def save(data, name, artist):
    with pd.get_store(SAVE_PATH + name + '_stream.h5') as store:
        store.append(artist, data.convert_objects())
    groups = data.groupby('scan', sort=False)
    for n, group in groups:
        if not n == -1:
            with pd.get_store(SAVE_PATH + name + '_scan_' + str(int(n)) + '.h5') as store:
                store.append(artist, group.convert_objects())

def save_csv(data, name, artist=''):
    for n, group in groups:
        if n == -1:
            with open(SAVE_PATH + name + '_stream.csv', 'a') as f:
                group.to_csv(f, na_rep='nan')
        else:
            with open(SAVE_PATH + name + '_scan' + str(int(n)) + '.csv', 'a') as f:
                group.to_csv(f, na_rep='nan')

def save_continuously(saveQ,saveDir,name,format):
    save_interval = 2
    format = [f.encode('utf-8') for f in format]
    store = h5py.File(saveDir + 'artist_data.h5','a')
    to_save = np.row_stack(flatten(emptyPipe(saveQ)))    
    try:
        store.create_dataset(name,
            data=to_save,
            shape=(to_save.shape[0],to_save.shape[1]),
            maxshape=(None,to_save.shape[1]),chunks=True)
        store[name].attrs['format'] = format
        store.close()
    except RuntimeError as e:
        print('Data file for artist {} exist, will append...'.format(name))
        pass

    while True:
        now = time.time()

        to_save = np.row_stack(flatten(emptyPipe(saveQ)))
        with h5py.File(saveDir + 'artist_data.h5','a') as store:
            newshape = (store[name].shape[0] + to_save.shape[0],
                                to_save.shape[1])
            store[name].resize(newshape)
            store[name][-to_save.shape[0]:] = to_save

        # slightly more stable if the save runs every 0.5 seconds,
        # regardless of how long the previous saving took
        wait = abs(min(0, time.time() - now - save_interval))
        time.sleep(wait)

def make_message(op,params):
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
            reply_dict['status'] = [0]
        except Exception as e:
            reply_dict = {'status': [1], 'exception': str(e)}
        return reply_dict
    return func_wrapper

def log_message(func):
    logging.basicConfig(filename='message_log',
                    format='%(asctime)s: %(message)s',
                    level=logging.INFO)

    def func_wrapper(self,message):
        if not message['message']['op'] == 'status' and \
           not message['message']['op'] == 'data':
            logging.info(message)
        if 'reply' in message.keys():
            if not message['reply']['parameters']['status'][0] == 0:
                logging.info(message)
        func(self,message)
    
    return func_wrapper
        
