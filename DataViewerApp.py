from PyQt5 import QtCore, QtGui, QtWidgets
import pyqtgraph as pg
import threading as th
import asyncore
import time
import pandas as pd
import numpy as np
from multiprocessing import freeze_support
import sys,os

from scanner import ScannerWidget
from connect import ConnectionsWidget
from graph import XYGraph

from backend.connectors import Connector

import configparser
CONFIG_PATH = "\\\\cern.ch\\dfs\\Users\\c\\CRIS\\Documents\\Networked-Data-Acquisition\\Config files\\config.ini"

class DataViewerApp(QtWidgets.QMainWindow):
    config_parser = configparser.ConfigParser()
    config_parser.read(CONFIG_PATH)

    fserver_ch = str(config_parser['IPs']['file_server'])
    fserver_port = int(config_parser['ports']['file_server'])
    fileserver_channel = (fserver_ch,fserver_port)
    
    server_ch = str(config_parser['IPs']['data_server'])
    server_port = int(config_parser['ports']['data_server'])
    dataserver_channel = (server_ch,server_port)

    launch_chooser_signal = QtCore.pyqtSignal()
    closeChooser =  QtCore.pyqtSignal()
    def __init__(self):
        super(DataViewerApp, self).__init__()
        self.initialized = False
        self.scan_number = -1

        self.looping = True
        t = th.Thread(target=self.startIOLoop).start()

        self.init_UI()

        self.setWindowTitle('Data Viewer')

        self.chooser_required = False    
        self.launch_chooser_signal.connect(self.launch_chooser)
        self.closeChooser.connect(self.close_chooser)
        self.mode = 'stream'
        self.graph.mode = 'stream'

        time.sleep(0.1)
        self.add_dataserver()
        self.add_fileserver()

    def init_UI(self):
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QGridLayout(widget)
        self.setCentralWidget(widget)

        self.stream_mode_button = QtWidgets.QPushButton('Stream')
        self.stream_mode_button.setCheckable(True)
        self.stream_mode_button.setChecked(True)
        layout.addWidget(self.stream_mode_button,0,0,1,1)
        self.stream_mode_button.clicked.connect(self.change_mode_stream)

        self.scan_mode_button = QtWidgets.QPushButton('Scan')
        self.scan_mode_button.setCheckable(True)
        self.scan_mode_button.setChecked(False)
        layout.addWidget(self.scan_mode_button,0,1,1,1)
        self.scan_mode_button.clicked.connect(self.change_mode_scan)

        self.fs_mode_button = QtWidgets.QPushButton('Completed scans')
        self.fs_mode_button.setCheckable(True)
        self.fs_mode_button.setChecked(False)
        layout.addWidget(self.fs_mode_button,0,2,1,1)
        self.fs_mode_button.clicked.connect(self.change_mode_fs)

        self.graph = XYGraph('data_viewer')
        layout.addWidget(self.graph,1,0,10,10)

        self.setGeometry(200,100,1200,800)
        self.show()

    def change_mode_stream(self,clicked):
        if clicked:
            self.scan_mode_button.setChecked(False)
            self.fs_mode_button.setChecked(False)
        else:
            self.stream_mode_button.setChecked(True)
        self.mode = 'stream'
        self.graph.mode = 'stream'
        self.graph.newXY()
        self.graph.reset_data()

        self.data_server.add_request(('change_mode',{'mode':self.mode}))

        self.graph.comboX.setEnabled(True)
        self.graph.comboY.setEnabled(True)

    def change_mode_scan(self,clicked):
        if clicked:
            self.stream_mode_button.setChecked(False)
            self.fs_mode_button.setChecked(False)
        else:
            self.scan_mode_button.setChecked(True)
        self.mode = 'scan'
        self.graph.mode = 'scan'
        self.graph.newXY()
        self.graph.reset_data()

        self.data_server.add_request(('change_mode',{'mode':self.mode}))

        self.graph.comboX.setEnabled(True)
        self.graph.comboY.setEnabled(True)

    def change_mode_fs(self,clicked):
        self.chooser_required = True
        if clicked:
            self.scan_mode_button.setChecked(False)
            self.stream_mode_button.setChecked(False)
        else:
            self.fs_mode_button.setChecked(True)
        self.mode = 'fs'
        self.graph.mode = 'fs'

        self.graph.comboX.setDisabled(True)
        self.graph.comboY.setDisabled(True)

    def stopIOLoop(self):
        self.looping = False

    def startIOLoop(self):
        while self.looping:
            asyncore.loop(count=1, timeout=0.01)
            time.sleep(0.03)

    def add_dataserver(self):
        try:
            self.data_server = Connector(name='V_to_DS',
                                         chan=self.dataserver_channel,
                                         callback=self.reply_cb,
                                         onCloseCallback=self.onCloseCallback,
                                         default_callback=self.default_cb)
        except Exception as e:
            print(e)

    def add_fileserver(self):
        try:
            self.file_server = Connector(name='V_to_FS',
                                         chan=self.fileserver_channel,
                                         callback=self.reply_cb,
                                         onCloseCallback=self.onCloseCallback,
                                         default_callback=self.default_cb_fileserver)
        except Exception as e:
            print(e)

    def reply_cb(self,message):
        if message['reply']['parameters']['status'][0] == 0:
            function = message['reply']['op']
            args = message['reply']['parameters']
            track = message['track']

            params = getattr(self, function)(track,args)
        else:
            print('DataViewer received fail message', message)

    def default_cb(self):
        if not self.mode == 'fs':
        # data server time!
            if not self.initialized:
                return 'data_format',{}
            elif self.graph.reset:
                self.graph.reset_data()
                return 'get_data',{'no_of_rows':self.graph.no_of_rows,
                               'x':self.graph.x_key,
                               'y':self.graph.y_key}

            else:
                return 'get_data',{'no_of_rows':self.graph.no_of_rows,
                               'x':self.graph.x_key,
                               'y':self.graph.y_key}
        else:
        #file server time
            return 'data_format',{}

    def default_cb_fileserver(self):
        if self.mode == 'fs':
        #file server time
            return 'get_status', {}
        else:
        # data server time!
            return 'get_status',{}

    def onCloseCallback(self,connector):
        print('lost connection')

    def change_mode_reply(self,track,params):
        self.graph.reset_data()

    def get_data_reply(self,track,params):
        origin, track_id = track
        data = params['data']
        scan_number = params['current_scan']
        mass = params['mass']

        if data == []:
            return

        self.graph.mass = mass
        self.graph.scan_number = int(scan_number)

        self.graph.no_of_rows = params['no_of_rows']

        data_x = pd.DataFrame({'time':np.array(data[0]),'x':data[1]})
        # number added to fix graphical jitter
        data_y = pd.DataFrame({'time':np.array(data[2])+1./10*10**-6,'y':data[3]})

        data = pd.concat([data_x,data_y])

        if self.mode == 'stream':
            self.graph.data = self.graph.data.append(data)
            if not str(scan_number) == '-1':
                self.scan_number = scan_number
        elif self.mode == 'scan':
            if not self.scan_number == scan_number:
                self.graph.data = data
                self.scan_number = scan_number
            else:
                self.graph.data = self.graph.data.append(data)
        self.graph.plot_needed = True

    def data_format_reply(self,track,params):
        origin, track_id = track
        formats = params['data_format']

        if not formats == {} and not formats == self.graph.formats:
            self.graph.formats = formats
            self.graph.no_of_rows = {k:0 for k in self.graph.formats.keys()}
            self.graph.setXYOptions(self.graph.formats)

            self.initialized = True

        if not str(params['current_scan']) == '-1':
            self.scan_number = params['current_scan']

    def get_status_reply(self,track,params):
        available_scans = params['available_scans']
        masses = params['masses']
        sorted_results = sorted(zip(available_scans,masses),key=lambda x:x[0])
        available_scans,masses = [[x[i] for x in sorted_results] for i in range(2)]

        self.available_scans = np.array(available_scans,dtype=int)
        self.masses = np.array(masses,dtype=int)

        if self.chooser_required:
            self.chooser_required = False
            self.launch_chooser_signal.emit()

    def launch_chooser(self):
        self.chooser = ScanChooser(self,self.masses,self.available_scans)
        self.chooser.formats_requested.connect(self.fetch_formats)
        self.chooser.scans_requested.connect(self.fetch_scans)
        self.chooser.exec_()

    def close_chooser(self):
        self.chooser.close()
        del self.chooser

    def fetch_formats(self):
        self.graph.mass = self.chooser.mass

        self.file_server.add_request(('scan_format', {'scans':self.chooser.scan_numbers}))

    def scan_format_reply(self,track,params):
        format = params['format']
        self.chooser.set_format(format)
        
    def fetch_scans(self):
        self.graph.x_key = self.chooser.xkey.split(': ')
        self.graph.y_key = self.chooser.ykey.split(': ')
        self.graph.verify_unit_check()
        self.graph.reset_data()

        self.scan_numbers = self.chooser.scan_numbers
        self.graph.scan_number = self.scan_numbers

        self.xkey = self.chooser.xkey
        self.ykey = self.chooser.ykey
        self.file_server.add_request(('request_data',{'scan_numbers':self.scan_numbers,
                                             'x':self.xkey,'y':self.ykey}))

    def request_data_reply(self,track,params):
        data = params['data']
        done = params['done']
        # progress = params['progress']

        data = pd.DataFrame({'time':data[0],'x':data[1],'y':data[2]})
        self.graph.data = self.graph.data.append(data)
        self.graph.plot_needed = True
        # self.graph.progress = int(100*progress)
        try:
            self.chooser
            self.closeChooser.emit()
        except:
            pass

        if not done:
            self.file_server.add_request(('request_data',{'scan_numbers':self.scan_numbers,
                                             'x':self.xkey,'y':self.ykey}))

    def closeEvent(self,event):
        self.stopIOLoop()
        event.accept()

class ScanChooser(QtWidgets.QDialog):
    scans_requested = QtCore.pyqtSignal()
    formats_requested = QtCore.pyqtSignal()
    def __init__(self,parent,masses,scans):
        super(QtWidgets.QDialog, self).__init__(parent)
        self.layout = QtWidgets.QGridLayout(self)

        self.layout.addWidget(QtWidgets.QLabel('Select mass:'),1,0)
        self.mass_selector = QtGui.QComboBox()
        self.mass_selector.currentIndexChanged.connect(self.mass_changed)
        self.layout.addWidget(self.mass_selector,1,1)

        self.layout.addWidget(QtWidgets.QLabel('Scans:'),2,0)

        self.fetch_formats_button = QtWidgets.QPushButton('Get x,y info')
        self.layout.addWidget(self.fetch_formats_button,19,3,1,1)
        self.fetch_formats_button.clicked.connect(self.fetch_formats)

        self.scan_selector = QtWidgets.QWidget()
        self.scan_layout = QtWidgets.QGridLayout(self.scan_selector)
        self.layout.addWidget(self.scan_selector,3,0,16,3)

        # self.setGeometry(1400,100,400,800)

        self.masses = masses
        self.scans = scans

        masses_list = sorted(list(set(masses)))
        self.mass_selector.clear()
        self.mass_selector.addItems([str(m) for m in masses_list])
        
        self.xkey = []
        self.ykey = []

        self.layout.addWidget(QtWidgets.QLabel('x: '),20,0)
        self.comboX = QtGui.QComboBox(parent=None)
        self.comboX.setMinimumWidth(250)
        self.comboX.setToolTip('Choose the variable you want to put\
 on the X-axis.')
        self.layout.addWidget(self.comboX, 20, 1)
        
        self.layout.addWidget(QtWidgets.QLabel('y: '),21,0)
        self.comboY = QtGui.QComboBox(parent=None)
        self.comboY.setMinimumWidth(250)
        self.comboY.setToolTip('Choose the variable you want to put\
 on the Y-axis.')
        self.layout.addWidget(self.comboY, 21, 1)

        self.fetch_scans_button = QtWidgets.QPushButton('Fetch scans')
        self.fetch_scans_button.setDisabled(True)
        self.layout.addWidget(self.fetch_scans_button,22,3,1,1)
        self.fetch_scans_button.clicked.connect(self.fetch_scans)

        self.layout.setColumnStretch(5, 1)
        self.layout.setRowStretch(30, 1)

    def mass_changed(self):
        for i in reversed(range(self.scan_layout.count())): 
            self.scan_layout.itemAt(i).widget().setParent(None)

        mass = self.mass_selector.currentText()
        slicer = self.masses == int(mass)
        scans = self.scans[slicer]
        self.scan_checks = {}
        i = 0
        for scan in scans:
            if not scan == -1.0:
                self.scan_checks[scan]=QtGui.QCheckBox(str(scan))
                self.scan_layout.addWidget(self.scan_checks[scan],i//3,i%3)
                i=i+1
        self.mass = mass

    def fetch_formats(self):
        self.scan_numbers = [int(name) for name,check in self.scan_checks.items() \
                                if check.isChecked()]
        if self.scan_numbers == []:
            return
        else:
            self.formats_requested.emit()

    def set_format(self, options):
        self.fetch_formats_button.setDisabled(True)
        self.scan_selector.setDisabled(True)
        self.mass_selector.setDisabled(True)

        opts = ['device: parameter']
        opts.extend(options)

        opts = sorted(opts)

        self.comboX.addItems(opts)
        try:
            self.comboX.setCurrentIndex(opts.index('wavemeter: wavenumber_1'))
        except:
            self.comboX.setCurrentIndex(0)

        self.comboY.addItems(opts)
        try:
            self.comboY.setCurrentIndex(opts.index('cris: Counts'))
        except:
            self.comboY.setCurrentIndex(0)

        self.fetch_scans_button.setEnabled(True)

    def fetch_scans(self):
        self.comboX.setDisabled(True)
        self.comboY.setDisabled(True)

        self.xkey = self.comboX.currentText()
        self.ykey = self.comboY.currentText()
        if self.xkey == 'device: parameter' and self.ykey == 'device: parameter':
            return
        else:
            self.scans_requested.emit()
            self.fetch_scans_button.setDisabled(True)
        self.fetch_scans_button.setText('Fetching...')

def main():
    pg.setConfigOption('background', 'w')
    pg.setConfigOption('foreground', 'k')
    # add freeze support
    freeze_support()
    app = QtWidgets.QApplication(sys.argv)
    m = DataViewerApp()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
