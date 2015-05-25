from PyQt4 import QtCore, QtGui
from picbutton import PicButton, PicSpinBox
import numpy as np


class ScannerWidget(QtGui.QWidget):

    scanInfoSig = QtCore.Signal(tuple)
    setPointSig = QtCore.Signal(tuple)
    stopScanSig = QtCore.Signal(bool)

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
        self.layout.addWidget(self.parCombo, 2, 0, 1, 1)

        self.startEdit = QtGui.QLineEdit("0")
        self.layout.addWidget(self.startEdit, 2, 1, 1, 1)
        self.stepsBox = PicSpinBox(iconName='step.png',
                                   step=1,
                                   integer=True)
        self.layout.addWidget(self.stepsBox, 2, 2, 1, 1)
        self.stopEdit = QtGui.QLineEdit("1")
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
                                   integer=True,
                                   iconName='time')
        self.timeEdit.setToolTip('Use this to specify the waiting\
 information per step for the chosen criterium (see combobox above).')
        self.timeEdit.setMaximumWidth(120)
        self.layout.addWidget(self.timeEdit, 2, 4, 1, 1)

        self.setpointlabel = QtGui.QLabel('Setpoint controls')
        self.layout.addWidget(self.setpointlabel, 3, 0, 1, 1)

        self.setpointCombo = QtGui.QComboBox()
        self.layout.addWidget(self.setpointCombo, 4, 0, 1, 1)
        self.setpointEdit = QtGui.QLineEdit('0')
        self.layout.addWidget(self.setpointEdit, 4, 1, 1, 4)

        self.setpointButton = PicButton('manual',
                                        checkable=False,
                                        size=100)
        self.layout.addWidget(self.setpointButton, 4, 5, 1, 1)
        self.setpointButton.clicked.connect(self.makeSetpoint)

    def control(self):
        if self.state == "START":
            self.makeScan()
        elif self.state == "STOP":
            self.stopScan()

    def changeControl(self):
        # if self.state == "NEW":
        #     self.state = "START"
        #     self.controlButton.setIcon('start.png')
        #     self.controlButton.setToolTip('Click here to initialize start the capture.')

        if self.state == "START":
            self.state = "STOP"
            self.controlButton.setIcon('stop.png')
            self.controlButton.setToolTip(
                'Click here to stop the current capture.')
            self.setpointButton.setCheckable(False)

        elif self.state == "STOP":
            self.state = "START"
            self.controlButton.setIcon('start.png')
            self.controlButton.setToolTip('Click here to start a new capture.')
            self.setpointButton.setCheckable(True)

    def makeScan(self):
        par = self.parCombo.currentText()

        start = float(self.startEdit.text())
        stop = float(self.stopEdit.text())
        steps = float(self.stepsBox.text())
        rng = np.linspace(start, stop, steps)

        dt = float(self.timeEdit.text())

        self.scanInfoSig.emit((par, rng, dt))

    def makeSetpoint(self):
        par = self.setpointCombo.currentText()
        value = float(self.setpointEdit.text())

        self.setPointSig.emit((par, value, 0.050))

    def stopScan(self):
        self.stopScanSig.emit(True)

    def update(self, info):
        format, progress, artists = info
        self.updateProgress(progress)
        try:
            form = {}
            for k, v in artists.items():
                if v[0]:
                    form[k] = format[k]
            self.setParCombo(form)
        except:
            pass

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
        self.progressBar.setValue(10 * val)
