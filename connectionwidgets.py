from PyQt4 import QtCore, QtGui
import configparser
from connectiondialogs import ConnectionDialog
import os

CONFIG_PATH = os.getcwd() + "\\config.ini"

class DeviceConnections(QtGui.QWidget):
    connectSig = QtCore.pyqtSignal(tuple)
    removeSig = QtCore.pyqtSignal(tuple)
    removeAllSig = QtCore.pyqtSignal(bool)
    
    ### get configuration details
    config_parser = configparser.ConfigParser()
    config_parser.read(CONFIG_PATH)
    def __init__(self, parent=None):
        super(DeviceConnections, self).__init__(parent)
        ports = self.config_parser['ports']
        IPs = self.config_parser['ports']
        self.address = {k:(ports[k],IPs[k]) \
                   for k in ports.keys() if not k in ('server','controller')}

        self.deviceWidgets = {}
        self.l = 0
        self.layout = QtGui.QGridLayout(self)

        self.deviceSelection = QtGui.QComboBox()
        self.deviceSelection.addItems(sorted(list(self.address.keys())))
        self.deviceSelection.setCurrentIndex(0)
        self.layout.addWidget(self.deviceSelection, 100, 0, 1, 1)

        self.addDeviceButton = QtGui.QPushButton('Add Device')
        self.addDeviceButton.clicked.connect(self.addConnection)
        self.layout.addWidget(self.addDeviceButton, 100, 1, 1, 1)

        self.ManDevices = []
        self.DSDevices = []

    def addConnection(self):
        selection = self.deviceSelection.currentText()
        respons = self.address[selection]
        self.connectSig.emit(('Both', selection, respons))

    def addDeviceWidget(self, name='',IP,PORT):
        self.deviceWidgets[name] = DeviceWidget(self, name, IP, PORT)
        self.deviceWidgets[name].removeSig.connect(self.remove)
        self.deviceWidgets[name].reconnectSig.connect(self.reconnect)
        self.layout.addWidget(self.deviceWidgets[name], self.l, 0, 1, 2)
        
        self.l += 1

    def remove(self, connWidget):
        self.removeSig.emit((connWidget.IP, connWidget.PORT))

    def remove_all_devices(self):
        for name in self.deviceWidgets:
            self.removeAllSig.emit(True)

    def reconnect(self, info):
        self.connectSig.emit(info)

    def update(self,track,params):
        origin, track_id = track[-1]
        # update list of existing connections
        if origin == 'Controller':
            self.ManDevices = params.keys()
        elif origin == 'DataServer':
            self.DSDevices = params.keys()

        for key,val in params.items():
            # if there is a new device, create a new widget
            if key not in self.deviceWidgets.keys():
                self.addDeviceWidget(name=key,
                    IP=str(val[1]), PORT=str(val[2]))
            # if it is not new: check if origin is still connected 
            # and update widget accordingly
            else:
                if not val[0]:
                    self.deviceWidgets[key].set_disconnected(origin)

        # update the status of the widget, delete if needed
        toDelete = []
        for key,val in self.deviceWidgets.items():
            if key not in self.ManDevices and key not in self.DSDevices:
                toDelete.append(key)
            else:
                if key not in params.keys():
                    val.set_disconnected(origin)
                elif params[key][0]:
                    val.set_connected(origin)

        for key in toDelete:
            try:
                self.deviceWidgets[key].close()
                del self.deviceWidgets[key]
            except KeyError as e:
                # raised when the widget has already been removed 
                # due to an earlier status update
                pass

    def updateData(self,track,params):
        for key,val in self.deviceWidgets.items():
            try:
                val.rowLabel.setText('data rows: ' + str(params['no_of_rows'][key]))
            except KeyError:
                pass

    def updateScan(self,track,params):
        for key,val in self.deviceWidgets.items():
            try:
                val.scanLabel.setText('scan: ' + str(params['scan_numbers'][key]))
            except KeyError:
                pass

class DeviceWidget(QtGui.QWidget):
    removeSig = QtCore.pyqtSignal(object)
    reconnectSig = QtCore.pyqtSignal(object)

    def __init__(self, parent=None, name='',IP,PORT):
        super(DeviceWidget, self).__init__(parent)
        self.IP = IP
        self.PORT = PORT
        self.name = name

        self.not_ok = "QLabel { background-color: red }"
        self.ok = "QLabel { background-color: green }"

        self.layout = QtGui.QGridLayout(self)

        self.label = QtGui.QLabel(' ' + str(name))
        self.layout.addWidget(self.label, 0, 0, 1, 1)

        self.ManLabel = QtGui.QLabel('Controller')
        self.ManLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.ManLabel.setMinimumWidth(50)
        self.ManLabel.setMinimumHeight(25)
        self.ManLabel.setStyleSheet(self.not_ok)
        self.layout.addWidget(self.ManLabel, 0, 1, 1, 1)

        self.DSLabel = QtGui.QLabel('Data Server')
        self.DSLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.DSLabel.setMinimumWidth(50)
        self.DSLabel.setMinimumHeight(25)
        self.DSLabel.setStyleSheet(self.not_ok)
        self.layout.addWidget(self.DSLabel, 0, 2, 1, 1)

        self.channel = QtGui.QLabel(self, text='IP: ' + IP)
        self.layout.addWidget(self.channel, 0, 3, 1, 1)

        self.portlabel = QtGui.QLabel(self, text='Port: ' + PORT)
        self.layout.addWidget(self.portlabel, 0, 4, 1, 1)

        self.ManReconnectButton = QtGui.QPushButton('Reconnect Controller')
        self.layout.addWidget(self.ManReconnectButton, 0, 1, 1, 1)
        self.ManReconnectButton.clicked.connect(
            lambda: self.reConnectDevice('Controller'))
        self.ManReconnectButton.setHidden(True)

        self.DSReconnectButton = QtGui.QPushButton('Reconnect Data Server')
        self.layout.addWidget(self.DSReconnectButton, 0, 2, 1, 1)
        self.DSReconnectButton.clicked.connect(
            lambda: self.reConnectDevice('Data Server'))
        self.DSReconnectButton.setHidden(True)

        self.rowLabel = QtGui.QLabel()
        self.layout.addWidget(self.rowLabel, 0, 6, 1, 1)

        self.scanLabel = QtGui.QLabel()
        self.layout.addWidget(self.scanLabel, 0, 7, 1, 1)

        self.removeButton = QtGui.QPushButton('Remove')
        self.removeButton.clicked.connect(self.removeDevice)
        self.layout.addWidget(self.removeButton, 0, 8, 1, 1)

    def removeDevice(self):
        self.removeSig.emit(self)

    def reConnectDevice(self, sender):
        self.IP = str(self.channel.text().split(': ')[-1])
        self.PORT = int(self.portlabel.text().split(': ')[-1])
        self.reconnectSig.emit((sender, self.name, (self.IP, self.PORT)))

    def set_disconnected(self,origin):
        if origin == 'Controller':
            self.ManLabel.setStyleSheet(self.not_ok)
            self.ManReconnectButton.setVisible(True)
        else:
            self.DSLabel.setStyleSheet(self.not_ok)
            self.DSReconnectButton.setVisible(True)
            
    def set_connected(self,origin):
        if origin == 'Controller':
            self.ManLabel.setStyleSheet(self.ok)
            self.ManReconnectButton.setHidden(True)
        else:
            self.DSLabel.setStyleSheet(self.ok)
            self.DSReconnectButton.setHidden(True)
   