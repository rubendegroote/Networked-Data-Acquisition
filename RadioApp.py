from PyQt4 import QtCore,QtGui
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
        self.centralDock.graphDocks[0].graph.dataRequested.connect(self.changeDataType)
        self.centralDock.graphDocks[0].graph.scanRequested.connect(self.changeCurrentScan)
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
        self.radio = RadioConnector(chan=(data[0], int(data[1])),
                                    callback=None,
                                    onCloseCallback=self.connLost)
        self.centralDock.graphDocks[0].graph.memoryClear.connect(self.radio.clearMemory)
        self.centralDock.graphDocks[0].graph.memoryChanged.connect(self.radio.changeMemory)
        self.connectToolBar.setHidden(True)

    def connLost(self):
        pass

    def plot(self):
        try:
            for g in self.centralDock.graphDocks:
                if g.graph.xkey == 'time':
                    selected = [g.graph.ykey]
                elif g.graph.ykey == 'time':
                    selected = [g.graph.xkey]
                else:
                    selected = [g.graph.xkey, g.graph.ykey]
                g.graph.setXYOptions(list(self.radio.format))
                if all([s in self.radio.data.columns for s in selected]):
                    # print(self.radio.data[selected])
                    g.graph.plot(self.radio.data[selected])
                self.radio.xy = list(self.radio.format)

                try:
                    self.statusBar().showMessage('Laser Wavelength: '+ str(self.radio.data['laser: wavenumber'][-1]) +  ' cm-1')
                except:
                    pass

        except AttributeError as e:
            pass

    def closeEvent(self,event):
        self.stopIOLoop()
        event.accept()
