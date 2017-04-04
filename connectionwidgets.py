from PyQt5 import QtCore, QtGui, QtWidgets
import configparser
from connectiondialogs import ConnectionDialog
import os

CONFIG_PATH = "\\\\cern.ch\\dfs\\Users\\c\\CRIS\\Documents\\Networked-Data-Acquisition\\Config files\\config.ini"

class DeviceConnections(QtWidgets.QWidget):
    connectSig = QtCore.pyqtSignal(tuple)
    removeSig = QtCore.pyqtSignal(tuple)
    removeAllSig = QtCore.pyqtSignal(bool)
    refresh_changed_sig = QtCore.pyqtSignal(tuple)
    change_save_mode_sig = QtCore.pyqtSignal(tuple)

    ### get configuration details
    config_parser = configparser.ConfigParser()
    config_parser.read(CONFIG_PATH)
    def __init__(self, parent=None):
        super(DeviceConnections, self).__init__(parent)
        ports = self.config_parser['ports']
        IPs = self.config_parser['IPs devices']
        self.address = {k:(IPs[k],ports[k])
                   for k in ports.keys() if not k in ('data_server','controller','file_server')}
        self.reads_data = self.config_parser['read_data']
        self.saves_data = self.config_parser['save_data']
        self.saves_stream = self.config_parser['save_stream']

        self.deviceWidgets = {}
        self.l = 0
        self.layout = QtWidgets.QGridLayout(self)

        self.deviceSelection = QtGui.QComboBox()
        self.deviceSelection.addItems(sorted(list(self.address.keys())))
        self.deviceSelection.setCurrentIndex(0)
        self.layout.addWidget(self.deviceSelection, 100, 0, 1, 1)

        self.addDeviceButton = QtWidgets.QPushButton('Add Device')
        self.addDeviceButton.clicked.connect(self.addConnection)
        self.layout.addWidget(self.addDeviceButton, 100, 1, 1, 1)

        spacer = QtGui.QSpacerItem(20,40,QtGui.QSizePolicy.Minimum,QtGui.QSizePolicy.Expanding)
        self.layout.addItem(spacer,200,0,1,1)

        self.ManDevices = []
        self.DSDevices = []

    def addConnection(self):
        selection = self.deviceSelection.currentText()
        respons = self.address[selection]
        if self.reads_data[selection] == 'yes':
            self.connectSig.emit(('Both', selection, respons))
        else:
            self.connectSig.emit(('Controller', selection, respons))

    def addDeviceWidget(self, name='',IP='',PORT=5000):
        self.deviceWidgets[name] = DeviceWidget(self, name, IP, PORT, self.reads_data[name] == 'yes')

        self.deviceWidgets[name].removeSig.connect(self.remove)
        self.deviceWidgets[name].refresh_changed_sig.connect(self.emit_refresh_change)
        self.deviceWidgets[name].change_save_mode_sig.connect(self.emit_save_mode_change)

        self.deviceWidgets[name].reconnectSig.connect(self.reconnect)
        self.layout.addWidget(self.deviceWidgets[name], self.l, 0, 1, 2)
        
        self.l += 1

    def emit_refresh_change(self,info):
        self.refresh_changed_sig.emit(info)

    def emit_save_mode_change(self,info):
        self.change_save_mode_sig.emit(info)

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
                rows = params['no_of_rows'][key]
                save = params['saving_devices'][key]
                stream = params['saving_stream_devices'][key]
                val.set_data_state(rows,save,stream)
            except KeyError as e:
                pass

    def updateRefresh(self,track,refresh_times):
        for key,val in self.deviceWidgets.items():
            try:
                val.refresh_time = refresh_times[key]
            except KeyError:
                pass

class DeviceWidget(QtWidgets.QWidget):
    removeSig = QtCore.pyqtSignal(object)
    reconnectSig = QtCore.pyqtSignal(object)
    refresh_changed_sig = QtCore.pyqtSignal(tuple)
    change_save_mode_sig = QtCore.pyqtSignal(tuple)

    def __init__(self, parent=None, name='',IP='',PORT=5000,data=True):
        super(DeviceWidget, self).__init__(parent)
        self.IP = str(IP)
        self.PORT = str(PORT)
        self.name = name
        self.has_data_connection = data

        self.not_ok = "QLabel { background-color: red }"
        self.neutral = "QLabel { background-color: yellow }"
        self.ok = "QLabel { background-color: green }"

        self.layout = QtWidgets.QGridLayout(self)

        self.label = QtWidgets.QLabel(' ' + str(name))
        self.label.setMinimumWidth(100)
        self.layout.addWidget(self.label, 0, 0, 1, 1)

        self.ManLabel = QtWidgets.QLabel('Controller')
        self.ManLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.ManLabel.setMinimumWidth(120)
        self.ManLabel.setMinimumHeight(25)
        self.ManLabel.setStyleSheet(self.not_ok)
        self.layout.addWidget(self.ManLabel, 0, 1, 1, 1)

        if self.has_data_connection:
            self.DSLabel = QtWidgets.QLabel('Data Server')
            self.DSLabel.setStyleSheet(self.not_ok)
        else:
            self.DSLabel = QtWidgets.QLabel('Data-less Device')
            self.DSLabel.setStyleSheet(self.neutral)

        self.DSLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.DSLabel.setMinimumWidth(120)
        self.DSLabel.setMinimumHeight(25)
        self.layout.addWidget(self.DSLabel, 0, 2, 1, 1)

        self.IP = IP
        self.PORT = PORT
        self.refresh_time = 0

        self.save = None
        self.saveLabel = QtWidgets.QLabel(self, text='')
        self.layout.addWidget(self.saveLabel, 0, 3, 1, 1)
        self.stream = None
        self.streamLabel = QtWidgets.QLabel(self, text='')
        self.layout.addWidget(self.streamLabel, 0, 4, 1, 1)

        self.ManReconnectButton = QtWidgets.QPushButton('Reconnect Controller')
        self.layout.addWidget(self.ManReconnectButton, 0, 1, 1, 1)
        self.ManReconnectButton.clicked.connect(
            lambda: self.reConnectDevice('Controller'))
        self.ManReconnectButton.setHidden(True)

        self.DSReconnectButton = QtWidgets.QPushButton('Reconnect Data Server')
        self.layout.addWidget(self.DSReconnectButton, 0, 2, 1, 1)
        self.DSReconnectButton.clicked.connect(
            lambda: self.reConnectDevice('Data Server'))
        self.DSReconnectButton.setHidden(True)

        self.rowLabel = QtWidgets.QLabel()
        self.layout.addWidget(self.rowLabel, 0, 6, 1, 1)

        self.scanLabel = QtWidgets.QLabel()
        self.layout.addWidget(self.scanLabel, 0, 7, 1, 1)

        # self.layout.addWidget(QtWidgets.QLabel('Refresh rate (ms)'),0,8)
        # self.refresh_field = QtWidgets.QSpinBox()
        # self.refresh_field.setRange(0,10**4)
        # self.refresh_field.valueChanged.connect(self.emit_refresh_change)
        # self.layout.addWidget(self.refresh_field,0,9)

        self.settingsButton = QtWidgets.QPushButton('Settings...')
        self.settingsButton.clicked.connect(self.show_settings)
        self.layout.addWidget(self.settingsButton, 0, 8, 1, 1)

        self.removeButton = QtWidgets.QPushButton('Remove')
        self.removeButton.clicked.connect(self.removeDevice)
        self.layout.addWidget(self.removeButton, 0, 9, 1, 1)
    
    # def emit_refresh_change(self):
    #     self.refresh_changed_sig.emit((self.name,int(self.refresh_field.value())))

    def show_settings(self):
        info = {'name':self.name,'IP':self.IP,'PORT':self.PORT,'refresh_time':self.refresh_time,
                'save':self.save,'stream':self.stream,
                'reading':self.has_data_connection}
        settings, ok = SettingsDialog.get_settings(self,info)
        self.refresh_changed_sig.emit((self.name,int(settings['refresh'])))
        if not settings['save'] == self.save or not settings['stream'] == self.stream:
            self.change_save_mode_sig.emit((self.name,
                {'save':settings['save'],'stream':settings['stream']}))

    def removeDevice(self):
        self.removeSig.emit(self)

    def reConnectDevice(self, sender):
        # self.IP = str(self.channel.text().split(': ')[-1])
        # self.PORT = str(int(self.portlabel.text().split(': ')[-1]))
        self.reconnectSig.emit((sender, self.name, (self.IP, self.PORT)))

    def set_disconnected(self,origin):
        if origin == 'Controller':
            self.ManLabel.setStyleSheet(self.not_ok)
            self.ManReconnectButton.setVisible(True)
        elif self.has_data_connection:
            self.DSLabel.setStyleSheet(self.not_ok)
            self.DSReconnectButton.setVisible(True)
            
    def set_connected(self,origin):
        if origin == 'Controller':
            self.ManLabel.setStyleSheet(self.ok)
            self.ManReconnectButton.setHidden(True)
        elif self.has_data_connection:
            self.DSLabel.setStyleSheet(self.ok)
            self.DSReconnectButton.setHidden(True)

    def set_data_state(self,rows,save,stream):
        self.rowLabel.setText('data rows: ' + str(rows))

        if not save == self.save:
            self.save = save
            if save:
                self.saveLabel.setText('saving scans')
                self.saveLabel.setStyleSheet("QLabel { color: green }")
            else:
                self.saveLabel.setText('not saving scans')
                self.saveLabel.setStyleSheet("QLabel { color: red }")

        if not stream == self.stream:
            self.stream = stream
            if stream:
                self.streamLabel.setText('saving stream')
                self.streamLabel.setStyleSheet("QLabel { color: green }")
            else:
                self.streamLabel.setText('not saving stream')
                self.streamLabel.setStyleSheet("QLabel { color: red }")
                

class SettingsDialog(QtWidgets.QDialog):
    def __init__(self,parent, info):
        super(SettingsDialog, self).__init__(parent)

        layout = QtWidgets.QGridLayout(self)

        layout.addWidget(QtWidgets.QLabel('Device: {}'.format(info['name'])),0,0)
        layout.addWidget(QtWidgets.QLabel('IP: {}'.format(info['IP'])),1,0)
        layout.addWidget(QtWidgets.QLabel('PORT: {}'.format(info['PORT'])),1,1)

        layout.addWidget(QtWidgets.QLabel('Refresh rate (ms)'),2,0)
        self.refresh_field = QtWidgets.QSpinBox()
        self.refresh_field.setRange(0,10**4)
        self.refresh_field.setValue(int(info['refresh_time']))
        layout.addWidget(self.refresh_field,2,1)

        self.save_data_check = QtGui.QCheckBox('Save scans?')
        self.save_data_check.stateChanged.connect(self.toggle_stream_check)
        layout.addWidget(self.save_data_check,3,0)

        self.save_stream_check = QtGui.QCheckBox('Save stream?')
        layout.addWidget(self.save_stream_check,4,0)

        if not info['reading']:
            self.save_data_check.setChecked(False)
            self.save_data_check.setHidden(True)
            self.save_stream_check.setChecked(False)
            self.save_stream_check.setHidden(True)
        else:
            try:
                self.save_data_check.setChecked(info['save'])
                self.save_stream_check.setChecked(info['stream'])
            except:
                pass

        # OK and Cancel buttons
        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel,
            QtCore.Qt.Horizontal, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons,100,100)

    def toggle_stream_check(self):
        if self.save_data_check.isChecked():
            self.save_stream_check.setEnabled(True)
        else:
            self.save_stream_check.setDisabled(True)
            self.save_stream_check.setChecked(False)

    # get current date and time from the dialog
    def settings(self):
        return {'refresh':self.refresh_field.value(),
            'save':self.save_data_check.isChecked(),
            'stream':self.save_stream_check.isChecked()}

    # static method to create the dialog and return (date, time, accepted)
    @staticmethod
    def get_settings(parent = None,info = {}):
        dialog = SettingsDialog(parent=parent,info=info)
        result = dialog.exec_()
        settings = dialog.settings()
        return (settings, result == QtWidgets.QDialog.Accepted)