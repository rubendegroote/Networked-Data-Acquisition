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
    from connectors import Connector,Acceptor
except:
    from backend.Helpers import *
    from backend.connectors import Connector,Acceptor

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

        self.acceptors = []

        self.looping = True
        t = th.Thread(target = self.start).start()

    def start(self):
        while self.looping:
            asyncore.loop(count=1)
            time.sleep(0.1)

    def stop(self):
        self.looping = False

    def addInstructor(self, address=None):
        if address is None:
            print('provide IP address and PORT')
            return
        for name,add in self._instructors.items():
            if address == (add.chan[0],str(add.chan[1])):
                if self._instructorInfo[name][0]:
                    return
        try:
            instr = ArtistInstructor(chan=(address[0],int(address[1])), 
                callback=self.processInformation,onCloseCallback=self.instructorClosed)
            self._instructors[instr.artistName] = instr
            self._instructorInfo[instr.artistName] = (True,instr.chan[0],instr.chan[1])
            for c in self.acceptors:
                c.commQ.put(self._instructorInfo)
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

        for c in self.acceptors:
            c.commQ.put(self._instructorInfo)

    def processInformation(self,sender,data):
        self.format[sender.artistName] = data['format']
        if sender.scanning and data['measuring'] != self.measuring:
            self.measuring = data['measuring']
            if data['measuring']:
                self.notifyAll(['Measuring', self.scanNo])
            else:
                self.notifyAll(['idling'])
                self.scanToNext()

    def processRequests(self,sender,data):
        if data[0] == 'Add Artist':
            self.addInstructor(data[1])
            return None
        elif data[0] == 'Remove Artist':
            self.removeInstructor(data[1])
            return None
        elif data[0] == 'Scan':
            self.scan(data[1])
            return None
        elif data[0] == 'Stop Scan':
            self.stopScan()
            return None
        elif data == 'info':
            try:
                return sender.commQ.get_nowait()
            except:
                return (self._instructorInfo,[self.scanning,self.progress,self.format])
        else:
            return None

    def instructorClosed(self,instr):
        self._instructorInfo[instr.artistName] = (False,instr.chan[0],instr.chan[1])
        for c in self.acceptors:
            c.commQ.put(self._instructorInfo)

    def accClosed(self,acceptor):
        self.acceptors.remove(acceptor)

    def scan(self,scanInfo):
        name,self.scanPar = scanInfo[0].split(':')
        self.scanner = self._instructors[name]
        self.scanner.scanning = True
        self.curPos = 0
        self.scanRange = scanInfo[1]
        self.tPerStep = scanInfo[2]
        self.scanning = True
        self.scanNo += 1
        self.scanToNext()

    def stopScan(self):
        self.scanning = False
        self.scanner.scanning = False

    def notifyAll(self,instruction):
        for instr in self._instructors.values():
            instr.send_instruction(instruction)

    def scanToNext(self):
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
            if sender == 'MGui_to_M':
                self.acceptors.append(Acceptor(sock=sock,callback=self.processRequests,
                    onCloseCallback=self.accClosed,t='MGui_to_M'))
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

class ArtistInstructor(Connector):

    """docstring for ArtistInstructor"""

    def __init__(self,chan,callback,onCloseCallback):
        super(ArtistInstructor, self).__init__(chan,callback,onCloseCallback,t='M_to_A')
        self.scanning = False
        self.artistName = self.acceptorName

        self.send_next()

    def found_terminator(self):
        message = pickle.loads(self.buff)
        self.buff = b""
        self.callback(sender=self,data=message)
        self.send_next()

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

def makeManager(PORT=5007):
    return Manager(PORT)

def main():
    PORT = input('PORT?')
    d = makeManager(channels,int(PORT))

if __name__ == '__main__':
    main()
