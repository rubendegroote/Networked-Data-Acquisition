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
        self.scan_number = -1
        self.progress = {}
        self.scanning = {}
        self.format = {}
        self.on_setpoint = {}

    @try_call
    def status(self, *args):
        params = {'connector_info': self.connInfo,
                  'scan_number': [self.scan_number],
                  'scanning': self.scanning,
                  'on_setpoint': self.on_setpoint,
                  'progress': self.progress,
                  'format': self.format}
        return params

    @try_call
    def start_scan(self, params):
        artist_name = params['artist'][0]
        scan_parameter = params['scan_parameter']
        scan_array = params['scan_array']
        time_per_step = params['time_per_step']
        
        self.scan_artist(artist_name,scan_parameter,scan_array,time_per_step)

        return {}

    def scan_artist(self,artist_name,scan_parameter,scan_array,time_per_step):
        self.scanner_name = artist_name
        scanner = self.connectors[artist_name]
        self.scan_number += 1
        self.set_all_scan_numbers(self.scan_number)
        scanner.add_request(('start_scan',{'scan_parameter':scan_parameter,
                                     'scan_array':scan_array,
                                     'time_per_step':time_per_step}))

    def start_scan_reply(self,track,params):
        origin, track_id = track[-1]
        self.notify_connectors(([0],"Artist {} received scanning instruction correctly.".format(origin)))

        # # logging stuff
        # self.scanParser['scanprogress'] = {'scan_number': self.scan_number}
        # self.progressParser['progress'] = {'name': name}
        # try:
        #     newEntry = {key: '' for key in self.logbook[-1][-1].keys()}
        #     if 'Tags' in self.logbook[-1][-1].keys():
        #         newEntry['Tags'] = OrderedDict()
        #         for t in self.logbook[-1][-1]['Tags'].keys():
        #             newEntry['Tags'][t] = False
        # except:
        #     newEntry = {}
        # entry = {'Scan Number': self.scan_number,
        #          'Author': 'Automatic Entry',
        #          'Text': self.startMessage.format(name,self.scanRange[0],
        #                                           self.scanRange[-1],
        #                                           len(self.scanRange),
        #                                           self.tPerStep)}
        # for key in entry.keys():
        #     newEntry[key] = entry[key]
        # logbooks.addEntry(self.logbook, **newEntry)
        # logbooks.saveEntry(self.logbookPath, self.logbook, -1)
        # self.notifyAllLogs(
        #         ['Notify', self.logbook[-1], len(self.logbook) - 1])
        # with open('ManagerScan.ini', 'w') as scanfile:
        #     self.scanParser.write(scanfile)

    @try_call
    def set_all_scan_numbers(self, number):
        op,params = 'set_scan_number',{'scan_number': [number]}
        for instr in self.connectors.values():
            instr.add_request((op,params))
        return {}

    def set_scan_number_reply(self,track,params):
        origin, track_id = track[-1]
        self.notify_connectors(([0],"Artist {} received scan number setting instruction correctly.".format(origin)))

    @try_call
    def stop_scan(self,params):
        self.set_all_scan_numbers(-1)
        self.connectors[self.scanner_name].add_request(('stop_scan',{}))
        return {}

    def stop_scan_reply(self,track,params):
        origin, track_id = track[-1]
        self.notify_connectors(([0],"Artist {} received stopping instruction correctly.".format(origin)))

    @try_call
    def go_to_setpoint(self, params):
        artist_name = params['artist'][0]
        parameter = params['parameter']
        setpoint = params['setpoint']
        
        self.set_artist(artist_name,parameter,setpoint)

        ## logging stuff
        # try:
        #     newEntry = {key: '' for key in self.logbook[-1][-1].keys()}
        #     if 'Tags' in self.logbook[-1][-1].keys():
        #         newEntry['Tags'] = OrderedDict()
        #         for t in self.logbook[-1][-1]['Tags'].keys():
        #             newEntry['Tags'][t] = False
        # except:
        #     newEntry = {}
        # entry = {'Author': 'Automatic Entry',
        #          'Text': self.setpointMessage.format(name, value)}
        # for key in entry.keys():
        #     newEntry[key] = entry[key]
        # logbooks.addEntry(self.logbook, **newEntry)
        # logbooks.saveEntry(self.logbookPath, self.logbook, -1)
        # self.notifyAllLogs(
        #         ['Notify', self.logbook[-1], len(self.logbook) - 1])
        # self.scanner.add_instruction(
        #     ["Setpoint Change", self.scanPar, value])

        return {}

    def set_artist(self,artist_name,parameter,setpoint):
        artist_to_set = self.connectors[artist_name]
        artist_to_set.add_request(('go_to_setpoint',{'parameter':parameter,
                                                     'setpoint':setpoint}))

    def go_to_setpoint_reply(self,track,params):
        origin, track_id = track[-1]
        self.notify_connectors(([0],"Artist {} received setpoint instruction correctly.".format(origin)))

    # def notify_all_logs(self, instruction):
    #     for viewer in self.viewers:
    #         viewer.commQ.put(instruction)

    def status_reply(self, track, params):
        origin, track_id = track[-1]
        self.format[origin] = params['format']
        self.scanning[origin] = params['scanning']
        self.progress[origin] = params['progress']
        self.on_setpoint[origin] = params['on_setpoint']

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
