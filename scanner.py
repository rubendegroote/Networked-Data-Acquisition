from PyQt4 import QtCore, QtGui
from picbutton import PicButton, PicSpinBox
import numpy as np


class ScannerWidget(QtGui.QWidget):

    scanInfoSig = QtCore.Signal(dict)
    setPointSig = QtCore.Signal(dict)
    stopScanSig = QtCore.Signal(bool)
    toggleConnectionsSig = QtCore.Signal(bool)

    def __init__(self):
        super(ScannerWidget, self).__init__()
        self.layout = QtGui.QGridLayout(self)

        self.scanningLabel = QtGui.QLabel('Scanning controls')
        self.layout.addWidget(self.scanningLabel, 0, 0, 1, 4)

        self.progressBar = QtGui.QProgressBar()
        self.progressBar.setMinimum(0)
        self.progressBar.setMaximum(1000)
        self.layout.addWidget(self.progressBar, 1, 0, 1, 4)

        self.parCombo = QtGui.QComboBox()
        self.pars = {}
        # self.layout.addWidget(self.parCombo, 2, 0, 1, 1)

        self.startEdit = QtGui.QLineEdit("15407.3")
        self.layout.addWidget(self.startEdit, 2, 1, 1, 1)
        self.stepsBox = PicSpinBox(iconName='step.png',
                                   step=1,
                                   value=10,
                                   integer=True)
        self.layout.addWidget(self.stepsBox, 2, 2, 1, 1)
        self.stopEdit = QtGui.QLineEdit("15407.35")
        self.layout.addWidget(self.stopEdit, 2, 3, 1, 1)

        self.controlButton = PicButton('start',
                                       checkable=False,
                                       size=100)
        self.state = 'START'
        self.controlButton.clicked.connect(self.control)
        self.layout.addWidget(self.controlButton, 1, 5, 2, 1)

        self.modeCombo = QtGui.QComboBox()
        self.modeCombo.setToolTip('Choose the criterium to be used for deciding\
 the length of a step in a scan. <b>Time</b>: wait for a specified time, \
 <b>Triggers</b>: wait for a specified number of triggers,<b>Supercycle</b>:\
 wait for a specified number of supercycles, <b>Proton Pulse</b>:\
 wait for a specified number of proton pulses.')
        self.modes = ['Time', 'Triggers', 'Supercycle', 'Proton Pulse']
        self.modeCombo.addItems(self.modes)
        self.modeCombo.setMaximumWidth(120)
        self.layout.addWidget(self.modeCombo, 1, 4, 1, 1)

        self.timeEdit = PicSpinBox(value=10,
                                   step=1,
                                   integer=False,
                                   iconName='time')
        self.timeEdit.setToolTip('Use this to specify the waiting\
 information per step for the chosen criterium (see combobox above).')
        self.timeEdit.setMaximumWidth(120)
        self.layout.addWidget(self.timeEdit, 2, 4, 1, 1)

        self.setpointlabel = QtGui.QLabel('Setpoint controls')
        self.layout.addWidget(self.setpointlabel, 5, 0, 1, 1)

        self.setpointCombo = QtGui.QComboBox()
        # self.layout.addWidget(self.setpointCombo, 6, 0, 1, 1)
        self.setpointEdit = QtGui.QLineEdit('15407.31')
        self.layout.addWidget(self.setpointEdit, 6, 1, 1, 4)

        self.setpointButton = PicButton('manual',
                                        checkable=False,
                                        size=100)
        self.layout.addWidget(self.setpointButton, 6, 5, 1, 1)
        self.setpointButton.clicked.connect(self.makeSetpoint)

        self.repeatLabel = QtGui.QLabel('Repeats')
        self.layout.addWidget(self.repeatLabel, 3, 1, 1, 1)
        self.repeatBox = QtGui.QLineEdit("1")
        self.layout.addWidget(self.repeatBox, 3, 2, 1, 3)

        self.scanLabel = QtGui.QLabel('Scan number')
        self.layout.addWidget(self.scanLabel, 4, 1, 1, 1)
        self.scanNumberLabel = QtGui.QLabel(str(-1))
        self.layout.addWidget(self.scanNumberLabel, 4, 2, 1, 1)

    def updateScanNumber(self, scan_number):
        self.scanNumberLabel.setText(str(scan_number))

    def control(self):
        if self.state == "START":
            self.makeScan()
            self.state = "STOP"

        elif self.state == "STOP":
            self.stopScan()
            self.state = "START"

    def makeScan(self):
        artist = ['M2']
        parameter = ['wavelength']

        start = float(self.startEdit.text())
        stop = float(self.stopEdit.text())
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

        dt = [float(self.timeEdit.text())]

        self.scanInfoSig.emit({'artist':artist,
                               'scan_parameter':parameter,
                               'scan_array':rng,
                               'time_per_step':dt})

    def makeSetpoint(self):
        artist = ['M2']
        parameter = ['wavelength']
        value = [float(self.setpointEdit.text())]

        self.setPointSig.emit({'artist':artist,
                               'parameter':parameter,
                               'setpoint': value})

    def stopScan(self):
        self.stopScanSig.emit(True)

    def update(self, track, info):
        origin, track_id = track[-1]
        scanning,on_setpoint = info['scanning'],info['on_setpoint']
        scan_number, progress = info['scan_number'][0],info['progress']

        if len(progress) > 0:
            scanning = any(scanning.values())
            progress = max(progress.values())
            on_setpoint = any(on_setpoint.values())

            self.updateScanNumber(scan_number)
            self.updateProgress(progress)
            if not scanning:
                self.state = "START"
                self.controlButton.setIcon('start.png')
                self.controlButton.setToolTip('Click here to start a new capture.')
                self.setpointButton.setCheckable(True)
                self.toggleConnectionsSig.emit(True)

            else:
                self.state = "STOP"
                self.controlButton.setIcon('stop.png')
                self.controlButton.setToolTip(
                    'Click here to stop the current capture.')
                self.setpointButton.setCheckable(False)
                self.toggleConnectionsSig.emit(False)

        # try:
        #     form = {}
        #     for k, v in artists.items():
        #         if v[0]:
        #             form[k] = format[k]
        #     self.setParCombo(form)
        # except Exception as e:
        #     pass

    def setParCombo(self, format):
        if self.pars == format:
            return

        self.pars = format
        items = []
        for key, val in self.pars.items():
            for v in val:
                if 'time' not in v and 'scan' not in v:
                    items.append(key + ': ' + v)

        curPar = int(self.parCombo.currentIndex())
        if curPar == -1:
            curPar = 0
        self.parCombo.clear()
        self.parCombo.addItems(items)
        self.parCombo.setCurrentIndex(curPar)

        curPar = int(self.setpointCombo.currentIndex())
        if curPar == -1:
            curPar = 0
        self.setpointCombo.clear()
        self.setpointCombo.addItems(items)
        self.setpointCombo.setCurrentIndex(curPar)

    def updateProgress(self, val):
        self.progressBar.setValue(1000*val)
