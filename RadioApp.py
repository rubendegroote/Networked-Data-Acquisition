from PyQt4 import QtCore, QtGui
import threading as th
import asyncore
import time

from scanner import ScannerWidget
from connect import ConnectionsWidget
from central import CentralDock

from backend.DataServer import DataServer
from backend.Manager import Manager
from backend.Radio import RadioConnector


class RadioApp(QtGui.QMainWindow):

    def __init__(self):
        super(RadioApp, self).__init__()
        self.looping = True
        t = th.Thread(target=self.startIOLoop).start()

        self.init_UI()

    def init_UI(self):

        self.connectToolBar = QtGui.QToolBar('Connections')
        self.connectToolBar.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.addToolBar(self.connectToolBar)

        self.connectionsWidget = ConnectionsWidget()
        self.connectionsWidget.newConn.connect(self.addConnection)
        self.connectToolBar.addWidget(self.connectionsWidget)

        self.centralDock = CentralDock()
        self.centralDock.graphDocks[
            0].graph.dataRequested.connect(self.changeDataType)
        self.setCentralWidget(self.centralDock)

        self.show()

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.plot)
        self.timer.start(50)

    def stopIOLoop(self):
        self.looping = False

    def startIOLoop(self):
        while self.looping:
            asyncore.loop(count=1, timeout=0.01)
            time.sleep(0.03)

    def changeDataType(self, value):
        if value == 'Per Scan':
            value = True
        else:
            value = False
        self.radio.perScan = value

    def addConnection(self, data):
        self.radio = RadioConnector(chan=(data[0], int(data[1])),
                                    callback=None,
                                    onCloseCallback=self.connLost)

    def connLost(self):
        pass

    def plot(self):
        try:
            for g in self.centralDock.graphDocks:
                g.graph.setXYOptions(list(self.radio.format))
                g.graph.plot(self.radio.data)
                self.radio.xy = [g.graph.xkey, g.graph.ykey]
        except AttributeError as e:
            pass

    def closeEvent(self, event):
        self.stopIOLoop()
        event.accept()
