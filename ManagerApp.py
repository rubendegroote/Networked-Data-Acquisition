import asyncore
import pickle
import threading as th
import time

from PyQt4 import QtCore, QtGui
from backend.connectors import Connector
import configparser
from connectiondialogs import Man_DS_ConnectionDialog
from connectionwidgets import ArtistConnections
from scanner import ScannerWidget


class ResumeScanSignal(QtCore.QObject):

    resumescan = QtCore.pyqtSignal(tuple)


class ManagerApp(QtGui.QMainWindow):
    updateSignal = QtCore.pyqtSignal(tuple)
    def __init__(self):
        super(ManagerApp, self).__init__()
        self.looping = True
        self.hasMan = False
        self.hasDS = False
        t = th.Thread(target=self.startIOLoop).start()
        self.init_UI()

        # self.timer = QtCore.QTimer()
        # self.timer.timeout.connect(self.update)
        # self.timer.start(50)
        self.updateSignal.connect(self.updateUI)

        self.show()

    def connectToServers(self, message=''):
        respons = Man_DS_ConnectionDialog.getInfo(parent=self, message=message)
        if respons[1]:
            self.addConnection(respons[0])

    def init_UI(self):
        self.central = QtGui.QWidget()
        layout = QtGui.QGridLayout(self.central)
        self.setCentralWidget(self.central)

        self.scanner = ScannerWidget()
        self.scanner.scanInfoSig.connect(self.startScan)
        self.scanner.stopScanSig.connect(self.stopScan)
        self.scanner.setPointSig.connect(self.setPoint)
        layout.addWidget(self.scanner, 0, 0, 1, 1)

        self.connWidget = ArtistConnections()
        self.connWidget.connectSig.connect(self.addArtist)
        self.connWidget.removeSig.connect(self.removeArtist)
        # self.connWidget.removeAll.connect(self.removeAll)
        layout.addWidget(self.connWidget, 1, 0, 1, 1)

        self.dispatchButton = QtGui.QPushButton('Connect to Servers')
        self.dispatchButton.clicked.connect(lambda: self.connectToServers())
        layout.addWidget(self.dispatchButton, 2, 0, 1, 1)

        self.disable()

    def updateUI(self,*args):
        target,info_dict = args[0]
        params,origin = info_dict['args'],info_dict['origin']
        target(origin,params)

    def addConnection(self, data):
        # try:
        #     self.Man_DS_Connector.man.handle_close()
        #     self.Man_DS_Connector.DS.handle_close()
        # except:
        #     pass
        ManChan = data[0], int(data[1])
        DSChan = data[2], int(data[3])
        self.Man_DS_Connector = Man_DS_Connector(ManChan, DSChan,
                                 callback=self.reply_cb,
                                 onCloseCallback = self.lostConn)

        if self.Man_DS_Connector.man and self.Man_DS_Connector.DS:
            self.enable()
            self.statusBar().showMessage(
                'Connected to Manager and Data Server')
            config = configparser.ConfigParser()
            config['manager'] = {'address': data[0], 'port': int(data[1])}
            config['data server'] = {'address': data[2], 'port': int(data[3])}
            with open('ManagerDSConnections.ini', 'w') as configfile:
                config.write(configfile)

            self.dispatchButton.setDisabled(True)
        else:
            self.statusBar().showMessage('Connection failure')

    def lostConn(self, connector):
        print('lostConn')
        self.statusBar().showMessage(
            connector.acceptorName + ' connection failure')
        self.dispatchButton.setEnabled(True)
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

    def startScan(self, scanInfo):
        self.connWidget.setDisabled(True)
        self.dispatchButton.setDisabled(True)
        self.Man_DS_Connector.instruct('Manager', ['Scan', scanInfo])

    def setPoint(self, setpointInfo):
        self.Man_DS_Connector.instruct('Manager', ['Setpoint', setpointInfo])

    def stopScan(self):
        self.Man_DS_Connector.instruct('Manager', ['Stop Scan'])

    def addArtist(self, info):
        receiver, address = info
        message = {'op': 'add_connector', 'parameters': {'address': address}}
        self.Man_DS_Connector.instruct(receiver, message)

    def removeArtist(self, address):
        self.Man_DS_Connector.instruct('Both', ['Remove Artist', address])

    def showResumeDialog(self, data):
        smin, smax, sl, curpos, tPerStep, name = data
        resuming = QtGui.QMessageBox.question(None, 'Resume scan?',
                                              'An interrupted scan was found:\nScanning %s, %f to %f V, %f steps, on step %f, %f s per step\nResume this scan?' % (name,
                                        float(smin),float(smax),float(sl),float(curpos),float(tPerStep)),QtGui.QMessageBox.Yes | QtGui.QMessageBox.No, QtGui.QMessageBox.No)
        if resuming == QtGui.QMessageBox.Yes:
            self.Man_DS_Connector.instruct('Manager', ['Resume Scan'])

    def closeEvent(self, event):
        self.stopIOLoop()
        event.accept()

    def reply_cb(self, message):
        if message['reply']['parameters']['status'][0] == 0:
            function = message['reply']['op']
            args = message['reply']['parameters']
            origin = message['track'][-1][0]

            params = getattr(self, function)(origin, args)

        else:
            print('ManagerApp received fail message', message)
            
    def status_reply(self, origin, params):
        if origin == 'Manager':
            self.updateSignal.emit((self.scanner.update,
                                    {'origin':origin,
                                    'args':params}))

            scanning = params['scanning']
            if self.scanner.state == 'START' and scanning:
                self.scanner.changeControl()
            elif self.scanner.state == 'STOP' and not scanning:
                self.dispatchButton.setEnabled(True)
                self.connWidget.setEnabled(True)
                self.scanner.changeControl()

        self.updateSignal.emit((self.connWidget.update,
                                       {'origin':origin,
                                       'args':params['connector_info']}))

    def add_connector_reply(self, origin, params):
        pass


class Man_DS_Connector():

    def __init__(self, ManChan, DSChan, callback,onCloseCallback):
    
        try:
            self.DS = Connector(DSChan,
                          callback=callback,
                          name='MGui_to_DS')
            # by only adding this closeCallback now, it is not triggerd
            # if the connection fails
            # prevents an Exception in the GUI
            self.DS.onCloseCallback = onCloseCallback
        except:
            self.DS = None
        try:    
            self.man = Connector(ManChan,
                          callback=callback,
                          onCloseCallback=onCloseCallback,
                          name='MGui_to_M')
            # same comment as for the DS closeCallback
            self.man.onCloseCallback = onCloseCallback

        except:
            self.man = None

    def instruct(self, receiver, instr):
        if receiver == 'Manager':
            self.man.add_request(instr)
        elif receiver == 'Data Server':
            self.DS.add_request(instr)
        elif receiver == 'Both':
            self.man.add_request(instr)
            self.DS.add_request(instr)