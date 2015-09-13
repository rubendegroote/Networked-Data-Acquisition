import time
import copy
import logging
import h5py
import traceback

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
        while q.poll(0.0005):
            try:
                toSend.append(q.recv())
            except Exception as e:  # What to do here?
                pass
    return toSend

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
           not message['message']['op'] == 'data' and \
           not message['message']['op'] == 'logbook_status':
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
            reply = ([1],traceback.format_exc())
        return reply
    return func_wrapper