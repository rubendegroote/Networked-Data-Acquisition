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
    messageUpdateSignal = QtCore.pyqtSignal(dict)
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
        self.messageUpdateSignal.connect(self.updateMessages)

        self.show()

    def connectToServers(self):
        respons = Man_DS_ConnectionDialog.getInfo(parent=self)
        if respons[1]:
            self.addConnection(respons[0])

    def init_UI(self):
        self.central = QtGui.QWidget()
        layout = QtGui.QGridLayout(self.central)
        self.setCentralWidget(self.central)

        self.scanner = ScannerWidget()
        self.scanner.scanInfoSig.connect(self.start_scan)
        self.scanner.stopScanSig.connect(self.stop_scan)
        self.scanner.setPointSig.connect(self.go_to_setpoint)
        self.scanner.toggleConnectionsSig.connect(self.toggleConnectionsUI)
        layout.addWidget(self.scanner, 0, 0, 1, 1)

        self.connWidget = ArtistConnections()
        self.connWidget.connectSig.connect(self.add_artist)
        self.connWidget.removeSig.connect(self.remove_artist)
        self.connWidget.removeAllSig.connect(self.remove_all_artists)
        layout.addWidget(self.connWidget, 1, 0, 1, 1)

        self.serverConnectButton = QtGui.QPushButton('Connect to Servers')
        self.serverConnectButton.clicked.connect(self.connectToServers)
        layout.addWidget(self.serverConnectButton, 2, 0, 1, 1)

        self.messageLog = QtGui.QPlainTextEdit()
        self.messageLog.setMinimumWidth(400)
        layout.addWidget(self.messageLog,0,1,3,1)

        self.disable()

    def updateUI(self,*args):
        target,info_dict = args[0]
        params,track = info_dict['args'],info_dict['track']
        target(track,params)

    def addConnection(self, data):
        ManChan = data[0], int(data[1])
        DSChan = data[2], int(data[3])
        self.Man_DS_Connector = Man_DS_Connector(ManChan, DSChan,
                                 callback=self.reply_cb,
                                 default_cb=self.default_cb,
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

            self.serverConnectButton.setDisabled(True)
        else:
            self.statusBar().showMessage('Connection failure')

    def reply_cb(self, message):
        if message['reply']['parameters']['status'][0] == 0:
            function = message['reply']['op']
            args = message['reply']['parameters']
            track = message['track']
            status_updates = message['status_updates']
            for status_update in status_updates:
                self.messageUpdateSignal.emit({'track':track,'args':status_update})
            params = getattr(self, function)(track, args)

        else:
            exception = message['reply']['parameters']['exception']
            self.messageUpdateSignal.emit(
                {'track':track,'args':[[1],"Received status fail in reply\n:{}".format(exception)]})

    def default_cb(self):
        return 'status',{}

    def lostConn(self, connector):
        print('lostConn')
        self.statusBar().showMessage(
            connector.acceptorName + ' connection failure')
        self.serverConnectButton.setEnabled(True)
        self.disable()

    def disable(self):
        self.scanner.setDisabled(True)
        self.connWidget.setDisabled(True)

    def enable(self):
        self.scanner.setEnabled(True)
        self.connWidget.setEnabled(True)

    def toggleConnectionsUI(self,boolean):
        if boolean:
            self.connWidget.setEnabled(True)
            self.serverConnectButton.setEnabled(True)
        else:
            self.connWidget.setDisabled(True)
            self.serverConnectButton.setDisabled(True)

    def startIOLoop(self):
        while self.looping:
            asyncore.loop(count=1)
            time.sleep(0.1)

    def stopIOLoop(self):
        self.looping = False

    def start_scan(self, scanInfo):
        self.Man_DS_Connector.instruct('Manager', ('start_scan', scanInfo))

    def go_to_setpoint(self, setpointInfo):
        self.Man_DS_Connector.instruct('Manager', ('go_to_setpoint', setpointInfo))

    def stop_scan(self):
        self.Man_DS_Connector.instruct('Manager', ('stop_scan',{}))

    def add_artist(self, info):
        receiver, address = info
        op,params = 'add_connector',{'address': address}
        self.Man_DS_Connector.instruct(receiver, (op,params))

    def remove_artist(self, address):
        op,params = 'remove_connector', {'address': address}
        self.Man_DS_Connector.instruct('Both',(op,params))

    def remove_all_artists(self):
        op,params = 'remove_all_connectors', {}
        self.Man_DS_Connector.instruct('Both',(op,params))

    # def showResumeDialog(self, data):
    #     smin, smax, sl, curpos, tPerStep, name = data
    #     resuming = QtGui.QMessageBox.question(None, 'Resume scan?',
    #                                           'An interrupted scan was found:\nScanning %s, %f to %f V, %f steps, on step %f, %f s per step\nResume this scan?' % (name,
    #                                     float(smin),float(smax),float(sl),float(curpos),float(tPerStep)),QtGui.QMessageBox.Yes | QtGui.QMessageBox.No, QtGui.QMessageBox.No)
    #     if resuming == QtGui.QMessageBox.Yes:
    #         self.Man_DS_Connector.instruct('Manager', ['Resume Scan'])

    def closeEvent(self, event):
        self.stopIOLoop()
        event.accept()
            
    def status_reply(self, track, params):
        origin, track_id = track[-1]
        if origin == 'Manager':
            self.updateSignal.emit((self.scanner.update,
                                    {'track':track,
                                    'args':params}))

        self.updateSignal.emit((self.connWidget.update,
                                       {'track':track,
                                       'args':params['connector_info']}))

    def start_scan_reply(self,track,params):
        origin,track_id = track[-1]
        self.messageUpdateSignal.emit(
            {'track':track,'args':[[0],"Start scan instruction received"]})
        
    def stop_scan_reply(self,track,params):
        origin,track_id = track[-1]
        self.messageUpdateSignal.emit(
            {'track':track,'args':[[0],"Stop scan instruction received"]})

    def add_connector_reply(self,track,params):
        origin,track_id = track[-1]
        self.messageUpdateSignal.emit(
            {'track':track,'args':[[0],"Add connector instruction received"]})
        
    def remove_connector_reply(self,track,params):
        origin,track_id = track[-1]
        self.messageUpdateSignal.emit(
            {'track':track,'args':[[0],"Remove connector instruction received"]})
        
    def remove_all_connectors_reply(self,track,params):
        origin,track_id = track[-1]
        self.messageUpdateSignal.emit(
            {'track':track,'args':[[0],"Remove all connectors instruction received"]})

    def updateMessages(self,info):
        track,message = info['track'],info['args']
        text = '{}: {} reports {}'.format(track[-1][1],track[-1][0],message[1])
        if message[0][0] == 0:
            self.messageLog.appendPlainText(text)        
        else:
            error_dialog = QtGui.QErrorMessage(self)
            error_dialog.showMessage(text)
            error_dialog.exec_()

class Man_DS_Connector():

    def __init__(self,ManChan,DSChan,callback,
            onCloseCallback,default_cb):
    
        try:
            self.DS = Connector(chan=DSChan,name='MGUI_to_DS',
                          callback=callback,
                          default_callback = default_cb,)
            # by only adding this closeCallback now, it is not triggerd
            # if the connection fails
            # prevents an Exception in the GUI
            self.DS.onCloseCallback = onCloseCallback
        except Exception as e:
            self.DS_error = e
            print('Error connecting to dataserver \n'+ str(e))
            self.DS = None
        try:    
            self.man = Connector(chan=ManChan,name='MGui_to_M',
                          callback=callback,
                          default_callback=default_cb)
            # same comment as for the DS closeCallback
            self.man.onCloseCallback = onCloseCallback

        except Exception as e:
            self.man_error = e
            print('Error connecting to manager \n'+ str(e))
            self.man = None

    def instruct(self, receiver, instr):
        if receiver == 'Manager':
            self.man.add_request(instr)
        elif receiver == 'Data Server':
            self.DS.add_request(instr)
        elif receiver == 'Both':
            self.man.add_request(instr)
            self.DS.add_request(instr)