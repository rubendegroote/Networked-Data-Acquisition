import asyncore
import threading as th
import time
import configparser
from multiprocessing import freeze_support
import sys
from PyQt4 import QtCore, QtGui

from backend.connectors import Connector
from connectiondialogs import Man_DS_ConnectionDialog
from connectionwidgets import DeviceConnections
from controlwidget import ControlWidgets,ControlWidget
from scanner import ScannerWidget

class ControllerApp(QtGui.QMainWindow):
    updateSignal = QtCore.pyqtSignal(tuple)
    messageUpdateSignal = QtCore.pyqtSignal(dict)
    lost_connection = QtCore.pyqtSignal(object)
    def __init__(self):
        super(ControllerApp, self).__init__()
        self.looping = True
        self.hasMan = False
        self.hasDS = False
        self.masses = []
        t = th.Thread(target=self.startIOLoop).start()
        self.init_UI()

        self.control_widgets = ControlWidgets()
        self.control_widgets.device_missing.connect(self.add_control_tab)

        self.updateSignal.connect(self.updateUI)
        self.messageUpdateSignal.connect(self.updateMessages)
        self.lost_connection.connect(self.update_ui_connection_lost)

        self.errorTracker = {}

        self.show()

        self.connectToServers()

    def connectToServers(self):
        respons = Man_DS_ConnectionDialog.getInfo(parent=self)
        if respons[1]:
            self.addConnection(respons[0])

    def init_UI(self):
        self.central = QtGui.QSplitter()
        widget = QtGui.QWidget()
        self.central.addWidget(widget)
        layout = QtGui.QGridLayout(widget)
        self.setCentralWidget(self.central)

        self.mainTabs = QtGui.QTabWidget()
        layout.addWidget(self.mainTabs)

        # self.connLabel = QtGui.QLabel('<font size="5"><b>Tuning <\b><\font>')
        # layout.addWidget(self.connLabel, 0, 0, 1, 1)

        self.scanner = ScannerWidget()
        self.scanner.scanInfoSig.connect(self.start_scan)
        self.scanner.stopScanSig.connect(self.stop_scan)
        self.scanner.setPointSig.connect(self.go_to_setpoint)
        self.scanner.calibration_sig.connect(self.calibrate_wavemeter)
        #self.scanner.toggleConnectionsSig.connect(self.toggleConnectionsUI)
        self.mainTabs.addTab(self.scanner, 'Tuning')
        # layout.addWidget(self.scanner, 1, 0, 1, 1)

        # self.connLabel = QtGui.QLabel('<font size="5"><b>Connections <\b><\font>')
        # layout.addWidget(self.connLabel, 2, 0, 1, 1)

        self.controltab = QtGui.QTabWidget()
        # layout.addWidget(self.controltab,3,0,1,1)
        self.mainTabs.addTab(self.controltab, 'Connections')

        self.connWidget = DeviceConnections()
        self.connWidget.connectSig.connect(self.add_connector)
        self.connWidget.removeSig.connect(self.remove_connector)
        self.controltab.addTab(self.connWidget, 'Device Overview')

        self.serverConnectButton = QtGui.QPushButton('Connect to Servers')
        self.serverConnectButton.clicked.connect(self.connectToServers)
        # layout.addWidget(self.serverConnectButton, 4, 0, 1, 1)

        self.messageLog = QtGui.QPlainTextEdit()
        self.central.addWidget(self.messageLog)

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

        if self.Man_DS_Connector.man or self.Man_DS_Connector.DS:
            self.enable()
            config = configparser.ConfigParser()
            if self.Man_DS_Connector.man and self.Man_DS_Connector.DS:
                self.statusBar().showMessage(
                    'Connected to Controller and Data Server')
                config['controller'] = {'address': data[0], 'port': int(data[1])}
                config['data server'] = {'address': data[2], 'port': int(data[3])}
            elif self.Man_DS_Connector.man:
                self.statusBar().showMessage('No Data Server Connection')
                config['controller'] = {'address': data[0], 'port': int(data[1])}
            elif self.Man_DS_Connector.DS:
                self.statusBar().showMessage('No Controller Connection')
                config['data server'] = {'address': data[2], 'port': int(data[3])}
                
            with open('ControllerDSConnections.ini', 'w') as configfile:
                config.write(configfile)
        
        else:
            self.statusBar().showMessage('Connection failure')


    def reply_cb(self, message):
        track = message['track']
        if message['reply']['parameters']['status'][0] == 0:
            function = message['reply']['op']
            args = message['reply']['parameters']
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
        self.lost_connection.emit(connector)

    def update_ui_connection_lost(self,connector):
        self.statusBar().showMessage(
            connector.acceptor_name + ' connection failure')
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
            time.sleep(0.05)

    def stopIOLoop(self):
        self.looping = False

    def add_control_tab(self,name):
        control_widget = ControlWidget(name)
        self.control_widgets.controls[name] = control_widget
        control_widget.refresh_changed_sig.connect(self.change_refresh_time)
        if name =='M2':
            control_widget.prop_changed_sig.connect(self.change_device_prop)
            control_widget.lock_etalon_sig.connect(self.lock_device_etalon)
            control_widget.etalon_value_sig.connect(self.set_device_etalon)
            control_widget.lock_cavity_sig.connect(self.lock_device_cavity)
            control_widget.cavity_value_sig.connect(self.set_device_cavity)
            control_widget.lock_wavelength_sig.connect(self.lock_device_wavelength)
            control_widget.lock_ecd_sig.connect(self.lock_device_ecd)
            control_widget.wavenumber_sig.connect(self.go_to_setpoint)
            control_widget.setpoint_reached_sig.connect(self.scanner.set_on_setpoint) ## bit of a hack
        elif name == 'wavemeter':
            control_widget.calibrate_sig.connect(self.calibrate_wavemeter)
            control_widget.setpoint_value_sig.connect(self.scanner.set_setpoint_value) ## bit of a hack
        elif name == 'RILIS':
            control_widget.setpoint_value_sig.connect(self.scanner.set_setpoint_value) ## bit of a hack
            

        self.controltab.addTab(control_widget,name)

    def closeEvent(self, event):
        self.stopIOLoop()
        event.accept()

    def status_reply(self, track, params):
        origin, track_id = track[-1]
        if origin == 'Controller':
            self.updateSignal.emit((self.scanner.update,
                                    {'track':track,
                                    'args':params}))
            self.masses = params['masses']
            self.updateSignal.emit((self.control_widgets.update,
                                    {'track':track,
                                    'args':params['status_data']}))
            self.updateSignal.emit((self.connWidget.updateScan,
                                    {'track':track,
                                    'args':params}))


        elif origin == 'DataServer':
            self.updateSignal.emit((self.connWidget.updateData,
                                    {'track':track,
                                    'args':params}))

        self.updateSignal.emit((self.connWidget.update,
                                       {'track':track,
                                       'args':params['connector_info']}))

    def forward_instruction_reply(self,track,params):
        origin,track_id = track[-1]
        self.messageUpdateSignal.emit(
            {'track':track,'args':[[0],"Instruction forwarded"]})

    def change_refresh_time(self,info):
        device, time = info
        self.Man_DS_Connector.instruct('Controller',('forward_instruction',
                                                    {'instruction':'change_device_refresh',
                                                     'device':device,
                                                     'arguments':{'time':time}}))
    def change_device_prop(self,info):
        device, prop = info
        self.Man_DS_Connector.instruct('Controller',('forward_instruction',
                                                    {'instruction':'change_device_prop',
                                                     'device':device,
                                                     'arguments':{'prop':prop}}))
    def lock_device_etalon(self,info):
        device, lock = info
        self.Man_DS_Connector.instruct('Controller',('forward_instruction',
                                                    {'instruction':'lock_device_etalon',
                                                     'device':device,
                                                     'arguments':{'lock':lock}}))

    def set_device_etalon(self,info):
        device, etalon_value = info
        self.Man_DS_Connector.instruct('Controller',('forward_instruction',
                                                    {'instruction':'set_device_etalon',
                                                     'device':device,
                                                     'arguments':{'etalon_value':etalon_value}}))
    def lock_device_cavity(self,info):
        device, lock = info
        self.Man_DS_Connector.instruct('Controller',('forward_instruction',
                                                    {'instruction':'lock_device_cavity',
                                                     'device':device,
                                                     'arguments':{'lock':lock}}))
    def set_device_cavity(self,info):
        device, cavity_value = info
        self.Man_DS_Connector.instruct('Controller',('forward_instruction',
                                                    {'instruction':'set_device_cavity',
                                                     'device':device,
                                                     'arguments':{'cavity_value':cavity_value}}))
    def lock_device_wavelength(self,info):
        device, lock = info
        self.Man_DS_Connector.instruct('Controller',('forward_instruction',
                                                    {'instruction':'lock_device_wavelength',
                                                     'device':device,
                                                     'arguments':{'lock':lock}}))
    def lock_device_ecd(self,info):
        device, lock = info
        self.Man_DS_Connector.instruct('Controller',('forward_instruction',
                                                    {'instruction':'lock_device_ecd',
                                                     'device':device,
                                                     'arguments':{'lock':lock}}))
    def calibrate_wavemeter(self,info):
        device = info['device']
        self.Man_DS_Connector.instruct('Controller',('forward_instruction',
                                                     {'instruction':'calibrate_wavemeter',      
                                                     'device':device,
                                                     'arguments':{}}))
    def start_scan(self, scanInfo):
        # ask for the isotope mass
        masses = [str(m) for m in self.masses]
        mass, result = QtGui.QInputDialog.getItem(self, 'Mass Input Dialog',
                'Choose a mass or enter new mass:', masses)
        if result:
            scanInfo['mass'] = [int(mass)]
            self.Man_DS_Connector.instruct('Controller', ('start_scan', scanInfo))
        else:
            pass

    def start_scan_reply(self,track,params):
        origin,track_id = track[-1]
        self.messageUpdateSignal.emit(
            {'track':track,'args':[[0],"Start scan instruction received"]})

    def stop_scan(self):
        self.Man_DS_Connector.instruct('Controller', ('stop_scan',{}))

    def stop_scan_reply(self,track,params):
        origin,track_id = track[-1]
        self.messageUpdateSignal.emit(
            {'track':track,'args':[[0],"Stop scan instruction received"]})

    def go_to_setpoint(self, setpointInfo):
        self.Man_DS_Connector.instruct('Controller', ('go_to_setpoint', setpointInfo))

    def go_to_setpoint_reply(self,track,params):
        origin,track_id = track[-1]
        self.messageUpdateSignal.emit(
            {'track':track,'args':[[0],"Go to setpoint instruction received"]})

    def add_connector(self, info):
        receiver, name, address = info
        self.Man_DS_Connector.instruct(receiver, ('add_connector',{'address': address}))
        if not name in self.control_widgets.controls.keys():
            self.add_control_tab(name)

    def add_connector_reply(self,track,params):
        origin,track_id = track[-1]
        self.messageUpdateSignal.emit(
            {'track':track,'args':[[0],"Add connector instruction received"]})

    def remove_connector(self, address):
        self.Man_DS_Connector.instruct('Both',('remove_connector', {'address': address}))

    def remove_connector_reply(self,track,params):
        origin,track_id = track[-1]
        self.messageUpdateSignal.emit(
            {'track':track,'args':[[0],"Remove connector instruction received"]})

    def updateMessages(self,info):
        track,message = info['track'],info['args']
        text = '{}: {} reports {}'.format(track[-1][1],track[-1][0],message[1])
        if message[0][0] == 0:
            self.messageLog.appendPlainText(text)
        else:
            textErr = str(track[-1][0]) + str(message[1])
            if textErr not in self.errorTracker or time.time() - self.errorTracker[textErr] > 5:
                self.errorTracker[textErr] = time.time()
                error_dialog = QtGui.QErrorMessage(self)
                error_dialog.showMessage(text)
                error_dialog.exec_()

class Man_DS_Connector():

    def __init__(self,ManChan,DSChan,callback,
            onCloseCallback,default_cb):

        try:
            self.DS = Connector(chan=DSChan,name='MGUI_to_DS',
                          callback=callback,
                          default_callback = default_cb)
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
            print('Error connecting to controller \n'+ str(e))
            self.man = None

    def instruct(self, receiver, instr):
        if receiver == 'Controller':
            self.man.add_request(instr)
        elif receiver == 'Data Server':
            self.DS.add_request(instr)
        elif receiver == 'Both':
            self.man.add_request(instr)
            self.DS.add_request(instr)


def main():
    # add freeze support
    freeze_support()
    app = QtGui.QApplication(sys.argv)
    m = ControllerApp()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()