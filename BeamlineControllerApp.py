import asyncore
import threading as th
import time
import configparser
from multiprocessing import freeze_support
import os,sys
from PyQt4 import QtCore, QtGui
import pyqtgraph as pg
from spin import Spin
from beamlinegraph import BeamlineGraph
import pandas as pd
from connectiondialogs import Contr_DS_ConnectionDialog

from backend.connectors import Connector

# from cupswitcher import CupSwitcher

from ui_7001switcher import CupSwitcher

class ControlContainer(QtGui.QWidget):
    new_setpoint = QtCore.pyqtSignal(dict)
    def __init__(self):
        super(ControlContainer,self).__init__()
        self.max_offset = 50
        self.layout = QtGui.QGridLayout(self)

        self.status_label = QtGui.QLabel("On Setpoint")
        self.status_label.setMaximumHeight(15)
        self.on_setpoint = False
        self.status_label.setStyleSheet("QLabel { background-color: red; }")
        self.layout.addWidget(self.status_label,1,0,1,1)

        self.layout.addWidget(QtGui.QWidget(),1000,0,1,1)

        self.ControlsLayout = QtGui.QGridLayout()
        self.layout.addLayout(self.ControlsLayout,10,0,1,1)
        self.controls = {}

    def update_controls(self,track,params):
        data = params['latest_data']['beamline']
        for key in self.controls.keys():
            val = data[self.formats['beamline'].index(key)]
            self.update_control(key=key,readback=val)

    def update(self,track,params):
        on_setpoint = params['on_setpoint']['beamline']
        if not on_setpoint == self.on_setpoint:
            self.on_setpoint = on_setpoint
            if on_setpoint:
                self.status_label.setStyleSheet("QLabel { background-color: green; }")
            else:
                self.status_label.setStyleSheet("QLabel { background-color: red; }")

    def define_controls(self,track,params):
        controls = params['data_format']['beamline']
        for c in controls:
            if not c in ('timestamp','offset','scan_number','mass','current'):
                label = QtGui.QLabel(str(c))
                self.ControlsLayout.addWidget(label,len(self.controls)%20,3*(len(self.controls)//20))
                setbox = Spin(value = 0)
                setbox.name = c
                setbox.setMaximumWidth(45)
                setbox.setMinimumWidth(45)
                setbox.sigValueChanging.connect(self.change_volts)
                self.ControlsLayout.addWidget(setbox,len(self.controls)%20,3*(len(self.controls)//20)+1)
                readback = QtGui.QLabel(str(0))
                readback.setMaximumWidth(45)
                readback.setMinimumWidth(45)
                self.ControlsLayout.addWidget(readback,len(self.controls)%20,3*(len(self.controls)//20)+2)
                self.controls[c] = (label,setbox,readback)

    def change_volts(self):
        setpoints = self.get_setpoints()
        self.new_setpoint.emit({'parameter':['voltages'],
                                'setpoint':[setpoints]})

    def ramp_down(self):
        for key,val in self.controls.items():
            self.controls[key][1].sigValueChanging.disconnect(self.change_volts)
            self.controls[key][1].value = 0
            self.controls[key][1].sigValueChanging.connect(self.change_volts)

        self.change_volts()

    def setControl(self,name,value):
        self.controls[name][1].setText(value)

    def get_setpoints(self):
        return {n:s[1].value for n,s in self.controls.items()}

    def update_control(self,key,readback=0,setpoint=0):
        self.controls[key][1].sigValueChanging.disconnect(self.change_volts)
        # self.controls[key][1].setValue(setpoint)

        self.controls[key][2].setText(str(round(readback,2)))

        # if abs(setpoint - readback) > self.max_offset:
        #     self.setStyleSheet("QLineEdit { background-color: red; }")
        # # elif abs(self.voltage.rampSet - readback) > self.max_offset:
        # #     self.setStyleSheet("QLineEdit { background-color: yellow; }")
        # else:
        #     self.setStyleSheet("QLineEdit { background-color: green; }")

        self.controls[key][1].sigValueChanging.connect(self.change_volts)

class BeamlineControllerApp(QtGui.QMainWindow):
    updateSignal = QtCore.pyqtSignal(tuple)
    messageUpdateSignal = QtCore.pyqtSignal(dict)
    def __init__(self):
        super(BeamlineControllerApp, self).__init__()   
        self.updateSignal.connect(self.updateUI)
        self.messageUpdateSignal.connect(self.updateMessages)
        self.initialized = False
        self.ask_data = True
        self.looping = True
        t = th.Thread(target=self.startIOLoop).start()
        self.init_UI()

        self.connectToServers()

    def connectToServers(self):
        respons = Contr_DS_ConnectionDialog.getInfo(parent=self)
        if respons[1]:
            self.addConnection(respons[0])

    def addConnection(self, data):
        ManChan = data[0], int(data[1])
        DSChan = data[2], int(data[3])
        
        try:
            self.control_connector = Connector(name = 'BGui_to_C',
                                 chan=ManChan,
                                 callback=self.reply_cb,
                                 default_callback = self.default_c_cb,
                                 onCloseCallback = self.lostConn)

        except Exception as e:
            self.control_connector = None

        try:
            self.DS_connector = Connector(name = 'BGui_to_DS',
                                 chan=DSChan,
                                 callback=self.reply_cb,
                                 default_callback=self.default_DS_cb,
                                 onCloseCallback = self.lostConn)
        except Exception as e:
            self.DS_connector = None


        if self.control_connector or self.DS_connector:
            if self.control_connector and self.DS_connector:
                self.statusBar().showMessage(
                    'Connected to Controller and Data Server')
            elif self.control_connector:
                self.statusBar().showMessage('No Data Server Connection')
            elif self.DS_connector:
                self.statusBar().showMessage('No Controller Connection')
                
        else:
            self.statusBar().showMessage('Connection failure')


    def init_UI(self):
        self.makeMenuBar()

        self.central = QtGui.QSplitter()
        self.setCentralWidget(self.central)

        wid = QtGui.QWidget()
        lay = QtGui.QGridLayout(wid)
        self.central.addWidget(wid)
        
        self.container = ControlContainer()
        lay.addWidget(self.container,0,0)

        self.cupswitcher = CupSwitcher()
        self.cupswitcher.switch_sig.connect(self.switch_cup)
        lay.addWidget(self.cupswitcher,1,0)

        self.container.new_setpoint.connect(self.change_volts)

        self.graph = BeamlineGraph()
        self.central.addWidget(self.graph)

        self.messageLog = QtGui.QPlainTextEdit()
        self.errorTracker = {}
        # self.central.addWidget(self.messageLog)

        self.show()

    def makeMenuBar(self):
        menubar = self.menuBar()

        self.saveAction = QtGui.QAction('&Save',self)
        self.saveAction.setShortcut('Ctrl+S')
        self.saveAction.setStatusTip('Save beam tuning parameters')
        self.saveAction.triggered.connect(self.save)

        self.loadAction = QtGui.QAction('&Load',self)
        self.loadAction.setShortcut('Ctrl+O')
        self.loadAction.setStatusTip('Load beam tuning parameters')
        self.loadAction.triggered.connect(self.load)

        fileMenu = menubar.addMenu('&File')
        fileMenu.addAction(self.saveAction)
        fileMenu.addAction(self.loadAction)

        self.optimizeAction = QtGui.QAction('&Optimize',self)
        self.optimizeAction.setShortcut('Ctrl+T')
        self.optimizeAction.setStatusTip('Optimize beam tuning parameters')
        self.optimizeAction.triggered.connect(self.optimize)

        self.rampDownAction = QtGui.QAction('&Ramp down all',self)
        self.rampDownAction.setShortcut('Ctrl+R')
        self.rampDownAction.setStatusTip('Ramp all voltages to zero')
        self.rampDownAction.triggered.connect(self.ramp_down)

        beamMenu = menubar.addMenu('&Beamline')
        beamMenu.addAction(self.optimizeAction)
        beamMenu.addAction(self.rampDownAction)

    def updateUI(self,*args):
        target,info_dict = args[0]
        params,track = info_dict['args'],info_dict['track']
        target(track,params)

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

    def default_c_cb(self):
        return 'status',{}

    def default_DS_cb(self):
        # data server time!
        if not self.initialized:
            return 'data_format',{}
        else:
            if self.ask_data:
                self.ask_data = False
                return 'get_data',{'no_of_rows':self.graph.no_of_rows,
                           'x':['current','timestamp'],
                           'y':['current','current']}
            else:
                self.ask_data = True
                return 'get_latest',{}

    def status_reply(self,track,params):
        self.cupswitcher.setOptions(params['status_data']['current']['cup_names'])
        self.cupswitcher.set_cup_in(params['status_data']['current']['cup_in'])
        self.updateSignal.emit((self.container.update,{'track':track,
                                    'args':params}))

    def get_data_reply(self,track,params):
        data = params['data']
        self.graph.no_of_rows = params['no_of_rows']
        frame = pd.DataFrame({'x':data[0],'y':data[3]})
        self.graph.data = self.graph.data.append(frame)

        self.updateSignal.emit((self.graph.plot,{'track':track,
                                    'args':params}))

    def get_latest_reply(self,track,params):
        self.updateSignal.emit((self.container.update_controls,{'track':track,
                                    'args':params}))

    def data_format_reply(self,track,params):
        origin, track_id = track
        self.container.formats = params['data_format']

        if not self.container.formats == {}:
            self.updateSignal.emit((self.container.define_controls,{'track':track,
                            'args':params}))
            self.graph.no_of_rows = {k:0 for k in self.container.formats.keys()}

            self.initialized = True

    def add_connector_reply(self,track,params):
        origin,track_id = track[-1]
        self.messageUpdateSignal.emit(
            {'track':track,'args':[[0],"Add connector instruction received"]})
    
    def forward_instruction_reply(self,track,params):
        origin,track_id = track[-1]
        self.messageUpdateSignal.emit(
            {'track':track,'args':[[0],"Instruction forwarded"]})

    def change_volts(self,arguments):
        self.control_connector.add_request(('forward_instruction',
                                   {'instruction':'go_to_setpoint',
                                    'device':'beamline',
                                    'arguments':arguments}))

    def switch_cup(self,cup):
        arguments = {'cup':cup}
        self.control_connector.add_request(('forward_instruction',
                                   {'instruction':'switch_cup',
                                    'device':'current',
                                    'arguments':arguments}))
    def save(self):
        fileName = QtGui.QFileDialog.getSaveFileName(self, 
            'Select file', os.getcwd(),"CSV (*.csv)")
        if fileName == '':
            return
        # Saves the settings to a .txt so they can easily be loaded next time.
        with open(fileName,'w') as f:
            for n,s in self.container.get_setpoints().items():
                f.write(n + ';' + str(s))
                f.write('\n')

    def load(self):
        fileName = QtGui.QFileDialog.getOpenFileName(self, 
            'Select file', os.getcwd(),"CSV (*.csv)")
        if fileName == '':
            return

        with open(fileName,'r') as f:
            for line in f.readlines():
                name,value = line.split(';')
                value = float(value.strip('\n'))
                self.container.setControl(name,value)
        self.container.change_volts()

    def optimize(self):
        print('optimization requested')

        # choose supplies

        # choose a range

        # choose time per step

        # loop over scanning region, send commands

        # update a plot
        
    def ramp_down(self):
        msgBox = QtGui.QMessageBox()
        msgBox.setText("Voltage ramp requested.")
        msgBox.setInformativeText("Do you want to save or discard the current voltages, or cancel the ramp?")
        msgBox.setStandardButtons(QtGui.QMessageBox.Save | QtGui.QMessageBox.Discard | QtGui.QMessageBox.Cancel)
        msgBox.setDefaultButton(QtGui.QMessageBox.Save)
        ret = msgBox.exec_()

        if ret == QtGui.QMessageBox.Save:
            self.save()
            self.container.ramp_down()

        elif ret == QtGui.QMessageBox.Discard:
            self.container.ramp_down()

        elif ret == QtGui.QMessageBox.Cancel:
            return

    def lostConn(self,connector):
        self.connectToServers()

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

    def startIOLoop(self):
        while self.looping:
            asyncore.loop(count=1)
            time.sleep(0.05)

    def stopIOLoop(self):
        self.looping = False

    def closeEvent(self, event):
        msgBox = QtGui.QMessageBox()
        msgBox.setText("Closing program.")
        msgBox.setInformativeText("Do you want to save or discard the current voltages, or cancel?")
        msgBox.setStandardButtons(QtGui.QMessageBox.Save | QtGui.QMessageBox.Discard | QtGui.QMessageBox.Cancel)
        msgBox.setDefaultButton(QtGui.QMessageBox.Save)
        ret = msgBox.exec_()

        if ret == QtGui.QMessageBox.Save:
            self.save()
            self.stopIOLoop()
            event.accept()

        elif ret == QtGui.QMessageBox.Discard:
            self.stopIOLoop()
            event.accept()

        elif ret == QtGui.QMessageBox.Cancel:
            event.ignore()




def main():
    # add freeze support
    freeze_support()
    app = QtGui.QApplication(sys.argv)
    m = BeamlineControllerApp()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
