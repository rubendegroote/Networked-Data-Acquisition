from PyQt4 import QtCore,QtGui
import threading as th
import asyncore
import time
import pandas as pd

from scanner import ScannerWidget
from connect import ConnectionsWidget
from graph import MyGraph

from backend.connectors import Connector

class RadioApp(QtGui.QMainWindow):

    def __init__(self):
        super(RadioApp, self).__init__()
        self.first_time = True

        self.looping = True
        t = th.Thread(target=self.startIOLoop).start()

        self.init_UI()

        time.sleep(0.1)
        self.addConnection(['127.0.0.1',5005])

    def init_UI(self):
        self.graph = MyGraph('central')
        self.setCentralWidget(self.graph)

        self.setGeometry(200,100,1200,800)
        self.show()

    def stopIOLoop(self):
        self.looping = False

    def startIOLoop(self):
        while self.looping:
            asyncore.loop(count=1, timeout=0.01)
            time.sleep(0.03)

    def changeDataType(self, value):
        if value == 'Give Scan':
            value = True
        else:
            value = False
        self.radio.giveScan = value

    def changeCurrentScan(self, value):
        if value == 'Current Scan':
            value = True
        else:
            value = False
        self.radio.currentScan = value

    def addConnection(self, data):
        self.radio = Connector(chan=(data[0], int(data[1])),name='Radio',
                    callback=self.reply_cb,
                    onCloseCallback=self.lostConn,
                    default_callback=self.default_cb)

    def reply_cb(self,message):
        if message['reply']['parameters']['status'][0] == 0:
            function = message['reply']['op']
            args = message['reply']['parameters']
            track = message['track']

            params = getattr(self, function)(track, args)

        else:
            print('Radio received fail message', message)

    def default_cb(self):
        if self.first_time:
            self.first_time = False
            return 'data_format',{}
        elif self.graph.reset:
            self.graph.reset_data()
            return 'data',{'no_of_rows':self.graph.no_of_rows,
                           'x':self.graph.x_key,
                           'y':self.graph.y_key}

        else:
            return 'data',{'no_of_rows':self.graph.no_of_rows,
                           'x':self.graph.x_key,
                           'y':self.graph.y_key}

    def lostConn(self,connector):
        print('lost connection')

    def data_reply(self,track,params):
        origin, track_id = track
        data = params['data']
        if data == []:
            pass

        else:
            self.graph.no_of_rows = params['no_of_rows']

            data_x = pd.DataFrame({'time':data[0],'x':data[1]})
            data_y = pd.DataFrame({'time':data[2],'y':data[3]})

            data = pd.concat([data_x,data_y])
            data.set_index(['time'],inplace=True)

            self.graph.data=self.graph.data.append(data)

    def data_format_reply(self,track,params):
        origin, track_id = track
        self.graph.formats = params['data_format']
        self.graph.no_of_rows = {k:0 for k in self.graph.formats.keys()}

        self.graph.setXYOptions(self.graph.formats)

    def closeEvent(self,event):
        self.stopIOLoop()
        event.accept()
