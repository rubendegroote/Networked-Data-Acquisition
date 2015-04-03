import asyncore
import asynchat
import socket
import multiprocessing as mp
import logging
import threading as th
import pickle
import numpy as np
import pandas as pd
try:
    from Helpers import *
    from connectors import ManagerConnector
except:
    from backend.Helpers import *
    from backend.connectors import ManagerConnector

logging.basicConfig(format='%(asctime)s: %(message)s',
                    level=logging.INFO)


class Manager(asyncore.dispatcher):
    def __init__(self, artists=[],PORT=5007):
        super(Manager, self).__init__()
        self.port = PORT
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        # self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self.bind(('', self.port))
        self.listen(5)
        logging.info('Listening on port {}'.format(self.port))

        self.scanNo = 0
        self.progress = 0
        self.scanning = False
        self.format = {}
        self.measuring = False
        self._instructors = {}
        self._instructorInfo = {}
        for address in artists:
            self.addInstructor(address)

        self.conns = []

        self.looping = True
        t = th.Thread(target = self.start).start()

    def start(self):
        while self.looping:
            asyncore.loop(count=1)
            time.sleep(0.01)

    def stop(self):
        self.looping = False

    def addInstructor(self, address=None):
        if address is None:
            print('provide IP address and PORT')
            return
        for name,add in self._instructors.items():
            if address == (add.IP,str(add.PORT)):
                if self._instructorInfo[name][0]:
                    return
        try:
            instr = ArtistInstructor(IP=address[0], PORT=int(address[1]), manager = self)
            self._instructors[instr.artistName] = instr
            self._instructorInfo[instr.artistName] = (True,instr.IP,instr.PORT)
            for c in self.conns:
                c.connQ.put(self._instructorInfo)
            logging.info('Connected to ' + instr.artistName)
        except Exception as e:
            logging.info('Connection failed')

    def removeInstructor(self,address):
        toRemove = []
        for name,prop in self._instructorInfo.items():
            if address == (prop[1],str(prop[2])):
                self._instructors[name].close()
                toRemove.append(name)

        for name in toRemove:
            del self._instructors[name]
            del self._instructorInfo[name]

        for c in self.conns:
            c.connQ.put(self._instructorInfo)

    def instructorClosed(self,artistName):
        instr = self._instructors[artistName]
        self._instructorInfo[artistName] = (False,instr.IP,instr.PORT)
        for c in self.conns:
            c.connQ.put(self._instructorInfo)

    def connClosed(self,connector):
        self.conns.remove(connector)

    def scan(self,scanInfo):
        name,self.scanPar = scanInfo[0].split(':')
        self.scanner = self._instructors[name]
        self.scanner.scanning = True
        self.curPos = 0
        self.scanRange = scanInfo[1]
        self.tPerStep = scanInfo[2]
        self.scanning = True
        self.scanNo += 1
        self.sendNext()

    def stopScan(self):
        self.scanning = False
        self.scanner.scanning = False

    def notifyAll(self,instruction):
        for instr in self._instructors.values():
            instr.send_instruction(instruction)

    def sendNext(self):
        if not self.scanning:
            return

        if self.curPos == len(self.scanRange):
            self.progress = 100
            self.scanning = False
            self.scanner.scanning = False
            return

        self.scanner.send_instruction(
            ["Change",self.scanPar,self.scanRange[self.curPos],self.tPerStep])
        self.curPos +=1
        self.progress =  int(self.curPos / len(self.scanRange) * 100)

    def writeable(self):
        return False

    def readable(self):
        return True

    def handle_accept(self):
        pair = self.accept()
        if pair is not None:
            sock, addr = pair
            try:
                sender = self.get_sender_ID(sock)
                logging.info(sender)
            except:
                logging.warn('Sender {} did not send proper ID'.format(addr))
                return
            if sender == 'Connector':
                self.conns.append(ManagerConnector(sock, self))
            else:
                logging.error('Sender {} named {} not understood'
                              .format(addr, sender))
                return
            logging.info('Accepted {} as {}'.format(addr, sender))

    def get_sender_ID(self, sock):
        now = time.time()
        while time.time() - now < 5:  # Tested; raises RunTimeError after 5 s
            try:
                sender = sock.recv(1024).decode('UTF-8')
                break
            except:
                pass
        else:
            raise
        return sender

    def handle_close(self):
        logging.info('Closing Manager')
        super(Manager, self).handle_close()

class ArtistInstructor(asynchat.async_chat):

    """docstring for ArtistInstructor"""

    def __init__(self, IP='KSF402', PORT=5005, manager = None):
        super(ArtistInstructor, self).__init__()
        self.manager = manager
        self.scanning = False

        self.IP = IP
        self.PORT = PORT

        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self.connect((IP, PORT))
        self.set_terminator('STOP_DATA'.encode('UTF-8'))

        self.send('Manager'.encode('UTF-8'))
        self.artistName = ''
        self.artistName = self.wait_for_connection()
        self.message = b""

        self.send_continue()

    def wait_for_connection(self):
        # Wait for connection to be made with timeout
        success = False
        now = time.time()
        while time.time() - now < 1:
            try:
                name = self.recv(1024).decode('UTF-8')
                success = True
                break
            except Exception as e:
                pass
        if not success:
            raise
        return name

    def collect_incoming_data(self, data):
        self.message += data

    def found_terminator(self):
        message = pickle.loads(self.message)
        self.message = b""
        if message is not None:
            self.manager.format[self.artistName] = message['format']
            if self.scanning and message['measuring'] != self.manager.measuring:
                self.manager.measuring = message['measuring']
                if message['measuring']:
                    self.manager.notifyAll(['Measuring', self.manager.scanNo])
                else:
                    self.manager.notifyAll(['idling'])
                    self.manager.sendNext()
            
        self.send_continue()

    def send_continue(self):
        self.push(pickle.dumps('CONT'))
        self.push('END_MESSAGE'.encode('UTF-8'))

    def send_instruction(self, instruction):
        """
        Some additional info on the instructions options and syntax

        Changing a paramter:
            instruction = ["Change", parameter name, value]
        Scanning a paramter:
            instruction = ["Scan", parameter name, range, time per step]
        Stopping the DAQ loop:
            instruction = ["STOP"]
        Starting the DAQ loop:
            instruction = ["START"]
        Restarting the DAQ loop:
            instruction = ["RESTART"]
        Pauzing the DAQ loop:
            instruction = ["PAUZE"]
        Resuming the DAQ loop:
            instruction = ["RESUME"]
        Changing hardware settings:
            instruction = ["CHANGE SETTINGS",Dict with settings]
        """
        self.push(pickle.dumps(instruction))
        self.push('END_MESSAGE'.encode('UTF-8'))

    def handle_close(self):
        try:
            logging.info('Closing ArtistInstructor ' + self.artistName)
            self.manager.instructorClosed(self.artistName)
        except AttributeError:
            pass
        super(ArtistInstructor, self).handle_close()

def makeManager(channel=[('KSF402', 5005)],PORT=5004):
    return Manager(channel,PORT)

def main():
    channels = input('Artist IP,PORTS?').split(";")
    channels = [c.split(",") for c in channels]
    PORT = input('PORT?')
    d = makeManager(channels,int(PORT))

if __name__ == '__main__':
    main()
