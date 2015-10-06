from PyQt4 import QtCore,QtGui
import pyqtgraph as pg
import threading as th
import asyncore
import time
import pandas as pd
import numpy as np
from multiprocessing import freeze_support
import sys

from scanner import ScannerWidget
from connect import ConnectionsWidget
from graph import MyGraph

from backend.connectors import Connector

dataserver_channel = ('PCCRIS1',5005)
fileServer_channel = ('PCCRIS1', 5006)

class DataViewerApp(QtGui.QMainWindow):
    update_scan_list_signal = QtCore.pyqtSignal()
    def __init__(self):
        super(DataViewerApp, self).__init__()
        self.initialized = False
        self.live_viewing = True
        self.mode = 'stream'
        self.scan_number = -1
        self.available_scans = []
        self.masses = []
        self.scan_children = {}
        self.mass_children = {}

        self.looping = True
        t = th.Thread(target=self.startIOLoop).start()

        self.init_UI()

        self.update_scan_list_signal.connect(self.update_scan_list)

        time.sleep(0.1)
        self.add_dataserver()
        self.add_fileserver()

    def init_UI(self):
        self.central = QtGui.QSplitter()
        widget = QtGui.QWidget()
        self.central.addWidget(widget)
        layout = QtGui.QGridLayout(widget)
        self.setCentralWidget(self.central)

        self.dataTree = QtGui.QTreeWidget()
        self.dataTree.setColumnCount(1)
        self.dataTree.itemDoubleClicked.connect(self.change_mode)
        self.live_item = QtGui.QTreeWidgetItem(['live'])
        self.live_item.insertChildren(0,[QtGui.QTreeWidgetItem(['stream']),
                                        QtGui.QTreeWidgetItem(['scan'])])
        self.scans_item = QtGui.QTreeWidgetItem(['old'])
        self.dataTree.setHeaderLabels(['Data'])
        self.dataTree.insertTopLevelItems(0,[self.live_item,self.scans_item])
        self.central.addWidget(self.dataTree)

        self.graph = MyGraph('data_viewer')
        self.central.addWidget(self.graph)

        self.setGeometry(200,100,1200,800)
        self.show()

    def change_mode(self,item):
        if item.text(0) in ['scan','stream']:
            self.live_viewing = True
            self.mode = item.text(0)
            self.data_server.add_request(('change_mode',{'mode':self.mode}))
        else:
            self.live_viewing = False
            self.scan = int(item.text(0).strip('Scan '))

    def stopIOLoop(self):
        self.looping = False

    def startIOLoop(self):
        while self.looping:
            asyncore.loop(count=1, timeout=0.01)
            time.sleep(0.03)

    def add_dataserver(self):
        try:
            self.data_server = Connector(name='R_to_DS',
                                         chan=dataserver_channel,
                                         callback=self.reply_cb,
                                         onCloseCallback=self.onCloseCallback,
                                         default_callback=self.default_cb)
        except Exception as e:
            print(e)

    def add_fileserver(self):
        try:
            self.file_server = Connector(name='R_to_FS',
                                         chan=fileServer_channel,
                                         callback=self.reply_cb,
                                         onCloseCallback=self.onCloseCallback,
                                         default_callback=self.default_fileserver_cb)
        except Exception as e:
            print(e)

    def reply_cb(self,message):
        if message['reply']['parameters']['status'][0] == 0:
            function = message['reply']['op']
            args = message['reply']['parameters']
            track = message['track']

            params = getattr(self, function)(track, args)

        else:
            print('DataViewer received fail message', message)

    def default_cb(self):
        if self.live_viewing:
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
            # file server time
            return 'data_format',{}

    def default_fileserver_cb(self):
        if self.live_viewing:
            # data server time
            return 'file_status',{}
        else:
            if not self.initialized:
                return 'data_format',{"scan_number":[self.scan]}
            else:
                return 'request_data',{'scan_number':[self.scan],
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

        if data == []:
            return

        self.graph.no_of_rows = params['no_of_rows']

        data_x = pd.DataFrame({'time':data[0],'x':data[1]})
        data_y = pd.DataFrame({'time':np.array(data[2])+np.random.rand(len(data[2]))*10**(-6),'y':data[3]})

        data = pd.concat([data_x,data_y])
        data.set_index(['time'],inplace=True)

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

    def file_status_reply(self,track,params):
        available_scans = params['available_scans']
        masses = params['masses']
        sorted_results = sorted(zip(available_scans,masses),key=lambda x:x[0])
        available_scans,masses = [[x[i] for x in sorted_results] for i in range(2)]
        if not available_scans == self.available_scans:
            self.available_scans = available_scans
            self.masses = masses
            self.update_scan_list_signal.emit()

    def request_data_reply(self,track,params):
        origin, track_id = track
        data = params['data']

        data_x = pd.DataFrame({'time':data[0],'x':data[1]})
        data_y = pd.DataFrame({'time':np.array(data[2])+10**(-6),'y':data[3]})

        data = pd.concat([data_x,data_y])
        data.set_index(['time'],inplace=True)

        self.graph.data = data

    def update_scan_list(self):
        for scan,mass in zip(self.available_scans,self.masses):
            scan = int(scan)
            mass = int(mass)
            if not scan in self.scan_children.keys():
                self.scan_children[scan] = QtGui.QTreeWidgetItem(['Scan '+str(scan)])
                if not scan == -1:
                    if not mass in self.mass_children.keys():
                        self.mass_children[mass] = QtGui.QTreeWidgetItem(['Mass '+str(mass)])
                        self.scans_item.insertChild(0,self.mass_children[mass])

                    self.mass_children[mass].insertChild(0,self.scan_children[scan])

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
