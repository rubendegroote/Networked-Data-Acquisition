from PyQt4 import QtCore,QtGui
from picbutton import PicButton,PicSpinBox
import numpy as np

class ScannerWidget(QtGui.QWidget):
    scanInfo = QtCore.Signal(tuple)
    def __init__(self):
        super(ScannerWidget,self).__init__()
        self.layout = QtGui.QGridLayout(self)

        self.progressBar = QtGui.QProgressBar()
        self.progressBar.setMinimum(0)
        self.progressBar.setMaximum(1000)
        self.layout.addWidget(self.progressBar,0,0,1,4)

        self.parCombo = QtGui.QComboBox()
        self.layout.addWidget(self.parCombo,1,0,1,1)
        self.parCombo.addItems(['WL'])

        self.startEdit = QtGui.QLineEdit("0")
        self.layout.addWidget(self.startEdit,1,1,1,1)
        self.stepsBox = PicSpinBox(iconName = 'step.png',step = 1, 
            integer=True)
        self.layout.addWidget(self.stepsBox,1,2,1,1)
        self.stopEdit = QtGui.QLineEdit("1")
        self.layout.addWidget(self.stopEdit,1,3,1,1)

        self.controlButton = PicButton('new',checkable = False,size = 100)
        self.state = 'NEW'
        self.controlButton.clicked.connect(self.changeControl)
        self.layout.addWidget(self.controlButton,0,5,1,1)

        self.modeCombo = QtGui.QComboBox()
        self.modeCombo.setToolTip('Choose the criterium to be used for deciding\
 the length of a step in a scan. <b>Time</b>: wait for a specified time, \
 <b>Triggers</b>: wait for a specified number of triggers,<b>Supercycle</b>:\
 wait for a specified number of supercycles, <b>Proton Pulse</b>:\
 wait for a specified number of proton pulses.')
        self.modes = ['Time','Triggers', 'Supercycle', 'Proton Pulse']
        self.modeCombo.addItems(self.modes)
        self.modeCombo.setMaximumWidth(120)
        self.layout.addWidget(self.modeCombo,0,4,1,1)

        self.timeEdit = PicSpinBox(value = 10,step = 1, integer=True, 
                    iconName = 'time')
        self.timeEdit.setToolTip('Use this to specify the waiting\
 information per step for the chosen criterium (see combobox above).')
        self.timeEdit.setMaximumWidth(120)
        self.layout.addWidget(self.timeEdit,1,4,1,1)

    def updateProgress(self,val):
        self.progressBar.setValue(10*val)

    def makeScan(self):
        par = self.parCombo.currentText()

        start = float(self.startEdit.text())
        stop = float(self.stopEdit.text())
        steps = float(self.stepsBox.text())
        rng = np.linspace(start,stop,steps)
            
        dt = float(self.timeEdit.text())

        self.scanInfo.emit((par,rng,dt))

    def changeControl(self):
        if self.state == "NEW":
            self.state = "START"
            self.controlButton.setIcon('start.png')
            self.controlButton.setToolTip('Click here to initialize start the capture.')

        elif self.state == "START":
            self.state = "STOP"
            self.makeScan()
            self.controlButton.setIcon('stop.png')
            self.controlButton.setToolTip('Click here to stop the current capture.')

        elif self.state == "STOP":
            self.state = "NEW"    
            self.controlButton.setIcon('new.png')
            self.controlButton.setToolTip('Click here to initialize a new capture.')