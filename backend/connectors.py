import asynchat
import asyncore
import socket
import multiprocessing as mp
import pickle
import time
import logging

logging.basicConfig(format='%(asctime)s: %(message)s',
                    level=logging.INFO)

class Man_DS_Connection():
    def __init__(self,ManChan,DSChan,callBack):
        self.AppCallBack = callBack
        try:
            self.man = ManagerConnection(ManChan,
                callback = self.callBack)
        except Exception as e:
            self.man = None

        try:
            self.DS = DataServerConnection(DSChan,
                callback = self.callBack)
        except Exception as e:
            self.DS = None

    def getArtistInfo(self):
        retDict = {}
        keys = set(self.DS.artists.keys()).union(set(self.man.artists.keys()))
        for key in keys:
            if key in self.man.artists.keys():
                if key in self.DS.artists.keys():
                    retDict[key] = (self.man.artists[key][0],self.DS.artists[key][0],
                                                        self.man.artists[key][1:])
                else:
                    retDict[key] = (self.man.artists[key][0],False,
                                                        self.man.artists[key][1:])
            else:
                retDict[key] = False,self.DS.artists[key][0],self.DS.artists[key][1:]

        return retDict

    def getScanInfo(self):
        return self.man.format,self.man.progress,self.man.artists

    def scanning(self):
        return self.man.scanning

    def instruct(self,t,instr):
        print(t,instr)
        if t == 'Manager':
            self.man.connQ.put(instr)
        elif t =='Data Server':
            self.DS.connQ.put(instr)
        elif t =='Both':
            self.man.connQ.put(instr)
            self.DS.connQ.put(instr)

    def callBack(self,info):
        # perhaps use this to change some settings or whatnot
        self.AppCallBack(info)

class Connection(asynchat.async_chat):
    def __init__(self,chan,callback,t=''):
        super(Connection,self).__init__()
        self.type = t
        self.callback = callback
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        # self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self.connect(chan)
        logging.info('Connecting to {}...'.format(self.type))
        self.send('Connector'.encode('UTF-8'))
        self.wait_for_connection()
        self.IP = chan[0]
        self.PORT = chan[1]

        self.set_terminator('STOP_DATA'.encode('UTF-8'))
        self._buffer = b''

        self.connQ = mp.Queue()
        self.artists = {}

        self.push(pickle.dumps(['ARTISTS?']))
        self.push('END_MESSAGE'.encode('UTF-8'))

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

    def collect_incoming_data(self, data):
        self._buffer += data

    def found_terminator(self):
        pass
    def send_next(self):
        self.push(pickle.dumps('NEXT'))
        self.push('END_MESSAGE'.encode('UTF-8'))

    def handle_close(self):
        try:
            logging.info('Closing {} Connection'.format(self.type))
            self.callback(self.type)
        except AttributeError:
            pass
        super(Connection, self).handle_close()

class ManagerConnection(Connection):
    def __init__(self,chan,callback):
        super(ManagerConnection,self).__init__(chan,callback,t='Manager')
        self.progress = 0
        self.scanning = False
        self.format = {}

    def found_terminator(self):
        buff = self._buffer
        self._buffer = b''
        data = pickle.loads(buff)
        if type(data) == dict:
            self.artists = data
        else:
            self.scanning,self.progress,self.format = data
        try:
            info = self.connQ.get_nowait()
            self.push(pickle.dumps(info))
            self.push('END_MESSAGE'.encode('UTF-8'))
        except:
            pass

        self.send_next()

class DataServerConnection(Connection):
    def __init__(self,chan,callback):
        super(DataServerConnection,self).__init__(chan,callback,t='DataServer')

    def found_terminator(self):
        buff = self._buffer
        self._buffer = b''
        data = pickle.loads(buff)
        if type(data) == dict:
            self.artists = data
        try:
            info = self.connQ.get_nowait()
            self.push(pickle.dumps(info))
            self.push('END_MESSAGE'.encode('UTF-8'))
        except:
            pass

        self.send_next()


class Connector(asynchat.async_chat):
    def __init__(self,sock,master=None,t=''):
        super(Connector, self).__init__(sock)
        self.set_terminator('END_MESSAGE'.encode('UTF-8'))
        self.master = master
        self.type = t
        self.buff = b""
        self.connQ = mp.Queue()

        self.push('CONNECTED'.encode('UTF-8'))

    def collect_incoming_data(self, data):
        self.buff += data

    def handle_close(self):
        logging.info('Closing {} Connector'.format(self.type))
        self.master.connClosed(self)
        super(Connector, self).handle_close() 

class ManagerConnector(Connector):
    def __init__(self,sock,master):
        super(ManagerConnector,self).__init__(sock,master=master,t='Manager')

    def found_terminator(self):
        buff = self.buff
        self.buff = b""

        data = pickle.loads(buff)

        if data[0] == 'ARTISTS?':
            self.push(pickle.dumps(self.master._instructorInfo))
            self.push('STOP_DATA'.encode('UTF-8'))
        elif data[0] == 'Add Artist':
            self.master.addInstructor(data[1])
        elif data[0] == 'Remove Artist':
            self.master.removeInstructor(data[1])
        elif data[0] == 'Scan':
            self.master.scan(data[1])
        elif data[0] == 'Stop Scan':
            self.master.stopScan()

        try:
            info = self.connQ.get_nowait()
            self.push(pickle.dumps(info))
            self.push('STOP_DATA'.encode('UTF-8'))
        except: 
            self.push(pickle.dumps([self.master.scanning,self.master.progress,
                    self.master.format]))
            self.push('STOP_DATA'.encode('UTF-8'))

class DataServerConnector(Connector):
    def __init__(self,sock,master):
        super(DataServerConnector,self).__init__(sock,master=master,t='DataServer')

    def found_terminator(self):
        buff = self.buff
        self.buff = b""

        data = pickle.loads(buff)

        if data[0] == 'ARTISTS?':
            self.push(pickle.dumps(self.master._readerInfo))
            self.push('STOP_DATA'.encode('UTF-8'))
        elif data[0] == 'Add Artist':
            self.master.addReader(data[1])
        elif data[0] == 'Remove Artist':
            self.master.removeReader(data[1])

        try:
            info = self.connQ.get_nowait()
            self.push(pickle.dumps(info))
            self.push('STOP_DATA'.encode('UTF-8'))
        except:
            self.push(pickle.dumps(self.master.bitrates))
            self.push('STOP_DATA'.encode('UTF-8'))
