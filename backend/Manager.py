import asyncore
import asynchat
import socket
import sys
import multiprocessing as mp
import ast
from collections import OrderedDict
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
from dispatcher import Dispatcher

SAVE_PATH = 'C:/Data/'


class Manager(Dispatcher):
    def __init__(self, PORT=5007, name='Manager'):
        super(Manager, self).__init__(PORT, name)
        self.scanNo = -1
        self.progress = 0
        self.scanning = False
        self.format = {}
        self.on_setpoint = False

    @try_call
    def status(self, *args):
        params = {'connector_info': self.connInfo,
                  'scan_number': [self.scanNo],
                  'scanning': self.scanning,
                  'progress': [self.progress],
                  'format': self.format}
        return params

    @try_call
    def resume_scan(self):
        self.scanner = self.connectors[self.resumeName]
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

        return {}

    @try_call
    def start_scan(self, scanInfo):
        name, self.scanPar = scanInfo[0].split(':')
        self.scanner = self.connectors[name]
        self.scanner.scanning = True
        self.curPos = 0
        self.scanRange = scanInfo[1]
        self.tPerStep = scanInfo[2]
        self.scanning = True
        self.scanNo += 1
        self.set_all_scan_numbers(self.scanNo)       
        
        self.scanToNext()

        # logging stuff
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

        return {}

    @try_call
    def go_to_setpoint(self, setpointInfo):
        name, self.scanPar = setpointInfo[0].split(':')
        self.scanner = self.connectors[name]
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

        return {}

    @try_call
    def stop_scan(self):
        self.scanning = False
        self.scanner.scanning = False
        self.set_all_scan_numbers(-1)
        return {}

    @try_call
    def set_all_scan_numbers(self, number):
        op,params = 'set_scan_number',{'scan_number': [number]}
        for instr in self.connectors.values():
            instr.add_request(make_message(op,params))
        return {}

    # def notify_all_logs(self, instruction):
    #     for viewer in self.viewers:
    #         viewer.commQ.put(instruction)

    def scan_to_next(self):
        if not self.scanning:
            return False

        if self.curPos == len(self.scanRange):
            self.progress = 100
            self.scanning = False
            try:
                os.remove('scanprogress.ini')
            except FileNotFoundError:
                pass

            return False

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

        return True


    def status_reply(self, origin, params):
        self.format[origin] = params['format']
        if params['scanning'] and params['on_setpoint'] != self.on_setpoint:
            self.on_setpoint = params['on_setpoint']
            if params['on_setpoint']:
                pass
            else:
                step_successful = self.scan_to_next()
                if not step_successful:
                    self.stop_scan()

def makeManager(PORT=5007):
    return Manager(PORT=PORT)


def main():
    # try:
    m = makeManager(5004)
    #     style = "QLabel { background-color: green }"
    #     e=''
    # except Exception as e:
    #     style = "QLabel { background-color: red }"

    # from PyQt4 import QtCore,QtGui
    # # Small visual indicator that this is running
    # app = QtGui.QApplication(sys.argv)
    # w = QtGui.QWidget()

    # w.setWindowTitle('Manager')
    # layout = QtGui.QGridLayout(w)
    # label = QtGui.QLabel(e)
    # label.setStyleSheet(style)
    # layout.addWidget(label)
    # w.show()
    
    # sys.exit(app.exec_())


if __name__ == '__main__':
    main()
