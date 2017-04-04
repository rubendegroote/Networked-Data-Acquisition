import asyncore
import threading as th
import time
import configparser
from multiprocessing import freeze_support
import sys
from PyQt5 import QtCore, QtGui, QtWidgets

from backend.connectors import Connector
from connectiondialogs import Contr_DS_ConnectionDialog
from connectionwidgets import DeviceConnections
from controlwidget import ControlWidget
from scanner import ScannerWidget
from LogbookApp import LogbookApp

class ControllerApp(QtWidgets.QMainWindow):
    updateSignal = QtCore.pyqtSignal(tuple)
    messageUpdateSignal = QtCore.pyqtSignal(dict)
    lost_connection = QtCore.pyqtSignal(object)
    def __init__(self):
        super(ControllerApp, self).__init__()

        self.setWindowTitle('Scan and device control')

        self.looping = True
        self.hasMan = False
        self.hasDS = False
        t = th.Thread(target=self.startIOLoop).start()
        
        self.init_UI()
        self.connectToServers()

        self.updateSignal.connect(self.updateUI)
        self.messageUpdateSignal.connect(self.updateMessages)
        self.lost_connection.connect(self.update_ui_connection_lost)

        self.errorTracker = {}

        self.show()

    def connectToServers(self):
        respons = Contr_DS_ConnectionDialog.getInfo(parent=self)
        if respons[1]:
            self.addConnection(respons[0])
            self.logbook.define_controller(self.Contr_DS_Connector.contr)
            self.enable()

    def init_UI(self):
        wid = QtWidgets.QWidget()
        self.layout = QtWidgets.QGridLayout(wid)
        self.setCentralWidget(wid)

        self.tabs = QtWidgets.QTabWidget()
        self.tabs.setTabBar(Tabs(width=100,height=25))
        self.tabs.setTabPosition(QtWidgets.QTabWidget.West)
        self.layout.addWidget(self.tabs,0,0,10,10)

        self.deviceConnections = DeviceConnections()
        self.deviceConnections.removeSig.connect(self.remove_connector)
        self.deviceConnections.connectSig.connect(self.add_connector)
        self.deviceConnections.refresh_changed_sig.connect(self.change_refresh_time) 
        self.deviceConnections.change_save_mode_sig.connect(self.change_save_mode) 
        self.tabs.addTab(self.deviceConnections,'Settings')

        self.deviceWidget = ControlWidget()
        self.deviceWidget.prop_changed_sig.connect(self.change_device_prop)
        self.deviceWidget.int_changed_sig.connect(self.change_device_int)
        self.deviceWidget.diff_changed_sig.connect(self.change_device_diff)
        self.deviceWidget.lock_etalon_sig.connect(self.lock_device_etalon)
        self.deviceWidget.etalon_value_sig.connect(self.set_device_etalon)
        self.deviceWidget.lock_cavity_sig.connect(self.lock_device_cavity)
        self.deviceWidget.cavity_value_sig.connect(self.set_device_cavity)
        self.deviceWidget.lock_wavelength_sig.connect(self.lock_device_wavelength)
        self.deviceWidget.lock_ecd_sig.connect(self.lock_device_ecd)
        self.deviceWidget.wavenumber_sig.connect(self.go_to_setpoint)
        self.deviceWidget.calibrate_sig.connect(self.calibrate_wavemeter)
        self.tabs.addTab(self.deviceWidget,'Devices')

        self.scanner = ScannerWidget()
        self.scanner.scanInfoSig.connect(self.start_scan)
        self.scanner.stopScanSig.connect(self.stop_scan)
        self.scanner.setPointSig.connect(self.go_to_setpoint)
        self.scanner.range_request_sig.connect(self.get_scan_ranges)

        self.tabs.addTab(self.scanner,'Scanning')

        self.logbook = LogbookApp()
        self.tabs.addTab(self.logbook,'Logbook')

        self.statusWidget = StatusWidget()
        self.layout.addWidget(self.statusWidget, 11,0,1,10)

        self.disable()

    def updateUI(self,*args):
        target,info_dict = args[0]
        params,track = info_dict['args'],info_dict['track']
        target(track,params)

    def addConnection(self, data):
        ManChan = data[0], int(data[1])
        DSChan = data[2], int(data[3])
        self.Contr_DS_Connector = Contr_DS_Connector(ManChan, DSChan,
                                 callback=self.reply_cb,
                                 default_cb=self.default_cb,
                                 onCloseCallback = self.lostConn)

        if self.Contr_DS_Connector.contr or self.Contr_DS_Connector.DS:
            self.enable()
            config = configparser.ConfigParser()
            if self.Contr_DS_Connector.contr and self.Contr_DS_Connector.DS:
                self.statusBar().showMessage('Connected to Controller and Data Server')
            elif self.Contr_DS_Connector.contr:
                self.statusBar().showMessage('No Data Server Connection')
            elif self.Contr_DS_Connector.DS:
                self.statusBar().showMessage('No Controller Connection')

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
            params = getattr(self, function)(track,args)

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
        self.disable()
        self.connectToServers()

    def disable(self):
        self.scanner.setDisabled(True)
        self.deviceConnections.setDisabled(True)

    def enable(self):
        self.scanner.setEnabled(True)
        self.deviceConnections.setEnabled(True)

    def toggleConnectionsUI(self,boolean):
        if boolean:
            self.deviceConnections.setEnabled(True)
            self.serverConnectButton.setEnabled(True)
        else:
            self.deviceConnections.setDisabled(True)
            self.serverConnectButton.setDisabled(True)

    def startIOLoop(self):
        while self.looping:
            asyncore.loop(count=1)
            time.sleep(0.05)

    def stopIOLoop(self):
        self.looping = False

    def closeEvent(self, event):
        self.stopIOLoop()
        event.accept()

    def status_reply(self,track,params):
        origin, track_id = track[-1]
        if origin == 'Controller':
            self.updateSignal.emit((self.statusWidget.update,
                                    {'track':track,'args':params}))

            self.updateSignal.emit((self.scanner.update,
                                    {'track':track,'args':params}))

            self.updateSignal.emit((self.deviceWidget.update,
                                    {'track':track,'args':params['status_data']}))

            self.updateSignal.emit((self.deviceConnections.updateRefresh,
                                    {'track':track,'args':params['refresh_time']}))

        elif origin == 'DataServer':
            self.updateSignal.emit((self.deviceConnections.updateData,
                                    {'track':track,'args':params}))

        self.updateSignal.emit((self.deviceConnections.update,
                                    {'track':track,'args':params['connector_info']}))

    def forward_instruction_reply(self,track,params):
        origin,track_id = track[-1]
        self.messageUpdateSignal.emit({'track':track,'args':[[0],"Instruction forwarded"]})

    def change_refresh_time(self,info):
        device, time = info
        self.Contr_DS_Connector.instruct('Controller',('forward_instruction',
                                                    {'instruction':'change_device_refresh',
                                                     'device':device,
                                                     'arguments':{'time':time}}))
    def change_device_prop(self,info):
        device, prop = info
        self.Contr_DS_Connector.instruct('Controller',('forward_instruction',
                                                    {'instruction':'change_device_prop',
                                                     'device':device,
                                                     'arguments':{'prop':prop}}))
    def change_device_int(self,info):
        device, int = info
        self.Contr_DS_Connector.instruct('Controller',('forward_instruction',
                                                    {'instruction':'change_device_int',
                                                     'device':device,
                                                     'arguments':{'int':int}}))
    def change_device_diff(self,info):
        device, diff = info
        self.Contr_DS_Connector.instruct('Controller',('forward_instruction',
                                                    {'instruction':'change_device_diff',
                                                     'device':device,
                                                     'arguments':{'diff':diff}}))
    def lock_device_etalon(self,info):
        device, lock = info
        self.Contr_DS_Connector.instruct('Controller',('forward_instruction',
                                                    {'instruction':'lock_device_etalon',
                                                     'device':device,
                                                     'arguments':{'lock':lock}}))
    def set_device_etalon(self,info):
        device, etalon_value = info
        self.Contr_DS_Connector.instruct('Controller',('forward_instruction',
                                                    {'instruction':'set_device_etalon',
                                                     'device':device,
                                                     'arguments':{'etalon_value':etalon_value}}))
    def lock_device_cavity(self,info):
        device, lock = info
        self.Contr_DS_Connector.instruct('Controller',('forward_instruction',
                                                    {'instruction':'lock_device_cavity',
                                                     'device':device,
                                                     'arguments':{'lock':lock}}))
    def set_device_cavity(self,info):
        device, cavity_value = info
        self.Contr_DS_Connector.instruct('Controller',('forward_instruction',
                                                    {'instruction':'set_device_cavity',
                                                     'device':device,
                                                     'arguments':{'cavity_value':cavity_value}}))
    def lock_device_wavelength(self,info):
        device, lock = info
        self.Contr_DS_Connector.instruct('Controller',('forward_instruction',
                                                    {'instruction':'lock_device_wavelength',
                                                     'device':device,
                                                     'arguments':{'lock':lock}}))
    def lock_device_ecd(self,info):
        device, lock = info
        self.Contr_DS_Connector.instruct('Controller',('forward_instruction',
                                                    {'instruction':'lock_device_ecd',
                                                     'device':device,
                                                     'arguments':{'lock':lock}}))
    def calibrate_wavemeter(self,info):
        device = info['device']
        self.Contr_DS_Connector.instruct('Controller',('forward_instruction',
                                                     {'instruction':'calibrate_wavemeter',      
                                                     'device':device,
                                                     'arguments':{}}))

    def get_scan_ranges(self,scans):
        self.Contr_DS_Connector.instruct('Controller',('get_scan_ranges',{'scans':scans}))

    def get_scan_ranges_reply(self,track,params):
        origin,track_id = track[-1]
        self.updateSignal.emit((self.scanner.fromOldWidget.update_ranges,
                                {'track':track,'args':params}))

    def change_save_mode(self,info):
        device,infodict = info
        infodict['device']=device
        self.Contr_DS_Connector.instruct('Controller',('change_save_mode',infodict))

    def change_save_mode_reply(self,track,params):
        origin,track_id = track[-1]
        
    def start_scan(self, scanInfo):
        # ask for the isotope mass
        scan_mass = self.scanner.fromOldWidget.scan_mass
        masses = [str(m) for m in scan_mass.keys()]
        mass, result = QtGui.QInputDialog.getItem(self, 'Mass Input Dialog',
                'Choose a mass or enter new mass:', masses)
        if result:
            scanInfo['mass'] = [int(mass)]
            self.Contr_DS_Connector.instruct('Controller', ('start_scan', scanInfo))
        else:
            pass

    def start_scan_reply(self,track,params):
        origin,track_id = track[-1]
        self.messageUpdateSignal.emit({'track':track,'args':[[0],"Start scan instruction received"]})

    def stop_scan(self):
        self.Contr_DS_Connector.instruct('Controller', ('stop_scan',{}))

    def stop_scan_reply(self,track,params):
        origin,track_id = track[-1]
        self.messageUpdateSignal.emit({'track':track,'args':[[0],"Stop scan instruction received"]})

    def go_to_setpoint(self, setpointInfo):
        self.Contr_DS_Connector.instruct('Controller', ('go_to_setpoint', setpointInfo))

    def go_to_setpoint_reply(self,track,params):
        origin,track_id = track[-1]
        self.messageUpdateSignal.emit({'track':track,'args':[[0],"Go to setpoint instruction received"]})

    def add_connector(self, info):
        receiver, name, address = info
        self.Contr_DS_Connector.instruct(receiver, ('add_connector',{'address': address}))
        # if not name in self.control_widgets.controls.keys():
        #     self.add_control_tab(name)

    def add_connector_reply(self,track,params):
        origin,track_id = track[-1]
        self.messageUpdateSignal.emit({'track':track,'args':[[0],"Add connector instruction received"]})

    def remove_connector(self, address):
        self.Contr_DS_Connector.instruct('Both',('remove_connector', {'address': address}))

    def remove_connector_reply(self,track,params):
        origin,track_id = track[-1]
        self.messageUpdateSignal.emit({'track':track,'args':[[0],"Remove connector instruction received"]})

    def updateMessages(self,info):
        track,message = info['track'],info['args']
        text = '{}: {} reports {}'.format(track[-1][1],track[-1][0],message[1])
        if message[0][0] == 0:
            # self.messageLog.appendPlainText(text)
            pass
        else:
            textErr = str(track[-1][0]) + str(message[1])
            if textErr not in self.errorTracker or time.time() - self.errorTracker[textErr] > 5:
                self.errorTracker[textErr] = time.time()
                error_dialog = QtGui.QErrorMessage(self)
                error_dialog.showMessage(text)
                error_dialog.exec_()

    def add_entry_to_log_reply(self,track,params):
        self.logbook.add_entry_to_log_reply(track,params)

    def change_entry_reply(self,track,params):
        self.logbook.change_entry_reply(track,params)

    def add_new_field_reply(self,track,params):
        self.logbook.add_new_field_reply(track,params)

    def add_new_tag_reply(self,track,params):
        self.logbook.add_new_tag_reply(track,params)

    def logbook_status_reply(self,track,params):
        self.logbook.logbook_status_reply(track,params)

class Contr_DS_Connector():
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
            self.contr = Connector(chan=ManChan,name='MGui_to_M',
                          callback=callback,
                          default_callback=default_cb)
            # same comment as for the DS closeCallback
            self.contr.onCloseCallback = onCloseCallback

        except Exception as e:
            self.contr_error = e
            print('Error connecting to controller \n'+ str(e))
            self.contr = None

    def instruct(self, receiver, instr):
        if receiver == 'Controller':
            self.contr.add_request(instr)
        elif receiver == 'Data Server':
            self.DS.add_request(instr)
        elif receiver == 'Both':
            self.contr.add_request(instr)
            self.DS.add_request(instr)

class StatusWidget(QtWidgets.QWidget):
    def __init__(self,*args,**kwargs):
        super(StatusWidget,self).__init__()

        self.layout = QtWidgets.QGridLayout(self)

        self.progressBar = QtGui.QProgressBar()
        self.progressBar.setMinimum(0)
        self.progressBar.setMaximum(1000)
        self.layout.addWidget(self.progressBar,0,0,1,1)

        self.textLayout = QtWidgets.QGridLayout()
        self.layout.addLayout(self.textLayout,1,0,1,1)

        self.scan_status = QtWidgets.QLabel()
        self.textLayout.addWidget(self.scan_status,0,0,1,1)

        self.wave_1 = QtWidgets.QLabel('Wavenumber 1:')
        self.textLayout.addWidget(self.wave_1,1,0)

        self.wave_2 = QtWidgets.QLabel('Wavenumber 2:')
        self.textLayout.addWidget(self.wave_2,1,1)

        self.wave_3 = QtWidgets.QLabel('Wavenumber pdl:')
        self.textLayout.addWidget(self.wave_3,1,2)

        self.laser_lock_M2 = QtWidgets.QLabel('M2: not locked')
        self.textLayout.addWidget(self.laser_lock_M2,0,1)

        self.laser_lock_Matisse = QtWidgets.QLabel('Matisse: not locked')
        self.textLayout.addWidget(self.laser_lock_Matisse,0,2)

        self.iscool = QtWidgets.QLabel('ISCOOL: ')
        self.textLayout.addWidget(self.iscool,2,0)

        self.scan_number_label = QtWidgets.QLabel('Scan number: ')
        self.textLayout.addWidget(self.scan_number_label, 2, 1, 1, 1)

        self.proton_label = QtWidgets.QLabel()
        self.textLayout.addWidget(self.proton_label, 2, 2, 1, 1)

        self.proton_info = {}

    def update(self, track, info):
        origin, track_id = track[-1]
        scanning,last_scan,on_setpoint,progress = (info['scanning'],
                                                   info['last_scan'],
                                                   info['on_setpoint'],
                                                   info['progress'])
        self.scan_number_label.setText('Scan number: {}'.format(last_scan))

        if len(progress) > 0:
            scanning = any(scanning.values())
            on_setpoint = all(on_setpoint.values())

            if scanning:
                if on_setpoint:
                    self.scan_status.setText('Scanning, on setpoint')
                else:
                    self.scan_status.setText('Scanning, going to setpoint')
            else:
                if on_setpoint:
                    self.scan_status.setText('Idle, on setpoint')
                else:
                    self.scan_status.setText('Idle, going to setpoint')


            progress = max(progress.values())
            self.progressBar.setValue(1000*progress)

        try:
            proton_info = info['status_data']['proton']
            protons_on = proton_info['HRS_protons_on']
            proton_info = 'Booster info: {}/{} ({} for HRS)'.format(proton_info['SC_current_bunch'],
                                                      proton_info['SC_bunches'],
                                                      proton_info['HRS_bunches'])
            if protons_on == 1:
                proton_info = "<b>" + proton_info + "<\b>"
            self.proton_label.setText(proton_info)
        except:
            self.proton_label.setText("No booster info")
            
        # try:
        #     if not self.proton_info['SC_bunches'] == proton_info['SC_bunches'] or \
        #        not self.proton_info['HRS_bunches'] == proton_info['HRS_bunches']:
        #         msg = QtGui.QMessageBox(self)
        #         msg.setIcon(QtGui.QMessageBox.Warning)
        #         msg.setText("Proton supercycle change")
        #         msg.setInformativeText("The number of HRS bunches in the proton supercycle has changed!")
        #         msg.setWindowTitle("Supercyle info")
        #         msg.setStandardButtons(QtGui.QMessageBox.Ok)
        #         msg.exec_()
        #     self.proton_info = proton_info
        # except:
        #     self.proton_info = proton_info

        try:
            wn_info = info['status_data']['wavemeter']
            self.wave_1.setText("Wavenumber 1: {0:.5f}".format(wn_info['wavenumber_1']))
            self.wave_2.setText("Wavenumber 2: {0:.5f}".format(wn_info['wavenumber_2']))
        except:
            self.wave_1.setText("Wavenumber 1: N/A")
            self.wave_2.setText("Wavenumber 2: N/A")

        try:
            wn_info = info['status_data']['wavemeter_pdl']
            self.wave_3.setText("Wavenumber pdl: {0:.5f}".format(wn_info['wavenumber_1']))
        except:
            self.wave_3.setText("Wavenumber pdl: N/A")
            
    
        try:
            M2_info = info['status_data']['m2']
            lock = M2_info['etalon_lock'] == 'on' and M2_info['cavity_lock'] == 'on'
            if lock:
                self.laser_lock_M2.setText("M2 locked")
                self.laser_lock_M2.setStyleSheet("QLabel {color : black; }");

            else:
                self.laser_lock_M2.setText("M2 not locked")
                self.laser_lock_M2.setStyleSheet("QLabel {color : red; }");

        except:
            self.laser_lock_M2.setText("M2 lock: N/A")

        try:
            Matisse_info = info['status_data']['Matisse']
            lock = Matisse_info['Laser Locked']
            if lock:
                self.laser_lock_Matisse.setText("Matisse locked")
                self.laser_lock_Matisse.setStyleSheet("QLabel {color : black; }");

            else:
                self.laser_lock_Matisse.setText("Matisse not locked")
                self.laser_lock_Matisse.setStyleSheet("QLabel {color : red; }");

        except:
            self.laser_lock_Matisse.setText("Matisse lock: N/A")

        try:
            self.iscool.setText('ISCOOL voltage: {}'.format(info['status_data']['iscool']['voltage']))
        except:
            self.iscool.setText("ISCOOL voltage: N/A")

    def set_setpoint_value(self,val):
        self.setpoint_value.setText(val)
       
class Tabs(QtGui.QTabBar):
    def __init__(self, *args, **kwargs):
        self.tabSize = QtCore.QSize(kwargs.pop('width'), kwargs.pop('height'))
        super(Tabs, self).__init__(*args, **kwargs)

    def paintEvent(self, event):
        painter = QtGui.QStylePainter(self)
        option = QtGui.QStyleOptionTab()

        for index in range(self.count()):
            self.initStyleOption(option, index)
            tabRect = self.tabRect(index)
            tabRect.moveLeft(10)
            painter.drawControl(QtGui.QStyle.CE_TabBarTabShape, option)
            painter.drawText(tabRect, QtCore.Qt.AlignVCenter |\
                             QtCore.Qt.TextDontClip, \
                             self.tabText(index));
        painter.end()
    def tabSizeHint(self,index):
        return self.tabSize

def main():
    # add freeze support
    freeze_support()
    app = QtWidgets.QApplication(sys.argv)
    m = ControllerApp()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()