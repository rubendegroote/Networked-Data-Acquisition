from PyQt4 import QtCore,QtGui
import threading as th
import multiprocessing as mp
import time
import pickle
import asyncore

from scanner import ScannerWidget
from connect import ConnectionsWidget
from central import CentralDock
from connectiondialogs import Man_DS_ConnectionDialog
from connectionwidgets import ArtistConnections

from backend.DataServer import DataServer
from backend.Radio import Radio
from backend.Manager import Manager
from backend.connectors import Man_DS_Connection

class ManagerApp(QtGui.QMainWindow):
    def __init__(self):
        super(ManagerApp, self).__init__()
        self.looping = True
        self.hasMan = False
        self.hasDS = False
        t = th.Thread(target = self.startIOLoop).start()
        self.init_UI()

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update)
        self.timer.start(50)

        self.show()

    def connectToServers(self,message = ''):
        respons = Man_DS_ConnectionDialog.getInfo(parent=self,message=message)
        if respons[1]:
            self.addConnection(respons[0])

    def init_UI(self):
        self.central = QtGui.QWidget()
        layout = QtGui.QGridLayout(self.central)
        self.setCentralWidget(self.central)

        self.scanner = ScannerWidget()
        self.scanner.scanInfoSig.connect(self.startScan)
        self.scanner.stopScanSig.connect(self.stopScan)
        layout.addWidget(self.scanner,0,0,1,1)

        self.connWidget = ArtistConnections()
        self.connWidget.connectSig.connect(self.addArtist)
        self.connWidget.removeSig.connect(self.removeArtist)
        layout.addWidget(self.connWidget,1,0,1,1)

        self.serverButton = QtGui.QPushButton('Connect to Servers')
        self.serverButton.clicked.connect(lambda:self.connectToServers())
        layout.addWidget(self.serverButton,2,0,1,1)

        self.disable()

    def addConnection(self,data):
        try:
            self.Man_DS_Connection.man.handle_close()
            self.Man_DS_Connection.DS.handle_close()
        except:
            pass
        ManChan = data[0],int(data[1])
        DSChan = data[2],int(data[3])
        self.Man_DS_Connection = Man_DS_Connection(ManChan,DSChan,callBack=self.lostConn)
        if self.Man_DS_Connection.man and self.Man_DS_Connection.DS:
            self.enable()
            self.statusBar().showMessage('Connected to Manager and Data Server')

    def lostConn(self,server):
        self.statusBar().showMessage(server + ' connection fail')
        self.disable()

    def disable(self):
        self.scanner.setDisabled(True)
        self.connWidget.setDisabled(True)

    def enable(self):
        self.scanner.setEnabled(True)
        self.connWidget.setEnabled(True)

    def startIOLoop(self):
        while self.looping:
            asyncore.loop(count=1)
            time.sleep(0.1)

    def stopIOLoop(self):
        self.looping = False

    def startScan(self,scanInfo):
        self.Man_DS_Connection.instruct('Manager', ['Scan',scanInfo])

    def stopScan(self):
        self.Man_DS_Connection.instruct('Manager', ['Stop Scan'])

    def addArtist(self,info):
        sender,address = info
        self.Man_DS_Connection.instruct(sender,['Add Artist',address])

    def removeArtist(self,address):
        self.Man_DS_Connection.instruct('Both',['Remove Artist',address])

    def update(self):
        try:
            self.scanner.update(self.Man_DS_Connection.getScanInfo())
            self.connWidget.update(self.Man_DS_Connection.getArtistInfo())
            if self.scanner.state == 'START' and self.Man_DS_Connection.scanning():
                self.scanner.changeControl()
            elif self.scanner.state == 'STOP' and not self.Man_DS_Connection.scanning():
                self.scanner.changeControl()
        except AttributeError as e:
            pass

    def closeEvent(self,event):
        self.stopIOLoop()
        event.accept()
