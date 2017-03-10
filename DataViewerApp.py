from PyQt4 import QtCore,QtGui
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
CONFIG_PATH = os.getcwd() + "\\Config files\\config.ini"


class DataViewerApp(QtGui.QMainWindow):
    config_parser = configparser.ConfigParser()
    config_parser.read(CONFIG_PATH)

    fserver_ch = str(config_parser['IPs']['file_server'])
    fserver_port = int(config_parser['ports']['file_server'])
    fileServer_channel = (fserver_ch,fserver_port)
    
    server_ch = str(config_parser['IPs']['data_server'])
    server_port = int(config_parser['ports']['data_server'])
    dataserver_channel = (server_ch,server_port)

    def __init__(self):
        super(DataViewerApp, self).__init__()
        self.initialized = False
        self.mode = 'stream'
        self.scan_number = -1

        self.looping = True
        t = th.Thread(target=self.startIOLoop).start()

        self.init_UI()

        time.sleep(0.1)
        self.add_dataserver()

    def init_UI(self):
        widget = QtGui.QWidget()
        layout = QtGui.QGridLayout(widget)
        self.setCentralWidget(widget)

        self.mode_selector = QtGui.QComboBox()
        self.mode_selector.addItems(['stream','scan'])
        layout.addWidget(self.mode_selector,0,0,1,1)
        self.mode_selector.currentIndexChanged.connect(self.change_mode)

        self.graph = XYGraph('data_viewer')
        layout.addWidget(self.graph,1,0,10,10)

        self.setGeometry(200,100,1200,800)
        self.show()

    def change_mode(self):
        self.mode = self.mode_selector.currentText()
        self.data_server.add_request(('change_mode',{'mode':self.mode}))

    def stopIOLoop(self):
        self.looping = False

    def startIOLoop(self):
        while self.looping:
            asyncore.loop(count=1, timeout=0.01)
            time.sleep(0.03)

    def add_dataserver(self):
        try:
            self.data_server = Connector(name='R_to_DS',
                                         chan=self.dataserver_channel,
                                         callback=self.reply_cb,
                                         onCloseCallback=self.onCloseCallback,
                                         default_callback=self.default_cb)
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


    def data_format_reply(self,track,params):
        origin, track_id = track
        formats = params['data_format']

        if not formats == {} and not formats == self.graph.formats:
            self.graph.formats = formats
            self.graph.no_of_rows = {k:0 for k in self.graph.formats.keys()}
            self.graph.setXYOptions(self.graph.formats)

            self.initialized = True

        if 'current_scan' in params.keys(): #this is from the  data server
            if not str(params['current_scan']) == '-1':
                self.scan_number = params['current_scan']

    def closeEvent(self,event):
        self.stopIOLoop()
        event.accept()

def main():
    pg.setConfigOption('background', 'w')
    pg.setConfigOption('foreground', 'k')
    # add freeze support
    freeze_support()
    app = QtGui.QApplication(sys.argv)
    m = DataViewerApp()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
