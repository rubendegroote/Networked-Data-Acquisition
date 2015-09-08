import asynchat
import socket
import multiprocessing as mp
import json
import time
from collections import deque
try:
    from .Helpers import track, make_message, log_message
except:
    from Helpers import track, make_message, log_message

class Connector(asynchat.async_chat):
    def __init__(self,name,chan,callback,
            onCloseCallback=None,default_callback=None):
        super(Connector,self).__init__()
        self.name = name
        self.callback = callback
        if onCloseCallback == None:
            self.onCloseCallback = lambda x: None
        else:
            self.onCloseCallback = onCloseCallback
        self.chan = chan
        self.default_callback = default_callback
        self.counter = 0

        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        # self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self.connect(chan)
        time.sleep(0.05)

        self.send(self.name.encode('UTF-8'))

        self.acceptorName = self.wait_for_connection()

        self.set_terminator('STOP_DATA'.encode('UTF-8'))
        self.buff = b''

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
        try:
            message = json.loads(self.buff.decode('UTF-8'))
            self.buff = b""
            self.callback(message=message)
        except Exception as e:
            print(e)
        finally:
            self.send_request()

    def add_request(self, request):
        self.requestQ.put(request)

    def send_request(self):
        try:
            message = self.requestQ.get_nowait()
        except:
            message = make_message(self.default_callback())

        self.push(message)

    @track
    @log_message
    def push(self,message):
        dump = (json.dumps(message) + "END_MESSAGE").encode('UTF-8')
        super(Connector, self).push(dump)
        # super(Connector, self).push('END_MESSAGE'.encode('UTF-8'))

    def handle_close(self):
        self.onCloseCallback(self)
        super(Connector, self).handle_close()


class Acceptor(asynchat.async_chat):

    def __init__(self, sock, callback=None, 
            onCloseCallback=None, name=''):
        super(Acceptor, self).__init__(sock)
        self.set_terminator('END_MESSAGE'.encode('UTF-8'))
        self.callback = callback
        self.onCloseCallback = onCloseCallback
        self.name = name
        self.counter = 0

        self.buff = b""

        super(Acceptor, self).push(self.name.encode('UTF-8'))

    def collect_incoming_data(self, data):
        self.buff += data

    def found_terminator(self):
        try:
            message = json.loads(self.buff.decode('UTF-8'))
            ret = self.callback(message=message)
            if not ret == None:
                self.push(ret)
        except ValueError as e:
            self.push({'reply': {'op': 'receive_fail', 
                'parameters': {'exception': str(e), 'status': [1],
                'attempt': self.buff.decode('UTF-8')}}})
        except Exception as e:
            print(e)
            print(self.buff.decode('UTF-8'))
        finally:
            self.buff = b""

    @track
    @log_message
    def push(self,message):
        dump = (json.dumps(message) + "STOP_DATA").encode('UTF-8')
        super(Acceptor, self).push(dump)
        # super(Acceptor, self).push('STOP_DATA'.encode('UTF-8'))

    def handle_close(self):
        self.onCloseCallback(self)
        super(Acceptor, self).handle_close()
