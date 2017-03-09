from PyQt4 import QtCore, QtGui
from picbutton import PicButton, PicSpinBox
import numpy as np
from spin import Spin
import pyqtgraph as pg
from collections import OrderedDict



def recall_old_scan(self,ranges):
    self.remove_all()
    for rng in ranges:
        self.add()
        self.startSpins[-1].setText(str(rng[0]))
        self.stopSpins[-1].setText(str(rng[1]))
        self.steps[-1].setValue(rng[2])

        self.timeEdit.setValue(rng[3])

    self.updateLabels()


def advanced(self):
    info, ok = AdvancedDialog.getInfo()
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


class AdvancedDialog(QtGui.QDialog):
    def __init__(self, parent = None):
        super(AdvancedDialog, self).__init__(parent)

        self.layout = QtGui.QGridLayout(self)

        self.sim = False

        self.fromSimWidget = FromSimWidget()
        self.layout.addWidget(self.fromSimWidget,1,0,1,5)

        spacer = QtGui.QSpacerItem(20,40,QtGui.QSizePolicy.Minimum,QtGui.QSizePolicy.Expanding)
        self.layout.addItem(spacer,1,1,1,5)

        # OK and Cancel buttons
        buttons = QtGui.QDialogButtonBox(
            QtGui.QDialogButtonBox.Ok | QtGui.QDialogButtonBox.Cancel,
            QtCore.Qt.Horizontal, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        self.layout.addWidget(buttons)


    # get current date and time from the dialog
    def info(self):
        return self.fromSimWidget.dist.value(), self.fromSimWidget.s1.value(), self.fromSimWidget.s2.value()

    @staticmethod
    def getInfo(parent = None):
        dialog = AdvancedDialog(parent)
        result = dialog.exec_()
        info = dialog.info()
        return (info, result == QtGui.QDialog.Accepted)

class FromSimWidget(QtGui.QWidget):
    def __init__(self):
        super(FromSimWidget,self).__init__()
        self.layout = QtGui.QGridLayout(self)

        self.layout.addWidget(QtGui.QLabel('Range around peak:'),1,0)
        self.dist = pg.SpinBox(value=50*10**6,bouns = (0,10**10),
                               suffix = 'Hz', siPrefix = True,
                               step = 10**6, minstep = 10**7)
        self.layout.addWidget(self.dist,1,1)

        self.layout.addWidget(QtGui.QLabel('Scan speed on peak:'),2,0)
        self.s1 = pg.SpinBox(value=10**6,bouns = (0,10**10),
                               suffix = 'Hz/step', siPrefix = True,
                               step = 10**5, minstep = 10**5)
        self.layout.addWidget(self.s1,2,1)

        self.layout.addWidget(QtGui.QLabel('Scan speed between peaks:'),3,0)
        self.s2 = pg.SpinBox(value=50*10**6,bouns = (0,10**10),
                               suffix = 'Hz/step', siPrefix = True,
                               step = 10**5, minstep = 10**5)
        self.layout.addWidget(self.s2,3,1)


class PrevScanWidget(QtGui.QWidget):
    update_mass_selector_sig = QtCore.pyqtSignal()
    range_request_sig = QtCore.pyqtSignal(list)
    new_scan_range_chosen_sig = QtCore.pyqtSignal(list)
    def __init__(self):
        super(PrevScanWidget,self).__init__()

        self.layout = QtGui.QGridLayout(self)

        self.update_mass_selector_sig.connect(self.update_mass_selector)
        self.layout.addWidget(QtGui.QLabel('Mass:'),0,0)
        self.mass_selector = QtGui.QComboBox()
        self.mass_selector.currentIndexChanged.connect(self.update_scan_selector)
        self.layout.addWidget(self.mass_selector,0,1)
        
        self.layout.addWidget(QtGui.QLabel('Scans:'),1,0)
        self.scan_selector = QtGui.QWidget()
        self.scan_layout = QtGui.QGridLayout(self.scan_selector)
        self.layout.addWidget(self.scan_selector,1,1)
        self.scan_mass = {}
        self.masses_list = []

        self.ranges_layout = QtGui.QGridLayout()
        self.layout.addLayout(self.ranges_layout, 2,0,1,2)

        self.grab_button = QtGui.QPushButton('Grab')
        self.grab_button.setDisabled(True)
        self.grab_button.clicked.connect(self.grab_ranges)
        self.layout.addWidget(self.grab_button,3,0,1,1)

    def update_scan_selector(self):
        for i in reversed(range(self.scan_layout.count())): 
            self.scan_layout.itemAt(i).widget().setParent(None)

        mass = self.mass_selector.currentText()
        scans = self.scan_mass[mass]
        self.scan_checks = {}
        i = 0
        for scan in scans:
            if not scan == -1.0:
                self.scan_checks[scan]=QtGui.QCheckBox(str(scan))
                self.scan_checks[scan].stateChanged.connect(self.emit_request)
                self.scan_layout.addWidget(self.scan_checks[scan],i//10,i%10)
                i=i+1

    def update_mass_selector(self):
        masses_list = sorted(self.scan_mass.keys())
        if not masses_list == self.masses_list:
            self.mass_selector.clear()
            self.mass_selector.addItems([str(m) for m in masses_list])
            self.masses_list = masses_list

    def emit_request(self):
        to_request = []
        for scan, check in self.scan_checks.items():
            if check.isChecked():
                to_request.append(scan)

        self.range_request_sig.emit(to_request)

    def update_ranges(self, track, params):
        self.scan_ranges = params['ranges']

        for i in reversed(range(self.ranges_layout.count())): 
            self.ranges_layout.itemAt(i).widget().setParent(None)

        if len(self.scan_ranges) > 0:
            self.grab_button.setEnabled(True)
        else:
            self.grab_button.setDisabled(True)

        row = 0
        for s,rs in self.scan_ranges.items():
            for i,r in enumerate(rs):
                self.ranges_layout.addWidget(QtGui.QLabel('Scan {} range {}:'.format(s,i)), row, 0, 1, 1)

                value1 = r[1] - r[0]
                value1 = value1 / r[2]
                value1 = value1 * 30000

                value2 = r[2]*r[3]

                text = 'From {} to {} in {} steps of {}s, so {} MHz/step, {}s total.'.format(r[0],r[1],r[2],r[3],value1,value2)
                label = QtGui.QLabel(text)
                self.ranges_layout.addWidget(label, row, 1, 1, 1)
                row += 1

    def grab_ranges(self):
        ranges = list(self.scan_ranges.values())
        ranges = [r for rng in ranges for r in rng]
        ranges = sorted(ranges, key = lambda x: x[0])

        self.new_scan_range_chosen_sig.emit(ranges)

        plot = pg.plot()
        x0 = 0
        for rng in ranges:
            x = np.arange(rng[2]) + x0
            y = np.linspace(rng[0],rng[1],rng[2])
            plot.addItem(pg.PlotCurveItem(x,y))
            x0+=rng[2]