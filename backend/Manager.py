import asyncore
import asynchat
import socket
import sys
import multiprocessing as mp
import ast
from collections import OrderedDict
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
import json
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
        self.startMessage = 'Started scanning Artist {} from {:.8f} to {:.8f} cm-1, in {:.0f} steps with {:.8f} seconds per step.'
        self.setpointMessage = 'Set Artist {} to {:.8f} cm-1.'
        self.resumeMessage = 'Resumed scanning Artist {} from {:.8f} to {:.8f} cm-1, in {:.0f} steps with {:.8f} seconds per step at step {:.0f}.'
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
            instr = Connector(chan=(address[0], int(address[1])),
                                     callback=self.processInformation,
                                     onCloseCallback=self.instructorClosed, t='M_to_A')
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

    def processInformation(self, sender, message):
        reply_params = message['reply']['parameters']
        self.format[sender.artistName] = reply_params['format']
        if sender.scanning and reply_params['measuring'] != self.measuring:
            self.measuring = reply_params['measuring']
            if message['reply']['parameters']['measuring']:
                self.notifyAll(['Measuring', self.scanNo])
            else:
                self.notifyAll(['idling'])
                self.scanToNext()

    def processRequests(self, sender, message):
        if message['message']['op'] == 'add_artist':
            try:
                self.addInstructor(message['message']['parameters']['address'])
                params = {'status': 0}
            except Exception as e:
                logging.info('Connection failed')
                params = {'status': 1, 'exception': e}
            message = add_reply(message, params)
            return message
            # if os.path.isfile('scanprogress.ini'):
            #     self.progressParser.read('scanprogress.ini')
            #     self.curPos = ast.literal_eval(
            #         self.progressParser['progress']['curpos'])
            #     self.tPerStep = ast.literal_eval(
            #         self.progressParser['progress']['tperstep'])
            #     smin = ast.literal_eval(
            #         self.progressParser['progress']['scanmin'])
            #     smax = ast.literal_eval(
            #         self.progressParser['progress']['scanmax'])
            #     sl = self.progressParser['progress']['scanlength']
            #     self.resumeName = self.progressParser['progress']['name']
            #     self.scanRange = np.linspace(smin, smax, sl)
            #     try:
            #         os.remove('scanprogress.ini')
            #     except FileNotFoundError:
            #         pass
            #     return ['resumemessage', (smin, smax, sl, self.curPos, self.tPerStep, self.resumeName)]
            # else:
            #     return None
        elif message['message']['op'] == 'Remove Artist':
            self.removeInstructor(data[1])
            return None
        elif message['message']['op'] == 'Remove All Artists':
            toRemove = []
            for name, prop in self._instructorInfo.items():
                self._instructors[name].close()
                toRemove.append(name)
            for name in toRemove:
                del self._instructors[name]
                del self._instructorInfo[name]
            for c in self.acceptors:
                c.commQ.put(self._instructorInfo)
            return None
        elif message['message']['op'] == 'Scan':
            self.scan(data[1])
            return None
        elif message['message']['op'] == 'Stop Scan':
            self.stopScan()
            return None
        elif message['message']['op'] == 'Resume Scan':
            self.resumeScan()
            return None
        elif message['message']['op'] == 'Setpoint':
            self.setpoint(data[1])
            return None
        elif message['message']['op'] == 'info':
            params = {'instructor_info': self._instructorInfo,
                      'scan_number': self.scanNo,
                      'scanning': self.scanning,
                      'progress': self.progress,
                      'format': self.format}

            message['reply'] = {}
            message['reply']['op'] = message['message']['op'] + '_reply'
            message['reply']['parameters'] = params
            return message
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
            newEntry = {key: '' for key in self.logbook[-1][-1].keys() if not key == 'Scan Number'}
            if 'Tags' in self.logbook[-1][-1].keys():
                newEntry['Tags'] = OrderedDict()
                for t in self.logbook[-1][-1]['Tags'].keys():
                    newEntry['Tags'][t] = False
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
        elif data[0] == 'Add Tag To Logbook':
            tag = data[1]
            for i, entry in enumerate(self.logbook):
                if 'Tags' not in entry[-1]:
                    entry[-1]['Tags'] = OrderedDict()
                if tag not in entry[-1]['Tags']:
                    entry[-1]['Tags'][tag] = False
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
        try:
            newEntry = {key: '' for key in self.logbook[-1][-1].keys()}
            if 'Tags' in self.logbook[-1][-1].keys():
                newEntry['Tags'] = OrderedDict()
                for t in self.logbook[-1][-1]['Tags'].keys():
                    newEntry['Tags'][t] = False
        except:
            newEntry = {}
        entry = {'Scan Number': self.scanNo,
                 'Author': 'Automatic Entry',
                 'Text': self.resumeMessage.format(name,
                                                   self.scanRange[0],
                                                   self.scanRange[-1],
                                                   len(self.scanRange),
                                                   self.tPerStep,
                                                   self.curPos)}
        for key in entry.keys():
            newEntry[key] = entry[key]
        logbooks.addEntry(self.logbook, **newEntry)
        logbooks.saveEntry(self.logbookPath, self.logbook, -1)
        self.notifyAllLogs(
                ['Notify', self.logbook[-1], len(self.logbook) - 1])
        self.scanParser['scanprogress'] = {'scanno': self.scanNo}
        self.progressParser['progress'] = {'name': self.resumeName}
        with open('ManagerScan.ini', 'w') as scanfile:
            self.scanParser.write(scanfile)
        self.scanToNext()

    def scan(self, scanInfo):
        try:
            name, self.scanPar = scanInfo[0].split(':')
            self.scanner = self._instructors[name]
        except:
            logging.error('Could not start scan, no connection with Artist')
        self.scanner.scanning = True
        self.curPos = 0
        self.scanRange = scanInfo[1]
        self.tPerStep = scanInfo[2]
        self.scanning = True
        self.scanNo += 1
        self.scanParser['scanprogress'] = {'scanno': self.scanNo}
        self.progressParser['progress'] = {'name': name}
        try:
            newEntry = {key: '' for key in self.logbook[-1][-1].keys()}
            if 'Tags' in self.logbook[-1][-1].keys():
                newEntry['Tags'] = OrderedDict()
                for t in self.logbook[-1][-1]['Tags'].keys():
                    newEntry['Tags'][t] = False
        except:
            newEntry = {}
        entry = {'Scan Number': self.scanNo,
                 'Author': 'Automatic Entry',
                 'Text': self.startMessage.format(name,
                                                   self.scanRange[0],
                                                   self.scanRange[-1],
                                                   len(self.scanRange),
                                                   self.tPerStep)}
        for key in entry.keys():
            newEntry[key] = entry[key]
        logbooks.addEntry(self.logbook, **newEntry)
        logbooks.saveEntry(self.logbookPath, self.logbook, -1)
        self.notifyAllLogs(
                ['Notify', self.logbook[-1], len(self.logbook) - 1])
        with open('ManagerScan.ini', 'w') as scanfile:
            self.scanParser.write(scanfile)
        self.scanToNext()

    def setpoint(self, setpointInfo):
        name, self.scanPar = setpointInfo[0].split(':')
        self.scanner = self._instructors[name]
        value = setpointInfo[1]
        try:
            newEntry = {key: '' for key in self.logbook[-1][-1].keys()}
            if 'Tags' in self.logbook[-1][-1].keys():
                newEntry['Tags'] = OrderedDict()
                for t in self.logbook[-1][-1]['Tags'].keys():
                    newEntry['Tags'][t] = False
        except:
            newEntry = {}
        entry = {'Author': 'Automatic Entry',
                 'Text': self.setpointMessage.format(name, value)}
        for key in entry.keys():
            newEntry[key] = entry[key]
        logbooks.addEntry(self.logbook, **newEntry)
        logbooks.saveEntry(self.logbookPath, self.logbook, -1)
        self.notifyAllLogs(
                ['Notify', self.logbook[-1], len(self.logbook) - 1])
        self.scanner.add_instruction(
            ["Setpoint Change", self.scanPar, value])

    def stopScan(self):
        self.scanning = False
        self.scanner.scanning = False
        self.notifyAll(['idling'])

    def notifyAll(self, instruction):
        for instr in self._instructors.values():
            instr.add_instruction(instruction)

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

        self.scanner.add_instruction(
            ["Scan Change", self.scanPar, self.scanRange[self.curPos], self.tPerStep])
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

def makeManager(PORT=5007):
    return Manager(PORT=PORT)


def main():
    try:
        m = makeManager(5004)
        style = "QLabel { background-color: green }"
        e=''
    except Exception as e:
        style = "QLabel { background-color: red }"

    from PyQt4 import QtCore,QtGui
    # Small visual indicator that this is running
    app = QtGui.QApplication(sys.argv)
    w = QtGui.QWidget()

    w.setWindowTitle('Manager')
    layout = QtGui.QGridLayout(w)
    label = QtGui.QLabel(e)
    label.setStyleSheet(style)
    layout.addWidget(label)
    w.show()
    
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
