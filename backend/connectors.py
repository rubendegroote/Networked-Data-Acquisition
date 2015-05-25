import asynchat
import socket
import multiprocessing as mp
import pickle
import time
import logging
from collections import deque


class Connector(asynchat.async_chat):

    def __init__(self, chan, callback, onCloseCallback=None, t=''):
        super(Connector, self).__init__()
        self.type = t
        self.callback = callback
        self.onCloseCallback = onCloseCallback
        self.chan = chan

        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        # self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self.connect(chan)
        logging.info('Connecting to {}...'.format(self.type))
        time.sleep(0.05)
        self.send(self.type.encode('UTF-8'))
        self.acceptorName = self.wait_for_connection()

        self.set_terminator('STOP_DATA'.encode('UTF-8'))
        self.buff = b''

        self.commQ = mp.Queue()

    def wait_for_connection(self):
        # Wait for connection to be made with timeout
        success = False
        now = time.time()
        while time.time() - now < 1:
            try:
                mes = self.recv(1024).decode('UTF-8')
                success = True
                break
            except:
                pass
        if not success:
            raise

        return mes

    def collect_incoming_data(self, data):
        self.buff += data

    def found_terminator(self):
        pass

    def send_next(self):
        self.push(pickle.dumps('info'))
        self.push('END_MESSAGE'.encode('UTF-8'))

    def handle_close(self):
        logging.info('Closing {} Connector'.format(self.type))
        try:
            self.onCloseCallback(self)
        except AttributeError:
            pass
        super(Connector, self).handle_close()


class Acceptor(asynchat.async_chat):

    def __init__(self, sock, callback=None, onCloseCallback=None, t=''):
        super(Acceptor, self).__init__(sock)
        self.set_terminator('END_MESSAGE'.encode('UTF-8'))
        self.callback = callback
        self.onCloseCallback = onCloseCallback
        self.type = t

        self.buff = b""
        self.commQ = mp.Queue()
        self.dataDQ = deque()

        self.push(self.type.encode('UTF-8'))

    def collect_incoming_data(self, data):
        self.buff += data

    def found_terminator(self):
        data = pickle.loads(self.buff)
        self.buff = b""

        ret = self.callback(sender=self, data=data)
        if not ret == None:
            self.push(pickle.dumps(ret))
            self.push('STOP_DATA'.encode('UTF-8'))
        else:
            info = self.callback(sender=self, data='info')
            self.push(pickle.dumps(info))
            self.push('STOP_DATA'.encode('UTF-8'))

    def handle_close(self):
        logging.info('Closing Acceptor {}'.format(self.type))
        try:
            self.onCloseCallback(self)
        except AttributeError:
            pass
        super(Acceptor, self).handle_close()
