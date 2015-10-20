import asyncore
import threading as th
import time
import configparser
from multiprocessing import freeze_support
import sys
from PyQt4 import QtCore, QtGui
import pyqtgraph as pg

from backend.connectors import Connector


class ControlContainer(QtGui.QWidget):
    new_setpoint = QtCore.pyqtSignal(dict)
    def __init__(self):
        super(ControlContainer,self).__init__()
        self.max_offset = 50
        self.layout = QtGui.QGridLayout(self)

        self.controls = {}

    def update(self,track,params):
        status_data = params['status_data']['beamline']
        for key,val in status_data.items():
            if key in self.controls.keys():
                self.update_control(key=key,readback=val)
            else:
                label = QtGui.QLabel(str(key))
                self.layout.addWidget(label,len(self.controls),0)
                setbox = pg.SpinBox(value=0,
                              min = 0, max = 10**4,
                              step = 1)
                setbox.name = key
                setbox.sigValueChanging.connect(self.change_volts)
                self.layout.addWidget(setbox,len(self.controls),1)
                readback = QtGui.QLineEdit(str(0))
                self.layout.addWidget(readback,len(self.controls),2)
                self.controls[key] = (label,setbox,readback)

    def change_volts(self):
        sender = self.sender()
        name,value = sender.name,sender.value()
        self.new_setpoint.emit({'parameter':[name],'setpoint':[value]})

    def get_setpoints(self):
        return [s[1].value() for s in self.controls.values()]

    def update_control(self,key,readback=0,setpoint=0):
         # self.set.sigValueChanging.disconnect(self.valueChanged)
        # self.controls[key][1].setValue(setpoint)

        self.controls[key][2].setText(str(readback))

        # if abs(setpoint - readback) > self.max_offset:
        #     self.setStyleSheet("QLineEdit { background-color: red; }")
        # # elif abs(self.voltage.rampSet - readback) > self.max_offset:
        # #     self.setStyleSheet("QLineEdit { background-color: yellow; }")
        # else:
        #     self.setStyleSheet("QLineEdit { background-color: green; }")

        # self.set.sigValueChanging.connect(self.valueChanged)

class BeamlineControllerApp(QtGui.QMainWindow):
    updateSignal = QtCore.pyqtSignal(tuple)
    messageUpdateSignal = QtCore.pyqtSignal(dict)
    def __init__(self):
        super(BeamlineControllerApp, self).__init__()
        self.updateSignal.connect(self.updateUI)
        self.messageUpdateSignal.connect(self.updateMessages)

        self.looping = True
        t = th.Thread(target=self.startIOLoop).start()

        self.central = QtGui.QSplitter()
        self.setCentralWidget(self.central)

        self.container = ControlContainer()
        self.central.addWidget(self.container)
        self.container.new_setpoint.connect(self.change_volts)

        self.messageLog = QtGui.QPlainTextEdit()
        self.errorTracker = {}
        self.central.addWidget(self.messageLog)

        self.show()

        channel = ('PCCRIS15',5004)
        self.connector = Connector(name = 'BGui_to_C',
                                 chan=channel,
                                 callback=self.reply_cb,
                                 default_callback=self.default_cb,
                                 onCloseCallback = self.lostConn)

        self.connector.add_request(('add_connector',{'address': ('PCCRIS3',6007)}))

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

    def status_reply(self,track,params):
        self.updateSignal.emit((self.container.update,{'track':track,
                                    'args':params}))

    def add_connector_reply(self,track,params):
        origin,track_id = track[-1]
        self.messageUpdateSignal.emit(
            {'track':track,'args':[[0],"Add connector instruction received"]})
    
    def forward_instruction_reply(self,track,params):
        origin,track_id = track[-1]
        self.messageUpdateSignal.emit(
            {'track':track,'args':[[0],"Instruction forwarded"]})


    def change_volts(self,arguments):
        self.connector.add_request(('forward_instruction',
                                   {'instruction':'go_to_setpoint',
                                    'device':'beamline',
                                    'arguments':arguments}))

    def default_cb(self):
        return 'status',{}

    def lostConn(self,connector):
        pass

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
        self.stopIOLoop()
        event.accept()

def main():
    # add freeze support
    freeze_support()
    app = QtGui.QApplication(sys.argv)
    m = BeamlineControllerApp()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()