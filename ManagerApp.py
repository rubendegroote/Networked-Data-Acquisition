from PyQt4 import QtCore,QtGui
import threading as th
import asyncore
import time

from scanner import ScannerWidget
from connect import ConnectionsWidget
from central import CentralDock

from backend.DataServer import DataServer
from backend.Radio import Radio
from backend.Manager import Manager


class ManagerApp(QtGui.QMainWindow):
    def __init__(self):
        super(ManagerApp, self).__init__()
        self.manager = Manager()
        self.looping = True
        t = th.Thread(target = self.startIOLoop).start()

        self.init_UI()

    def init_UI(self):

        self.connectToolBar = QtGui.QToolBar('Connections')
        self.connectToolBar.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.addToolBar(self.connectToolBar)

        self.connectionsWidget = ConnectionsWidget()
        self.connectionsWidget.newConn.connect(self.addConnection)
        self.connectToolBar.addWidget(self.connectionsWidget)

        self.scanner = ScannerWidget()
        self.scanner.scanInfo.connect(self.startScan)
        self.setCentralWidget(self.scanner)

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update)
        self.timer.start(50)

        self.show()

    def addConnection(self,data):
        self.manager.addInstructor(data)
        time.sleep(0.1)
        self.scanner.setParCombo(self.manager.format)

    def startIOLoop(self):
        while self.looping:
            asyncore.loop(count=1)
            time.sleep(0.01)

    def stopIOLoop(self):
        self.looping = False

    def startScan(self,scanInfo):
        self.manager.scan(scanInfo)

    def update(self):
        try:
            self.scanner.updateProgress(self.manager.progress)
            if self.scanner.state == 'START' and self.manager.scanning:
                self.scanner.changeControl()
            elif self.scanner.state == 'STOP' and not self.manager.scanning:
                self.scanner.changeControl()
        except Exception as e:
            print(e)

    def closeEvent(self,event):
        self.stopIOLoop()
        event.accept()