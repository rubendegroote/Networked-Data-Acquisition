from PyQt4 import QtCore, QtGui
from picbutton import PicButton, PicSpinBox
import numpy as np
from spin import Spin
import pyqtgraph as pg

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

        self.scanningLabel = QtGui.QLabel('<font size="4"><b>Scanning<\b><\font>')
        self.layout.addWidget(self.scanningLabel, 2, 0, 1, 4)

        self.progressBar = QtGui.QProgressBar()
        self.progressBar.setMinimum(0)
        self.progressBar.setMaximum(1000)
        self.layout.addWidget(self.progressBar, 3, 0, 1, 4)

        self.scan_definer = ScanDefiner()
        self.layout.addWidget(self.scan_definer,4,0,1,4)

        self.controlButton = QtGui.QPushButton('Start!')
        self.state = 'START'
        self.controlButton.clicked.connect(self.control)
        self.layout.addWidget(self.controlButton, 5, 0, 1, 4)


        self.setpointlabel = QtGui.QLabel('<font size="4"><b>Setpoint<\b><\font>')
        self.layout.addWidget(self.setpointlabel, 7, 0, 1, 1)

        self.setPointSpin = Spin(11836.0000,0,10**5)
        self.layout.addWidget(self.setPointSpin, 8, 0, 1, 2)

        self.setpointButton = PicButton('manual',
                                        checkable=False,
                                        size=40)
        self.layout.addWidget(self.setpointButton, 8, 2, 1, 1)
        self.setpointButton.clicked.connect(self.makeSetpoint)

        self.setpoint_reached = QtGui.QLabel()
        self.layout.addWidget(self.setpoint_reached, 8, 3)

    def control(self):
        if self.state == "START":
            scan_range, dt, scan_summary = self.scan_definer.makeScan()

            parameter = self.tuning_parameter_combo.currentText()
            self.scan_device,parameter = parameter.split(': ')

            self.scanInfoSig.emit({'device':self.scan_device,
                               'scan_parameter':parameter,
                               'scan_array':scan_range,
                               'scan_summary':scan_summary,
                               'time_per_step':[dt]})

            self.state = "STOP"

        elif self.state == "STOP":
            self.stopScan()
            # self.state = "CALIBRATE"

        # elif self.state == "CALIBRATE":
            # self.send_calibrate()
            self.state = "START"


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
        scanning,calibrated,on_setpoint,progress,write_params = (info['scanning'],
                                                   info['calibrated'],
                                                   info['on_setpoint'],
                                                   info['progress'],
                                                   info['write_params'])
        if len(progress) > 0:
            scanning = any(scanning.values())
            calibrated = any(calibrated.values())
            progress = max(progress.values())

            self.updateProgress(progress)
            if not scanning:
                # if calibrated:
                    self.state = "START"
                    self.controlButton.setText('Start!')
                    self.controlButton.setToolTip('Click here to start a new scan.')
                    self.toggleConnectionsSig.emit(True)
                # else:
                #     self.state = "CALIBRATE"
                #     self.controlButton.setIcon('calibrate.png')
                #     self.controlButton.setToolTip('Click here to calibrate the wavemeter.')
                #     self.toggleConnectionsSig.emit(True)

            else:
                self.state = "STOP"
                self.controlButton.setText('Stop')
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

class ScanDefiner(QtGui.QWidget):
    def __init__(self):
        super(ScanDefiner, self).__init__()
        
        self.layout = QtGui.QGridLayout(self)
        self.points_layout = QtGui.QGridLayout()
        self.layout.addLayout(self.points_layout,0,0,1,4)

        self.adds = 0

        self.startSpins = []
        self.stopSpins = []
        self.steps = []
        self.removeButtons = []
        self.freqLabels = []

        self.add_button = QtGui.QPushButton('Add')
        self.layout.addWidget(self.add_button, 3, 3, 1, 1)
        self.add_button.clicked.connect(self.add)

        self.load_button = QtGui.QPushButton('From peak estimates...')
        self.layout.addWidget(self.load_button, 3, 0, 1, 1)
        self.load_button.clicked.connect(self.load)

        self.fromPeakInfoLabel = QtGui.QLabel()
        self.layout.addWidget(self.fromPeakInfoLabel,3,1,1,1)

        self.total_freq = QtGui.QLabel()
        self.total_freq.setMinimumWidth(120)
        self.layout.addWidget(self.total_freq, 6, 0, 1, 1)

        self.total_time = QtGui.QLabel()
        self.total_time.setMinimumWidth(120)
        self.layout.addWidget(self.total_time, 6, 2, 1, 1)


        self.layout.addWidget(QtGui.QLabel('Repeats: '), 5, 0, 1, 1)
        self.repeatBox = QtGui.QLineEdit("1")
        self.repeatBox.textChanged.connect(self.updateLabels)
        self.layout.addWidget(self.repeatBox, 5, 1, 1, 1)

        self.layout.addWidget(QtGui.QLabel('Time/step: '), 5, 2, 1, 1)
        self.timeEdit = PicSpinBox(value=10,
                                   step=1,
                                   integer=False,
                                   iconName='time')
        self.timeEdit.sigValueChanged.connect(self.updateLabels)
        self.timeEdit.setToolTip('Use this to specify the waiting\
 information per step for the chosen criterium (see combobox above).')
        self.layout.addWidget(self.timeEdit, 5, 3, 1, 1)

        self.reverse_button = QtGui.QPushButton('Reverse')
        self.layout.addWidget(self.reverse_button, 7, 0, 1, 1)
        self.reverse_button.clicked.connect(self.reverse_scan)

        self.add()

    def reverse_scan(self):
        for startSpin,stopSpin in zip(self.startSpins,self.stopSpins):
            start = startSpin.text()
            stop = stopSpin.text()

            startSpin.setText(stop)
            stopSpin.setText(start)

        starts = [s.text() for s in self.startSpins]
        for i,start in enumerate(reversed(starts)):
            self.startSpins[i].setText(start)

        stops = [s.text() for s in self.stopSpins]
        for i,stop in enumerate(reversed(stops)):
            self.stopSpins[i].setText(stop)

        steps = [s.text() for s in self.steps]
        for i,step in enumerate(reversed(steps)):
            self.steps[i].setValue(step)

    def makeScan(self):
        dt = float(self.timeEdit.text())

        total_range = np.array([])
        summary = []
        for start,step,stop in zip(self.startSpins,self.steps,self.stopSpins):
            start = float(start.value)
            stop = float(stop.value)
            steps = int(step.text())
            rng = np.linspace(start,stop,steps)

            total_range = np.concatenate((total_range,rng))

            summary.append([start,stop,steps,dt])

        times = int(self.repeatBox.text())
        if times == 0:
            times = 1

        newRng = total_range
        if times > 1:
            for t in range(times-1):
                if t%2==0:
                    newRng = np.concatenate((newRng,rng[::-1]))
                else:
                    newRng = np.concatenate((newRng,rng))
        rng = list(newRng)


        return rng,dt,summary

    def add(self):
        self.adds += 1
        try:
            default = float(self.stopSpins[-1].value)
        except:
            default = 13378.00

        startSpin = Spin(default,0,10**5)
        startSpin.sigValueChanging.connect(self.updateLabels)
        self.startSpins.append(startSpin)
        self.points_layout.addWidget(startSpin, self.adds, 0, 1, 1)
        
        stepsBox = PicSpinBox(iconName='step.png',
                                   step=1,
                                   value=10,
                                   integer=True)
        stepsBox.sigValueChanged.connect(self.updateLabels)
        self.steps.append(stepsBox)
        self.points_layout.addWidget(stepsBox,self.adds,1)

        stopSpin = Spin(default,0,10**5)
        stopSpin.sigValueChanging.connect(self.updateLabels)
        self.stopSpins.append(stopSpin)
        self.points_layout.addWidget(stopSpin, self.adds, 2, 1, 1)

        self.freqLabels.append(QtGui.QLabel())
        self.points_layout.addWidget(self.freqLabels[-1], self.adds, 3, 1, 1)

        self.updateLabels()

        removeButton = QtGui.QPushButton('Remove')
        removeButton.clicked.connect(self.remove)
        self.removeButtons.append(removeButton)
        self.points_layout.addWidget(removeButton, self.adds, 4, 1, 1)

    def remove(self):
        index = self.removeButtons.index(self.sender())
        self.remove_by_index(index)

    def remove_by_index(self,index):
        startSpin = self.startSpins[index]
        self.startSpins.remove(startSpin)
        startSpin.deleteLater()

        step = self.steps[index]
        self.steps.remove(step)
        step.deleteLater()

        stopSpin = self.stopSpins[index]
        self.stopSpins.remove(stopSpin)
        stopSpin.deleteLater()

        freqLabel = self.freqLabels[index]
        self.freqLabels.remove(freqLabel)
        freqLabel.deleteLater()

        button = self.removeButtons[index]
        button.deleteLater()
        self.removeButtons.remove(button)

    def load(self):
        info, ok = PeakScanDialog.getInfo()
        if not ok:
            return

        dist, s1, s2 = info
        s1 = s1 / 2.998 / 10**10
        s2 = s2 / 2.998 / 10**10
        dist = dist / 2.998 / 10**10

        path = "\\\\cern.ch\\dfs\\Users\\c\\CRIS\\Documents\\HFS Simulator\\hfs_peaks.txt"
        with open(path,'r') as f:
            data = np.loadtxt(f,dtype=bytes)
        isotope = str(data[0].decode('utf-8'))
        voltage = str(data[1].decode('utf-8'))

        self.fromPeakInfoLabel.setText('{} at {} kV'.format(isotope,voltage))

        peaks = [float(d) for d in data[2:]]

        peaks = sorted([float(p) for p in peaks if not p == ''])

        ## remove existing stuf
        for i in reversed(range(len(self.removeButtons))):
            self.remove_by_index(i)

        starts = []
        stops = []
        i = 0
        while i < len(peaks):
            peak = peaks[i]
            left = peak - dist
            right = peak + dist
            starts.append(left)
            for j,peak2 in enumerate(peaks[i+1:]):
                left2 = peak2-dist
                right2 = peak2+dist
                if right >= left2:
                    pass
                else:
                    stops.append(right)
                    i = i+j+1
                    break
            else:
                try:
                    stops.append(right2)
                except UnboundLocalError:
                    stops.append(right)
                break

        for start,stop in zip(starts,stops):
            self.add()
            self.startSpins[-1].setText(round(start,5))
            self.stopSpins[-1].setText(round(stop,5))
            steps =  max(1,int( (stop-start) / s1) )
            self.steps[-1].setValue(steps)

            try:
                start2 = starts[starts.index(start)+1]
                self.add()
                self.startSpins[-1].setText(round(stop,5))
                self.stopSpins[-1].setText(round(start2,5))
                steps = max(1,int(np.ceil( (start2-stop) / s2) ) )
                self.steps[-1].setValue(steps)
            except:
                pass

        self.updateLabels()

    def updateLabels(self):
        for i, label in enumerate(self.freqLabels):
            value = self.stopSpins[i].value - self.startSpins[i].value
            value = value / int(self.steps[i].text())
            value = value * 30000
            label.setText('{:.1f} MHz/step'.format(value))        

        try:
            total_freq = self.stopSpins[-1].value - self.startSpins[0].value
            total_freq = total_freq * 30000
            if total_freq < 1000:
                self.total_freq.setText('Total frequency: {:.0f} MHz'.format(total_freq))
            else:
                total_freq = total_freq / 1000
                self.total_freq.setText('Total frequency: {:.1f} GHz'.format(total_freq))

            total_time = sum([int(s.text()) for s in self.steps]) * float(self.timeEdit.text())
            total_time = total_time * int(self.repeatBox.text())
            if total_time > 3600:
                self.total_time.setText('Total time: >{:.0f} h'.format(total_time/3600))
            elif total_time > 60:
                self.total_time.setText('Total time: >{:.0f} min'.format(total_time/60))
            else:
                self.total_time.setText('Total time: >{:.0f} s'.format(total_time))


        except:
            pass

class PeakScanDialog(QtGui.QDialog):
    def __init__(self, parent = None):
        super(PeakScanDialog, self).__init__(parent)

        self.layout = QtGui.QGridLayout(self)

        self.layout.addWidget(QtGui.QLabel('Range around peak:'),0,0)
        self.dist = pg.SpinBox(value=50*10**6,bouns = (0,10**10),
                               suffix = 'Hz', siPrefix = True,
                               step = 10**6, minstep = 10**7)
        self.layout.addWidget(self.dist,0,1)

        self.layout.addWidget(QtGui.QLabel('Scan speed on peak:'),1,0)
        self.s1 = pg.SpinBox(value=10**6,bouns = (0,10**10),
                               suffix = 'Hz/step', siPrefix = True,
                               step = 10**5, minstep = 10**5)
        self.layout.addWidget(self.s1,1,1)

        self.layout.addWidget(QtGui.QLabel('Scan speed between peaks:'),2,0)
        self.s2 = pg.SpinBox(value=50*10**6,bouns = (0,10**10),
                               suffix = 'Hz/step', siPrefix = True,
                               step = 10**5, minstep = 10**5)
        self.layout.addWidget(self.s2,2,1)

        # OK and Cancel buttons
        buttons = QtGui.QDialogButtonBox(
            QtGui.QDialogButtonBox.Ok | QtGui.QDialogButtonBox.Cancel,
            QtCore.Qt.Horizontal, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        self.layout.addWidget(buttons)

    # get current date and time from the dialog
    def info(self):
        return self.dist.value(), self.s1.value(), self.s2.value()

    # static method to create the dialog and return (date, time, accepted)
    @staticmethod
    def getInfo(parent = None):
        dialog = PeakScanDialog(parent)
        result = dialog.exec_()
        info = dialog.info()
        return (info, result == QtGui.QDialog.Accepted)