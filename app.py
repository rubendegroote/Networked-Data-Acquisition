from PyQt4 import QtCore, QtGui
import asyncore
import time

from scanner import ScannerWidget
from connect import ConnectionsWidget
from central import CentralDock

from backend.DataViewer import DataViewer
from backend.Controller import Controller


class Application(QtGui.QMainWindow):

    def __init__(self):
        super(Application, self).__init__()
        self.init_UI()

    def init_UI(self):

        self.connectToolBar = QtGui.QToolBar('Connections')
        self.connectToolBar.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.addToolBar(self.connectToolBar)

        self.connectionsWidget = ConnectionsWidget()
        self.connectionsWidget.newConn.connect(self.addConnection)
        self.connectToolBar.addWidget(self.connectionsWidget)

        self.scanToolBar = QtGui.QToolBar('Connections')
        self.scanToolBar.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.addToolBar(self.scanToolBar)
        self.scanner = ScannerWidget()
        self.scanner.scanInfo.connect(self.startScan)
        self.scanToolBar.addWidget(self.scanner)

        self.centralDock = CentralDock()
        self.setCentralWidget(self.centralDock)

        self.show()

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.plot)
        self.timer.start(50)

        # self.looping = True
        # t = th.Thread(target = self.startIOLoop).start()

    def stopIOLoop(self):
        self.looping = False

    def startIOLoop(self):
        while self.looping:
            asyncore.loop(count=1)
            time.sleep(0.01)

    def addConnection(self, data):
        if data[0] == 'DataViewer':
            self.DataViewer = DataViewer(IP=data[1], PORT=int(data[2]))
        elif data[0] == 'FileServer':
            self.fileServer = FileServer(devices=[(data[1], data[2])],
                                         save=False, remember=True)
        elif data[0] == 'Controller':
            self.controller = Controller(devices=[(data[1], data[2])])

    def plot(self):
        try:
            for g in self.centralDock.graphDocks:
                g.graph.setXYOptions(list(self.DataViewer.format))
                g.graph.plot(self.DataViewer.data)
                self.DataViewer.xy = [g.graph.xkey, g.graph.ykey]
        except AttributeError as e:
            pass

    def startScan(self, scanInfo):
        self.controller.scan(scanInfo)

    def closeEvent(self, event):
        self.stopIOLoop()
        event.accept()
