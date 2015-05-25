import asyncore
import asynchat
import socket
import multiprocessing as mp
import ast
import logging
logging.basicConfig(filename='Manager.log',
                    format='%(asctime)s: %(message)s',
                    level=logging.INFO)
try:
    from Helpers import *
    from connectors import Connector, Acceptor
    import logbook as logbooks
except:
    from backend.Helpers import *
    from backend.connectors import Connector, Acceptor
    import backend.logbook as logbooks

from datetime import datetime
import configparser
import threading as th
import pickle
import numpy as np
import pandas as pd
import os
import time
import glob

SAVE_PATH = 'C:/Data/'


class Manager(asyncore.dispatcher):

    def __init__(self, artists=[], PORT=5007):
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
        self.scanParser = configparser.ConfigParser()
        self.progressParser = configparser.ConfigParser()
        self.logbookPath = SAVE_PATH + 'ManagerLogbook'
        try:
            self.logbook = logbooks.loadLogbook(self.logbookPath)
        except:
            self.logbook = []
        logbooks.saveLogbook(self.logbookPath, self.logbook)
        self.startMessage = 'Started scanning Artist {} from {:.2f} to {:.2f} V, in {:.0f} steps with {:.2f} seconds per step.'
        self.setpointMessage = 'Set Artist {} to {:.2f} V.'
        self.resumeMessage = 'Resumed scanning Artist {} from {:.2f} to {:.2f} V, in {:.0f} steps with {:.2f} seconds per step at step {:.0f}.'
        if os.path.isfile('ManagerScan.ini'):
            self.scanParser.read('ManagerScan.ini')
            self.scanNo = int(self.scanParser['scanprogress']['scanno'])

        self.acceptors = []
        self.viewers = []

        self.looping = True
        t = th.Thread(target=self.start).start()

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
        for name, add in self._instructors.items():
            if address == (add.chan[0], str(add.chan[1])):
                if self._instructorInfo[name][0]:
                    return
        try:
            instr = ArtistInstructor(chan=(address[0], int(address[1])),
                                     callback=self.processInformation,
                                     onCloseCallback=self.instructorClosed)
            self._instructors[instr.artistName] = instr
            self._instructorInfo[instr.artistName] = (
                True, instr.chan[0], instr.chan[1])
            for c in self.acceptors:
                c.commQ.put(self._instructorInfo)
            logging.info('Connected to ' + instr.artistName)
        except Exception as e:
            logging.info('Connection failed')

    def removeInstructor(self, address):
        toRemove = []
        for name, prop in self._instructorInfo.items():
            if address == (prop[1], str(prop[2])):
                self._instructors[name].close()
                toRemove.append(name)

        for name in toRemove:
            del self._instructors[name]
            del self._instructorInfo[name]

        for c in self.acceptors:
            c.commQ.put(self._instructorInfo)

    def processInformation(self, sender, data):
        self.format[sender.artistName] = data['format']
        if sender.scanning and data['measuring'] != self.measuring:
            self.measuring = data['measuring']
            if data['measuring']:
                self.notifyAll(['Measuring', self.scanNo])
            else:
                self.notifyAll(['idling'])
                self.scanToNext()

    def processRequests(self, sender, data):
        if data[0] == 'Add Artist':
            self.addInstructor(data[1])
            if os.path.isfile('scanprogress.ini'):
                self.progressParser.read('scanprogress.ini')
                self.curPos = ast.literal_eval(
                    self.progressParser['progress']['curpos'])
                self.tPerStep = ast.literal_eval(
                    self.progressParser['progress']['tperstep'])
                smin = ast.literal_eval(
                    self.progressParser['progress']['scanmin'])
                smax = ast.literal_eval(
                    self.progressParser['progress']['scanmax'])
                sl = self.progressParser['progress']['scanlength']
                self.resumeName = self.progressParser['progress']['name']
                self.scanRange = np.linspace(smin, smax, sl)
                return ['resumemessage', (smin, smax, sl, self.curPos, self.tPerStep, self.resumeName)]
            else:
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
        elif data[0] == 'Resume Scan':
            self.resumeScan()
            return None
        elif data[0] == 'Setpoint':
            self.setpoint(data[1])
            return None
        elif data == 'info':
            try:
                return sender.commQ.get_nowait()
            except:
                return ['infomessage', (self._instructorInfo, [self.scanning, self.progress, self.format])]
        else:
            return None

    def processLogbook(self, sender, data):
        if data == 'info':
            try:
                return sender.commQ.get_nowait()
            except:
                logs = set([f.split('entry')[0].split('\\')[1]
                            for f in glob.glob(SAVE_PATH + '\*_raw')])
                return ['Choices', tuple(logs)]

        elif data[0] == 'Get Logbook':
            return ['Logbook', self.logbook]
        elif data[0] == 'Edit Logbook':
            logbooks.editEntry(self.logbook, data[1], **data[2])
            logbooks.saveEntry(self.logbookPath, self.logbook, data[1])
            self.notifyAllLogs(['Notify', self.logbook[data[1]], data[1]])
        elif data[0] == 'Add To Logbook':
            newEntry = {key: '' for key in self.logbook[-1][-1].keys()}
            logbooks.addEntry(self.logbook, **newEntry)
            logbooks.saveEntry(self.logbookPath, self.logbook, -1)
            self.notifyAllLogs(
                ['Notify', self.logbook[-1], len(self.logbook) - 1])
        elif data[0] == 'Add Field To Logbook':
            field = data[1]
            for i, entry in enumerate(self.logbook):
                entry[-1][data[1]] = ''
                logbooks.editEntry(self.logbook, i, **entry[-1])
            self.notifyAllLogs(['Logbook', self.logbook])
        elif data[0] == 'Get Entry':
            return ['Entry', self.logbook[data[1]]]
        else:
            return None

    def instructorClosed(self, instr):
        self._instructorInfo[instr.artistName] = (
            False, instr.chan[0], instr.chan[1])
        for c in self.acceptors:
            c.commQ.put(self._instructorInfo)

    def accClosed(self, acceptor):
        self.acceptors.remove(acceptor)

    def viewClosed(self, viewer):
        self.viewers.remove(viewer)

    def resumeScan(self):
        self.scanner = self._instructors[self.resumeName]
        self.scanner.scanning = True
        self.scanPar = 'A0V'
        self.scanning = True
        self.scanNo += 1
        logbooks.addEntry(self.logbook, **{'Scan Number': self.scanNo,
                                           'Author': 'Automatic Entry',
                                           'Text': self.resumeMessage.format(name,
                                                                             self.scanRange[
                                                                                 0],
                                                                             self.scanRange[
                                                                                 -1],
                                                                             len(self.scanRange),
                                                                             self.tPerStep,
                                                                             self.curPos)})
        logbooks.saveEntry(self.logbookPath, self.logbook, -1)
        self.scanParser['scanprogress'] = {'scanno': self.scanNo}
        self.progressParser['progress'] = {'name': self.resumeName}
        with open('ManagerScan.ini', 'w') as scanfile:
            self.scanParser.write(scanfile)
        self.scanToNext()

    def scan(self, scanInfo):
        name, self.scanPar = scanInfo[0].split(':')
        self.scanner = self._instructors[name]
        self.scanner.scanning = True
        self.curPos = 0
        self.scanRange = scanInfo[1]
        self.tPerStep = scanInfo[2]
        self.scanning = True
        self.scanNo += 1
        self.scanParser['scanprogress'] = {'scanno': self.scanNo}
        self.progressParser['progress'] = {'name': name}
        logbooks.addEntry(self.logbook, **{'Scan Number': self.scanNo,
                                           'Author': 'Automatic Entry',
                                           'Text': self.startMessage.format(name,
                                                                            self.scanRange[
                                                                                0],
                                                                            self.scanRange[
                                                                                -1],
                                                                            len(self.scanRange),
                                                                            self.tPerStep,
                                                                            self.curPos)})
        logbooks.saveEntry(self.logbookPath, self.logbook, -1)
        with open('ManagerScan.ini', 'w') as scanfile:
            self.scanParser.write(scanfile)
        self.scanToNext()

    def setpoint(self, setpointInfo):
        name, self.scanPar = scanInfo[0].split(':')
        self.scanner = self._instructors[name]
        value = scanInfo[1]
        logbooks.addEntry(self.logbook, **{'Author': 'Automatic Entry',
                                           'Text': self.setpointMessage.format(name,
                                                                               value)})
        logbooks.saveEntry(self.logbookPath, self.logbook, -1)
        self.scanner.send_instruction(
            ["Change", self.scanPar, value])

    def stopScan(self):
        self.scanning = False
        self.scanner.scanning = False

    def notifyAll(self, instruction):
        for instr in self._instructors.values():
            instr.send_instruction(instruction)

    def notifyAllLogs(self, instruction):
        for viewer in self.viewers:
            viewer.commQ.put(instruction)

    def scanToNext(self):
        if not self.scanning:
            return

        if self.curPos == len(self.scanRange):
            self.progress = 100
            self.scanning = False
            self.scanner.scanning = False
            try:
                os.remove('scanprogress.ini')
            except FileNotFoundError:
                pass
            return

        self.scanner.send_instruction(
            ["Change", self.scanPar, self.scanRange[self.curPos], self.tPerStep])
        name = self.progressParser['progress']['name']
        self.progressParser['progress'] = {'curpos': self.curPos,
                                           'scanmin': self.scanRange[0],
                                           'scanmax': self.scanRange[-1],
                                           'scanlength': len(self.scanRange),
                                           'tperstep': self.tPerStep,
                                           'name': name}
        with open('scanprogress.ini', 'w') as scanprogressfile:
            self.progressParser.write(scanprogressfile)
        self.curPos += 1
        self.progress = int(self.curPos / len(self.scanRange) * 100)

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
                self.acceptors.append(Acceptor(sock=sock,
                                               callback=self.processRequests,
                                               onCloseCallback=self.accClosed,
                                               t='MGui_to_M'))
            elif sender == 'LGui_to_M':
                self.viewers.append(Acceptor(sock=sock,
                                             callback=self.processLogbook,
                                             onCloseCallback=self.viewClosed,
                                             t='LGui_to_M'))
            else:
                logging.error(
                    'Sender {} named {} not understood'.format(addr, sender))
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

    def __init__(self, chan, callback, onCloseCallback):
        super(ArtistInstructor, self).__init__(
            chan, callback, onCloseCallback, t='M_to_A')
        self.scanning = False
        self.artistName = self.acceptorName

        self.send_next()

    def found_terminator(self):
        message = pickle.loads(self.buff)
        self.buff = b""
        self.callback(sender=self, data=message)
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
    return Manager(PORT=PORT)


def main():
    PORT = input('PORT?')
    d = makeManager(int(PORT))

if __name__ == '__main__':
    main()
