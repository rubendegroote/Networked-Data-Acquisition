from PyQt4 import QtCore, QtGui
from picbutton import PicButton, PicSpinBox
import numpy as np
from spin import Spin
import pyqtgraph as pg
from collections import OrderedDict
 
class ScannerWidget(QtGui.QWidget):
    scanInfoSig = QtCore.pyqtSignal(dict)
    setPointSig = QtCore.pyqtSignal(dict)
    stopScanSig = QtCore.pyqtSignal(bool)
    range_request_sig = QtCore.pyqtSignal(list)
    def __init__(self,*args,**kwargs):
        super(ScannerWidget,self).__init__()
 
        self.widgets = []
        self.state = 0
 
        self.layout = QtGui.QGridLayout(self)
 
        self.stacked = QtGui.QStackedWidget()
        self.layout.addWidget(self.stacked,0,0)
 
        self.initializer = Initializer()
        self.widgets.append(self.initializer)
        self.stacked.addWidget(self.initializer)
 
        self.configurator = Configurator()
        self.widgets.append(self.configurator)
        self.stacked.addWidget(self.configurator)
 
        self.scanner = Scanner()
        self.scanner.scanInfoSig.connect(self.emit_scaninfo)
        self.scanner.stopScanSig.connect(self.emit_stopscan)
        self.scanner.setPointSig.connect(self.emit_setpoint)
 
        self.widgets.append(self.scanner)
        self.stacked.addWidget(self.scanner)
 
        self.fromSimWidget = FromSimWidget()
        self.widgets.append(self.fromSimWidget)
        self.stacked.addWidget(self.fromSimWidget)
 
        self.fromOldWidget = FromOldWidget()
        self.fromOldWidget.range_request_sig.connect(self.emit_range_request)
        self.widgets.append(self.fromOldWidget)
        self.stacked.addWidget(self.fromOldWidget)
 
        self.from_sim = False
        self.from_old = False
 
        self.back = QtGui.QPushButton('Back')
        self.back.setEnabled(True)
        self.back.setMaximumWidth(100)
        self.back.clicked.connect(self.go_back)
        self.layout.addWidget(self.back,1,1)
 
        self.next = QtGui.QPushButton('Next')
        self.next.setMaximumWidth(100)
        self.next.clicked.connect(self.go_to_next)
        self.layout.addWidget(self.next,1,2)
 
    def go_back(self):
        if self.state == 0:
            return
 
        self.state -= 1
        self.state = self.state%3
        self.from_sim = False
        self.from_old = False
        self.change_state()
 
    def go_to_next(self):
        if self.state == 2:
            if self.from_sim or self.from_old:
                pass
            else:
                self.state += 1
        else:
            self.state += 1
        self.state = self.state%3
 
        self.change_state()
 
    def change_state(self):
        if self.state == 0:
            self.back.setDisabled(True)
        else:
            self.back.setEnabled(True)
 
        if self.state < 2:
            self.stacked.setCurrentWidget(self.widgets[self.state])
        else:
            state = self.state + self.configurator.options.currentIndex()
            if state == 2:
                self.from_sim = False
                self.from_sim = False
                self.stacked.setCurrentWidget(self.widgets[state])
 
            elif state == 3:
                if self.from_sim:
                    info = self.fromSimWidget.dist.value(), self.fromSimWidget.s1.value(), self.fromSimWidget.s2.value()
                    self.scanner.from_sim(info)
                    self.stacked.setCurrentWidget(self.scanner)
 
                else:
                    self.stacked.setCurrentWidget(self.widgets[state])
                self.from_sim = True
             
            elif state == 4:
                if self.from_old:
                    self.scanner.from_old(self.fromOldWidget.ranges)
                    self.stacked.setCurrentWidget(self.scanner)
                    self.next.setText('Back to home')
 
                else:
                    self.stacked.setCurrentWidget(self.widgets[state])
 
                self.from_old = True
                 
 
    def update(self, track, info):
        origin, track_id = track[-1]
        scanning = info['scanning']
        scanning = any(scanning.values())
         
        write_params = info['write_params']
 
        self.fromOldWidget.scan_mass = info['scan_mass']
        self.fromOldWidget.update_mass_selector_sig.emit()
 
        if not write_params == self.initializer.tuning_parameters:
            self.initializer.set_tuning_parameters(write_params)
         
        self.scanner.set_state(scanning)
 
    def emit_setpoint(self,info):
        parameter = str(self.initializer.tuning_parameter_combo.currentText())
        device,parameter = parameter.split(': ')
        info['device'] = device
        info['parameter'] = parameter
        self.setPointSig.emit(info)
 
    def emit_scaninfo(self, info):
        parameter = str(self.initializer.tuning_parameter_combo.currentText())
        device,parameter = parameter.split(': ')
 
        info['device'] = device
        info['scan_parameter'] = parameter
 
        self.scanInfoSig.emit(info)
     
    def emit_stopscan(self):
        self.stopScanSig.emit(True)
 
    def emit_range_request(self,request):
        self.range_request_sig.emit(request)
 
class Initializer(QtGui.QWidget):
    def __init__(self):
        super(Initializer,self).__init__()
        self.layout = QtGui.QGridLayout(self)
 
        label = QtGui.QLabel('Choose scan parameter')
        font = QtGui.QFont("Helvetica", 16, QtGui.QFont.Bold) 
        label.setFont(font)
        self.layout.addWidget(label,0,0,1,5)
 
        self.tuning_parameter_combo = QtGui.QComboBox()
        self.tuning_parameters = {}
        self.layout.addWidget(QtGui.QLabel('Tuning parameter'), 1, 0, 1, 1)
        self.layout.addWidget(self.tuning_parameter_combo, 1, 1, 1, 1)
 
        spacer = QtGui.QSpacerItem(20,40,QtGui.QSizePolicy.Minimum,QtGui.QSizePolicy.Expanding)
        self.layout.addItem(spacer,2,0,1,5)
 
    def set_tuning_parameters(self,tuning_parameters):
        self.tuning_parameters = tuning_parameters
        self.tuning_parameter_combo.clear()
        items = []
        for key,val in self.tuning_parameters.items():
            for item in val:
                items.append(str(key) + ': ' + str(item) )
        self.tuning_parameter_combo.addItems(items)
 
class Configurator(QtGui.QWidget):
    def __init__(self):
        super(Configurator,self).__init__()
        self.layout = QtGui.QGridLayout(self)
 
        label = QtGui.QLabel('Choose scan option')
        font = QtGui.QFont("Helvetica", 16, QtGui.QFont.Bold) 
        label.setFont(font)
        self.layout.addWidget(label,0,0,1,5)
 
        self.options = QtGui.QComboBox()
        self.options.addItems(['From previous settings','From simulated settings','From old settings'])
        self.layout.addWidget(QtGui.QLabel('Scan options:'), 1, 0, 1, 1)
        self.layout.addWidget(self.options, 1, 1, 1, 1)
 
        spacer = QtGui.QSpacerItem(20,40,QtGui.QSizePolicy.Minimum,QtGui.QSizePolicy.Expanding)
        self.layout.addItem(spacer,2,0,1,5)
 
class FromSimWidget(QtGui.QWidget):
    def __init__(self):
        super(FromSimWidget,self).__init__()
        self.layout = QtGui.QGridLayout(self)
 
        label = QtGui.QLabel('Grab scan settings from simulation')
        font = QtGui.QFont("Helvetica", 16, QtGui.QFont.Bold) 
        label.setFont(font)
        self.layout.addWidget(label,0,0,1,5)
 
        self.layout.addWidget(QtGui.QLabel('Range around peak:'),1,0)
        self.dist = pg.SpinBox(value=50*10**6,bounds = (0,10**10),
                               suffix = 'Hz', siPrefix = True,
                               step = 10**6, minStep = 10**7)
        self.layout.addWidget(self.dist,1,1)
 
        self.layout.addWidget(QtGui.QLabel('Scan speed on peak:'),2,0)
        self.s1 = pg.SpinBox(value=10**6,bounds = (0,10**10),
                               suffix = 'Hz/step', siPrefix = True,
                               step = 10**5, minStep = 10**5)
        self.layout.addWidget(self.s1,2,1)
 
        self.layout.addWidget(QtGui.QLabel('Scan speed between peaks:'),3,0)
        self.s2 = pg.SpinBox(value=50*10**6,bounds = (0,10**10),
                               suffix = 'Hz/step', siPrefix = True,
                               step = 10**5, minStep = 10**5)
        self.layout.addWidget(self.s2,3,1)
 
        spacer = QtGui.QSpacerItem(20,40,QtGui.QSizePolicy.Minimum,QtGui.QSizePolicy.Expanding)
        self.layout.addItem(spacer,4,0,1,5)
 
class FromOldWidget(QtGui.QWidget):
    update_mass_selector_sig = QtCore.pyqtSignal()
    range_request_sig = QtCore.pyqtSignal(list)
    def __init__(self):
        super(FromOldWidget,self).__init__()
 
        self.layout = QtGui.QGridLayout(self)
 
        label = QtGui.QLabel('Recall previous scan settings')
        font = QtGui.QFont("Helvetica", 16, QtGui.QFont.Bold) 
        label.setFont(font)
        self.layout.addWidget(label,0,0,1,5)
 
        self.update_mass_selector_sig.connect(self.update_mass_selector)
        self.layout.addWidget(QtGui.QLabel('Mass:'),1,0)
        self.mass_selector = QtGui.QComboBox()
        self.mass_selector.currentIndexChanged.connect(self.update_scan_selector)
        self.layout.addWidget(self.mass_selector,1,1)
         
        self.layout.addWidget(QtGui.QLabel('Scans:'),2,0)
        self.scan_selector = QtGui.QWidget()
        self.scan_layout = QtGui.QGridLayout(self.scan_selector)
        self.layout.addWidget(self.scan_selector,2,1)
        self.scan_mass = {}
        self.masses_list = []
 
        self.ranges_layout = QtGui.QGridLayout()
        self.layout.addLayout(self.ranges_layout, 3,0,1,2)
 
        spacer = QtGui.QSpacerItem(20,40,QtGui.QSizePolicy.Minimum,QtGui.QSizePolicy.Expanding)
        self.layout.addItem(spacer,4,0,1,5)
 
        self.scans = []
        self.ranges = []
 
    def update_scan_selector(self):
        for i in reversed(range(self.scan_layout.count())): 
            self.scan_layout.itemAt(i).widget().setParent(None)
 
        mass = self.mass_selector.currentText()
        try:
            self.scans = self.scan_mass[mass]
        except:
            pass
        self.scan_checks = {}
        i = 0
        for scan in self.scans:
            if not scan == -1.0:
                self.scan_checks[scan] = QtGui.QCheckBox(str(scan))
                self.scan_checks[scan].stateChanged.connect(self.emit_request)
                self.scan_layout.addWidget(self.scan_checks[scan],i//10,i%10)
                i=i+1
 
    def update_mass_selector(self):
        masses_list = sorted(self.scan_mass.keys())
        if not masses_list == self.masses_list:
            self.mass_selector.clear()
            self.mass_selector.addItems([str(m) for m in masses_list])
            self.masses_list = masses_list
 
        try:
            if not self.scans == self.scan_mass[self.mass_selector.currentText()]:
                self.update_scan_selector()
        except KeyError:
            pass
    def emit_request(self):
        to_request = []
        for scan, check in self.scan_checks.items():
            if check.isChecked():
                to_request.append(scan)
 
        self.range_request_sig.emit(to_request)
 
    def update_ranges(self,track,params):
        self.scan_ranges = params['ranges']
 
        for i in reversed(range(self.ranges_layout.count())): 
            self.ranges_layout.itemAt(i).widget().setParent(None)
 
        row = 0
        for s,rs in self.scan_ranges.items():
            for i,r in enumerate(rs):
                self.ranges_layout.addWidget(QtGui.QLabel('Scan {} range {}:'.format(s,i)), row, 0, 1, 1)
 
                # value1 = r[1] - r[0]
                # value1 = value1 / r[2]
                # value1 = value1 * 30000
 
                # value2 = r[2]*r[3]
 
                text = 'From {} to {} in {} steps of {} units of {}.'.format(r[0],r[1],r[2],r[3],r[4])
                label = QtGui.QLabel(text)
                self.ranges_layout.addWidget(label, row, 1, 1, 1)
                row += 1
 
        ranges = list(self.scan_ranges.values())
        ranges = [r for rng in ranges for r in rng]
        ranges = sorted(ranges, key = lambda x: x[0])
 
        self.ranges = ranges
 
 
class Scanner(QtGui.QWidget):
    scanInfoSig = QtCore.pyqtSignal(dict)
    setPointSig = QtCore.pyqtSignal(dict)
    stopScanSig = QtCore.pyqtSignal(bool)
    def __init__(self):
        super(Scanner,self).__init__()
        self.layout = QtGui.QGridLayout(self)
        self.points_layout = QtGui.QGridLayout()
 
        label = QtGui.QLabel('Change laser setpoint')
        font = QtGui.QFont("Helvetica", 16, QtGui.QFont.Bold) 
        label.setFont(font)
        self.layout.addWidget(label,0,0,1,5)
 
        self.setPointSpin = Spin(11836.0000,0,10**5)
        self.layout.addWidget(self.setPointSpin, 1, 0)
 
        self.setpointButton = QtGui.QPushButton('Go to setpoint')
        self.layout.addWidget(self.setpointButton, 1, 1)
        self.setpointButton.clicked.connect(self.makeSetpoint)
 
        label = QtGui.QLabel('Define scan regions')
        font = QtGui.QFont("Helvetica", 16, QtGui.QFont.Bold) 
        label.setFont(font)
        self.layout.addWidget(label,2,0,1,5)
 
        self.layout.addLayout(self.points_layout,3,0,1,2)
 
        self.adds = 0
 
        self.startSpins = []
        self.stopSpins = []
        self.steps = []
        self.removeButtons = []
        self.freqLabels = []
 
        self.add_button = QtGui.QPushButton('Add')
        self.layout.addWidget(self.add_button, 5, 1, 1, 1)
        self.add_button.clicked.connect(self.add)
 
        self.reverse_button = QtGui.QPushButton('Reverse')
        self.layout.addWidget(self.reverse_button, 5, 0, 1, 1)
        self.reverse_button.clicked.connect(self.reverse_scan)
 
        self.layout.addWidget(QtGui.QLabel('Repeats: '), 6, 0, 1, 1)
        self.repeatBox = QtGui.QLineEdit("1")
        self.repeatBox.textChanged.connect(self.updateLabels)
        self.layout.addWidget(self.repeatBox, 6, 1, 1, 1)
 
        self.layout.addWidget(QtGui.QLabel('units/step: '), 7, 0, 1, 1)
        self.units_per_step_box = QtGui.QLineEdit("1")
        self.units_per_step_box.textChanged.connect(self.updateLabels)
        self.units_per_step_box.setToolTip('Use this to specify the waiting time per step.')
        self.layout.addWidget(self.units_per_step_box, 7, 1, 1, 1)
 
        self.options_box = QtGui.QComboBox()
        self.options_box.addItems(['seconds','proton pulses','proton supercycles'])
        self.layout.addWidget(self.options_box, 7, 2, 1, 1)
 
        self.controlButton = QtGui.QPushButton('Start!')
        self.state = 'START'
        self.controlButton.clicked.connect(self.control)
        self.layout.addWidget(self.controlButton, 10, 0, 2, 1)
 
        self.layout.addWidget(QtGui.QLabel('Total Frequency: '), 8, 0, 1, 1)
        self.total_freq = QtGui.QLabel()
        self.total_freq.setMinimumWidth(120)
        self.layout.addWidget(self.total_freq, 8, 1, 1, 1)
 
        self.layout.addWidget(QtGui.QLabel('Total time: '), 9, 0, 1, 1)
        self.total_time = QtGui.QLabel()
        self.total_time.setMinimumWidth(120)
        self.layout.addWidget(self.total_time, 9, 1, 1, 1)
 
        self.fromPeakInfoLabel = QtGui.QLabel()
        self.layout.addWidget(self.fromPeakInfoLabel,10,1,1,1)
 
        spacer = QtGui.QSpacerItem(20,40,QtGui.QSizePolicy.Minimum,QtGui.QSizePolicy.Expanding)
        self.layout.addItem(spacer,11,0,1,5)
 
        self.add()
     
    def makeSetpoint(self):
        value = self.setPointSpin.value
        self.setPointSig.emit({'setpoint': [value]})
         
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
        dt = float(self.units_per_step_box.text())
        mode = str(self.options_box.currentText())
 
        total_range = np.array([])
        summary = []
        for start,step,stop in zip(self.startSpins,self.steps,self.stopSpins):
            start = float(start.value)
            stop = float(stop.value)
            steps = int(step.text())
            rng = np.linspace(start,stop,steps)
 
            total_range = np.concatenate((total_range,rng))
 
            summary.append([start,stop,steps,dt,mode])
 
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
 
 
        return rng,mode,dt,summary
 
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
 
    def remove_all(self):
        ## remove existing stuf
        for i in reversed(range(len(self.removeButtons))):
            self.remove_by_index(i)
 
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
                self.total_freq.setText('{:.0f} MHz'.format(total_freq))
            else:
                total_freq = total_freq / 1000
                self.total_freq.setText('{:.1f} GHz'.format(total_freq))
 
            total_time = sum([int(s.text()) for s in self.steps]) * float(self.units_per_step_box.text())
            total_time = total_time * int(self.repeatBox.text())
            if total_time > 3600:
                self.total_time.setText('>{:.0f} h'.format(total_time/3600))
            elif total_time > 60:
                self.total_time.setText('>{:.0f} min'.format(total_time/60))
            else:
                self.total_time.setText('>{:.0f} s'.format(total_time))
 
        except:
            pass
 
    def control(self):
        if self.state == "START":
            scan_range, mode, dt, scan_summary = self.makeScan()
 
            self.scanInfoSig.emit({'scan_array':scan_range,
                                   'scan_summary':scan_summary,
                                   'units_per_step':[dt],
                                   'mode':mode})
 
            self.state = "STOP"
 
        elif self.state == "STOP":
            self.stopScan()
            self.state = "START"
 
    def stopScan(self):
        self.stopScanSig.emit(True)
 
    def set_state(self,scanning):
        if not scanning:
            self.state = "START"
            self.controlButton.setText('Start!')
            self.controlButton.setToolTip('Click here to start a new scan.')
 
        else:
            self.state = "STOP"
            self.controlButton.setText('Stop')
            self.controlButton.setToolTip(
                'Click here to stop the current scan.')
 
    def from_sim(self,info):
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
 
        self.remove_all()
 
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
 
    def from_old(self,ranges):
        self.remove_all()
        for rng in ranges:
            self.add()
            self.startSpins[-1].setText(str(rng[0]))
            self.stopSpins[-1].setText(str(rng[1]))
            self.steps[-1].setValue(rng[2])
 
            self.units_per_step_box.setText(str(rng[3]))
            index = self.options_box.findText(str(rng[4]))
            self.options_box.setCurrentIndex(index)
 
        self.updateLabels()