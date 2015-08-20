import asynchat
import socket
import multiprocessing as mp
import json
import time
import logging
from collections import deque
try:
    from .Helpers import track
except:
    from Helpers import track



class Connector(asynchat.async_chat):
    def __init__(self, chan, callback, onCloseCallback=None, name='', defaultRequest='status'):
        super(Connector, self).__init__()
        self.name = name
        self.callback = callback
        self.onCloseCallback = onCloseCallback
        self.chan = chan
        self.defaultRequest = defaultRequest

        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        # self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self.connect(chan)
        logging.info('Connecting to {}...'.format(self.name))
        time.sleep(0.05)

        self.send(self.name.encode('UTF-8'))

        self.acceptorName = self.wait_for_connection()

        self.set_terminator('STOP_DATA'.encode('UTF-8'))
        self.buff = b''

        self.commQ = mp.Queue()
        self.requestQ = mp.Queue()


        self.send_request()

    def wait_for_connection(self):
        # Wait for connection to be made with timeout
        success = False
        now = time.time()
        while time.time() - now < 1:
            try:
                mes = self.recv(1024).decode('UTF-8')
                success = True
                break
            except Exception as e:
                pass
        if not success:
            raise

        return mes

    def collect_incoming_data(self, data):
        self.buff += data

    def found_terminator(self):
        message = json.loads(self.buff.decode('UTF-8'))
        self.buff = b""

        self.callback(message=message)
        
        self.send_request()

    def add_request(self, request):
        self.requestQ.put(request)

    def send_request(self):
        try:
            instr = self.requestQ.get_nowait()
            self.push({'message': instr})
        except:
            self.push({'message': {'op': self.defaultRequest, 'parameters': {}}})

    @track
    def push(self,message):
        dump = json.dumps(message)
        super(Connector, self).push(json.dumps(message).encode('UTF-8'))
        super(Connector, self).push('END_MESSAGE'.encode('UTF-8'))

    def handle_close(self):
        logging.info('Closing {} Connector'.format(self.name))
        try:
            self.onCloseCallback(self)
        except AttributeError:
            pass
        super(Connector, self).handle_close()


class Acceptor(asynchat.async_chat):

    def __init__(self, sock, callback=None, onCloseCallback=None, name=''):
        super(Acceptor, self).__init__(sock)
        self.set_terminator('END_MESSAGE'.encode('UTF-8'))
        self.callback = callback
        self.onCloseCallback = onCloseCallback
        self.name = name

        self.buff = b""
        self.commQ = mp.Queue()
        self.dataDQ = deque()

        super(Acceptor, self).push(self.name.encode('UTF-8'))

    def collect_incoming_data(self, data):
        self.buff += data

    def found_terminator(self):
        try:
            message = json.loads(self.buff.decode('UTF-8'))
        except ValueError as e:
            raise
        self.buff = b""

        ret = self.callback(message=message)
        if not ret == None:
            self.push(ret)

    @track
    def push(self,message):
        dump = json.dumps(message)
        super(Acceptor, self).push(json.dumps(message).encode('UTF-8'))
        super(Acceptor, self).push('STOP_DATA'.encode('UTF-8'))

    def handle_close(self):
        logging.info('Closing Acceptor {}'.format(self.name))
        try:
            self.onCloseCallback(self)
        except AttributeError:
            pass
        super(Acceptor, self).handle_close()
