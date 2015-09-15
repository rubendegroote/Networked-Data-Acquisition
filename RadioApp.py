from PyQt4 import QtCore,QtGui
import threading as th
import asyncore
import time
import pandas as pd

from scanner import ScannerWidget
from connect import ConnectionsWidget
from graph import MyGraph

from backend.connectors import Connector

dataserver_channel = ('127.0.0.1',5005)
fileServer_channel = ('127.0.0.1', 5006)

class RadioApp(QtGui.QMainWindow):
    update_scan_list_signal = QtCore.pyqtSignal()
    def __init__(self):
        super(RadioApp, self).__init__()
        self.first_time = True
        self.live_viewing = True
        self.mode = 'stream'
        self.scan_number = -1
        self.available_scans = []
        self.scan_children = {}

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
        self.scan_item = QtGui.QTreeWidgetItem(['old'])
        self.dataTree.setHeaderLabels(['Data'])
        self.dataTree.insertTopLevelItems(0,[self.live_item,self.scan_item])
        self.central.addWidget(self.dataTree)

        self.graph = MyGraph('data_viewer')
        self.central.addWidget(self.graph)

        self.setGeometry(200,100,1200,800)
        self.show()

    def change_mode(self,item):
        if item.text(0) in ['scan','stream']:
            self.live_viewing = True
        else:
            self.live_viewing = False

        self.mode = item.text(0)
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
            print('Radio received fail message', message)

    def default_cb(self):
        if self.live_viewing:
            # data server time!
            if self.first_time:
                self.first_time = False
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
            # file sesrver time
            return 'data_format',{}

    def default_fileserver_cb(self):
        if self.live_viewing:
            # data server time
            return 'file_status',{}
        else:
            # file server time!
            return 'file_status',{}

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
        data_y = pd.DataFrame({'time':data[2],'y':data[3]})

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
        if not available_scans == self.available_scans:
            self.available_scans = available_scans
            self.update_scan_list_signal.emit()

    def update_scan_list(self):
        print('here')
        print(self.available_scans)
        for scan in self.available_scans:
            scan = str(int(scan))
            if not scan in self.scan_children.keys():
                self.scan_children[scan] = QtGui.QTreeWidgetItem(['Scan '+scan])
                if not scan == '-1':
	                self.scan_item.insertChild(0,self.scan_children[scan])

    def data_format_reply(self,track,params):
        origin, track_id = track
        if not str(params['current_scan']) == '-1':
            self.scan_number = params['current_scan']
        self.graph.formats = params['data_format']
        self.graph.no_of_rows = {k:0 for k in self.graph.formats.keys()}

        self.graph.setXYOptions(self.graph.formats)

    def closeEvent(self,event):
        self.stopIOLoop()
        event.accept()
