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

    def __init__(self):
        super(ManagerApp, self).__init__()
        self.looping = True
        self.hasMan = False
        self.hasDS = False
        t = th.Thread(target=self.startIOLoop).start()
        self.init_UI()

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update)
        self.timer.start(50)

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

        self.serverButton = QtGui.QPushButton('Connect to Servers')
        self.serverButton.clicked.connect(lambda: self.connectToServers())
        layout.addWidget(self.serverButton, 2, 0, 1, 1)

        self.disable()

    def addConnection(self, data):
        try:
            self.Man_DS_Connector.man.handle_close()
            self.Man_DS_Connector.DS.handle_close()
        except:
            pass
        ManChan = data[0], int(data[1])
        DSChan = data[2], int(data[3])
        self.Man_DS_Connector = Man_DS_Connector(ManChan, DSChan,
                                                 callBack=self.lostConn,
                                                 resumeScanCallback=self.showResumeDialog)
        if self.Man_DS_Connector.man and self.Man_DS_Connector.DS:
            self.enable()
            self.statusBar().showMessage(
                'Connected to Manager and Data Server')
            config = configparser.ConfigParser()
            config['manager'] = {'address': data[0], 'port': int(data[1])}
            config['data server'] = {'address': data[2], 'port': int(data[3])}
            with open('ManagerDSConnections.ini', 'w') as configfile:
                config.write(configfile)

    def lostConn(self, server):
        print(server)
        self.statusBar().showMessage(server + ' connection fail')
        self.serverButton.setEnabled(True)
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
        self.serverButton.setDisabled(True)
        self.Man_DS_Connector.instruct('Manager', ['Scan', scanInfo])

    def setPoint(self, setpointInfo):
        print(setpointInfo)
        self.Man_DS_Connector.instruct('Manager', ['Setpoint', setpointInfo])

    def stopScan(self):
        self.Man_DS_Connector.instruct('Manager', ['Stop Scan'])

    def addArtist(self, info):
        sender, address = info
        self.Man_DS_Connector.instruct(sender, ['Add Artist', address])

    def removeArtist(self, address):
        self.Man_DS_Connector.instruct('Both', ['Remove Artist', address])

    # def removeAll(self):
    #     self.Man_DS_Connector.instruct('Both', ['Remove All Artists'])

    def update(self):
        try:
            self.scanner.update(self.Man_DS_Connector.getScanInfo())
            self.connWidget.update(self.Man_DS_Connector.getArtistInfo())
            if self.scanner.state == 'START' and self.Man_DS_Connector.scanning():
                self.scanner.changeControl()
            elif self.scanner.state == 'STOP' and not self.Man_DS_Connector.scanning():
                self.serverButton.setEnabled(True)
                self.connWidget.setEnabled(True)
                self.scanner.changeControl()
        except AttributeError as e:
            pass

    def showResumeDialog(self, data):
        smin, smax, sl, curpos, tPerStep, name = data
        resuming = QtGui.QMessageBox.question(None, 'Resume scan?',
                                              'An interrupted scan was found:\nScanning %s, %f to %f V, %f steps, on step %f, %f s per step\nResume this scan?' % (name,
                                                                                                                                                                   float(
                                                                                                                                                                       smin),
                                                                                                                                                                   float(
                                                                                                                                                                       smax),
                                                                                                                                                                   float(
                                                                                                                                                                       sl),
                                                                                                                                                                   float(
                                                                                                                                                                       curpos),
                                                                                                                                                                   float(tPerStep)),
                                              QtGui.QMessageBox.Yes | QtGui.QMessageBox.No, QtGui.QMessageBox.No)
        if resuming == QtGui.QMessageBox.Yes:
            self.Man_DS_Connector.instruct('Manager', ['Resume Scan'])

    def closeEvent(self, event):
        self.stopIOLoop()
        event.accept()


class Man_DS_Connector():

    def __init__(self, ManChan, DSChan, callBack, resumeScanCallback):
        self.AppCallBack = callBack
        try:
            self.man = ManagerConnector(ManChan,
                                        callback=None,
                                        onCloseCallback=self.onClosedCallback,
                                        resumeScanCallback=resumeScanCallback)
        except Exception as e:
            print(e)
            self.man = None

        try:
            self.DS = DataServerConnector(DSChan,
                                          callback=None,
                                          onCloseCallback=self.onClosedCallback)
        except Exception as e:
            print(e)
            self.DS = None

    def getArtistInfo(self):
        retDict = {}
        keys = set(self.DS.artists.keys()).union(set(self.man.artists.keys()))
        for key in keys:
            if key in self.man.artists.keys():
                if key in self.DS.artists.keys():
                    retDict[key] = (self.man.artists[key][0],
                                    self.DS.artists[key][0],
                                    self.man.artists[key][1:])
                else:
                    retDict[key] = (self.man.artists[key][0],
                                    False,
                                    self.man.artists[key][1:])
            else:
                retDict[key] = False, self.DS.artists[
                    key][0], self.DS.artists[key][1:]

        return retDict

    def getScanInfo(self):
        return self.man.scanNo, self.man.format, self.man.progress, self.man.artists

    def scanning(self):
        return self.man.scanning

    def instruct(self, t, instr):
        if t == 'Manager':
            self.man.commQ.put(instr)
        elif t == 'Data Server':
            self.DS.commQ.put(instr)
        elif t == 'Both':
            self.man.commQ.put(instr)
            self.DS.commQ.put(instr)

    def onClosedCallback(self, server):
        print(server, server.type)
        # perhaps use this to change some settings or whatnot
        self.AppCallBack(server.type)


class ManagerConnector(Connector):

    def __init__(self, chan, callback, onCloseCallback, resumeScanCallback=None):
        super(ManagerConnector, self).__init__(
            chan, callback, onCloseCallback, t='MGui_to_M')
        self.resumeSignal = ResumeScanSignal()
        self.resumeSignal.resumescan.connect(resumeScanCallback)
        self.scanNo = -1
        self.progress = 0
        self.scanning = False
        self.format = {}
        self.artists = {}

        self.send_next()

    def found_terminator(self):
        buff = self.buff
        self.buff = b''
        data = pickle.loads(buff)
        if type(data) == list:
            message, data = data
            if message == 'infomessage':
                self.artists, info = data
                self.scanNo, self.scanning, self.progress, self.format = info
            elif message == 'resumemessage':
                smin, smax, sl, curpos, tPerStep, name = data
                self.resumeSignal.resumescan.emit(
                    (smin, smax, sl, curpos, tPerStep, name))
            else:
                pass

        try:
            info = self.commQ.get_nowait()
            self.push(pickle.dumps(info))
            self.push('END_MESSAGE'.encode('UTF-8'))
        except:
            self.send_next()


class DataServerConnector(Connector):

    def __init__(self, chan, callback, onCloseCallback):
        super(DataServerConnector, self).__init__(
            chan, callback, onCloseCallback, t='MGui_to_DS')

        self.artists = {}

        self.send_next()

    def found_terminator(self):
        buff = self.buff
        self.buff = b''
        data = pickle.loads(buff)
        if type(data) == tuple:
            self.artists, bitrates = data
        try:
            info = self.commQ.get_nowait()
            self.push(pickle.dumps(info))
            self.push('END_MESSAGE'.encode('UTF-8'))
        except:
            self.send_next()
