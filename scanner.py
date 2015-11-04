from PyQt4 import QtCore, QtGui
from picbutton import PicButton, PicSpinBox
import numpy as np
from spin import Spin

class ScannerWidget(QtGui.QWidget):

    scanInfoSig = QtCore.pyqtSignal(dict)
    setPointSig = QtCore.pyqtSignal(dict)
    stopScanSig = QtCore.pyqtSignal(bool)
    toggleConnectionsSig = QtCore.pyqtSignal(bool)
    calibration_sig = QtCore.pyqtSignal(dict)
    def __init__(self):
        super(ScannerWidget, self).__init__()
        self.layout = QtGui.QGridLayout(self)

        self.tuning_parameter_combo = QtGui.QComboBox()
        self.tuning_parameters = {}
        self.layout.addWidget(QtGui.QLabel('Tuning parameter'), 0, 0, 1, 1)
        self.layout.addWidget(self.tuning_parameter_combo, 0, 1, 1, 1)

        self.layout.addWidget(QtGui.QLabel("Parameter value"), 0, 2, 1, 1)
        self.setpoint_value = QtGui.QLabel()
        self.layout.addWidget(self.setpoint_value, 0, 3, 1, 1)

        self.scanLabel = QtGui.QLabel('Scan number')
        self.layout.addWidget(self.scanLabel, 1, 0, 1, 1)
        self.scanNumberLabel = QtGui.QLabel(str(-1))
        self.layout.addWidget(self.scanNumberLabel, 1, 1, 1, 1)

        self.scanningLabel = QtGui.QLabel('<font size="4"><b>Scanning<\b><\font>')
        self.layout.addWidget(self.scanningLabel, 2, 0, 1, 4)

        self.progressBar = QtGui.QProgressBar()
        self.progressBar.setMinimum(0)
        self.progressBar.setMaximum(1000)
        self.layout.addWidget(self.progressBar, 3, 0, 1, 4)

        self.startSpin = Spin(11836.0000,0,10**5)
        self.layout.addWidget(self.startSpin, 4, 0, 1, 1)
        self.stepsBox = PicSpinBox(iconName='step.png',
                                   step=1,
                                   value=10,
                                   integer=True)
        self.layout.addWidget(self.stepsBox, 4, 1, 1, 1)

        self.stopSpin = Spin(11836.0000,0,10**5)
        self.layout.addWidget(self.stopSpin, 4, 2, 1, 1)

        self.controlButton = PicButton('start',
                                       checkable=False,
                                       size=100)
        self.state = 'START'
        self.controlButton.clicked.connect(self.control)
        self.layout.addWidget(self.controlButton, 3, 4, 2, 1)

        self.timeEdit = PicSpinBox(value=10,
                                   step=1,
                                   integer=False,
                                   iconName='time')
        self.timeEdit.setToolTip('Use this to specify the waiting\
 information per step for the chosen criterium (see combobox above).')
        self.timeEdit.setMaximumWidth(120)
        self.layout.addWidget(self.timeEdit, 4, 3, 1, 1)

        self.setpointlabel = QtGui.QLabel('<font size="4"><b>Setpoint<\b><\font>')
        self.layout.addWidget(self.setpointlabel, 7, 0, 1, 1)

        self.setpointCombo = QtGui.QComboBox()
        # self.layout.addWidget(self.setpointCombo, 6, 0, 1, 1)
        self.setPointSpin = Spin(11836.0000,0,10**5)
        self.layout.addWidget(self.setPointSpin, 8, 0, 1, 3)

        self.setpointButton = PicButton('manual',
                                        checkable=False,
                                        size=40)
        self.layout.addWidget(self.setpointButton, 8, 3, 1, 1)
        self.setpointButton.clicked.connect(self.makeSetpoint)

        self.setpoint_reached = QtGui.QLabel()
        self.layout.addWidget(self.setpoint_reached, 8, 4)

        self.reverse_button = QtGui.QPushButton('Reverse')
        self.layout.addWidget(self.reverse_button, 5, 1, 1, 1)
        self.reverse_button.clicked.connect(self.reverse_scan)

        self.repeatLabel = QtGui.QLabel('Repeats')
        self.layout.addWidget(self.repeatLabel, 6, 0, 1, 1)
        self.repeatBox = QtGui.QLineEdit("1")
        self.layout.addWidget(self.repeatBox, 6, 1, 1, 1)


    def updateScanNumber(self, scan_number):
        self.scanNumberLabel.setText(str(scan_number))

    def control(self):
        if self.state == "START":
            self.makeScan()
            self.state = "STOP"

        elif self.state == "STOP":
            self.stopScan()
            self.state = "CALIBRATE"

        elif self.state == "CALIBRATE":
            self.send_calibrate()
            self.state = "START"

    def makeScan(self):
        parameter = self.tuning_parameter_combo.currentText()
        self.scan_device,parameter = parameter.split(': ')

        start = float(self.startSpin.value)
        stop = float(self.stopSpin.value)
        steps = float(self.stepsBox.text())
        times = int(self.repeatBox.text())

        if times == 0:
            times == 1

        rng = np.linspace(start,stop,steps)
        newRng = rng
        if times > 1:
            for t in range(times-1):
                if t%2==0:
                    newRng = np.concatenate((newRng,rng[::-1]))
                else:
                    newRng = np.concatenate((newRng,rng))
        rng = list(newRng)

        dt = float(self.timeEdit.text())

        self.scanInfoSig.emit({'device':self.scan_device,
                               'scan_parameter':parameter,
                               'scan_array':rng,
                               'time_per_step':[dt]})

    def reverse_scan(self):
        start = self.startSpin.text()
        stop = self.stopSpin.text()

        self.startSpin.setText(stop)
        self.stopSpin.setText(start)

    def makeSetpoint(self):
        parameter = str(self.tuning_parameter_combo.currentText())
        device,parameter = parameter.split(': ')
        value = self.setPointSpin.value

        self.setPointSig.emit({'device':device,
                               'parameter':parameter,
                               'setpoint': [value]})

    def stopScan(self):
        self.stopScanSig.emit(True)

    def send_calibrate(self):
        self.calibration_sig.emit({'device':'wavemeter'})

    def update(self, track, info):
        origin, track_id = track[-1]
        scanning,calibrated,on_setpoint = info['scanning'],info['calibrated'],info['on_setpoint']
        scan_number, progress = info['scan_number'][0],info['progress']
        write_params = info['write_params']
        print(calibrated)
        if len(progress) > 0:
            scanning = any(scanning.values())
            calibrated = any(calibrated.values())
            progress = max(progress.values())

            self.updateScanNumber(scan_number)
            self.updateProgress(progress)
            if not scanning:
                if calibrated:
                    self.state = "START"
                    self.controlButton.setIcon('start.png')
                    self.controlButton.setToolTip('Click here to start a new scan.')
                    self.toggleConnectionsSig.emit(True)
                else:
                    self.state = "CALIBRATE"
                    self.controlButton.setIcon('calibrate.png')
                    self.controlButton.setToolTip('Click here to calibrate the wavemeter.')
                    self.toggleConnectionsSig.emit(True)

            else:
                self.state = "STOP"
                self.controlButton.setIcon('stop.png')
                self.controlButton.setToolTip(
                    'Click here to stop the current scan.')
                self.setpointButton.setCheckable(False)
                self.toggleConnectionsSig.emit(False)

        if not write_params == self.tuning_parameters:
            self.tuning_parameters = write_params
            self.set_tuning_parameters()

    def set_tuning_parameters(self):
        self.tuning_parameter_combo.clear()
        items = []
        for key,val in self.tuning_parameters.items():
            for item in val:
                items.append(str(key) + ': ' + str(item) )
        self.tuning_parameter_combo.addItems(items)

    def set_on_setpoint(self,on_setpoint):
        if on_setpoint:
            self.setpoint_reached.setText('Setpoint reached.')
        else:
            self.setpoint_reached.setText('Going to setpoint...')

    def set_setpoint_value(self,val):
        self.setpoint_value.setText(val)

    def updateProgress(self, val):
        self.progressBar.setValue(1000*val)
