from PyQt4 import QtCore,QtGui
import pyqtgraph as pg
import threading as th
import asyncore
import time
import pandas as pd
import numpy as np
from multiprocessing import freeze_support
import sys
import satlas as sat
import lmfit

from scanner import ScannerWidget
from connect import ConnectionsWidget
from backend.connectors import Connector

dataserver_channel = ('PCCRIS1',5005)
fileServer_channel = ('PCCRIS1', 5006)

c = 2.998*10**8

class ScanRecaller(QtGui.QMainWindow):
    update_UI_sig = QtCore.pyqtSignal()
    plot_sig = QtCore.pyqtSignal()
    update_progress_sig = QtCore.pyqtSignal(float)
    def __init__(self):
        super(ScanRecaller, self).__init__()
        self.update_UI_sig.connect(self.update_ui)
        self.plot_sig.connect(self.plot)
        self.update_progress_sig.connect(self.update_progress)
        self.initialized = False
        self.holding = True
        self.scan_numbers = []
        self.available_scans = []
        self.masses = []
        self.formats = {}
        self.xkey = []
        self.ykey = []
        self.checks = {}

        self.looping = True
        t = th.Thread(target=self.startIOLoop).start()

        self.init_UI()

        time.sleep(0.1)
        self.add_fileserver()


    def init_UI(self):
        widget = QtGui.QWidget()
        self.setCentralWidget(widget)

        self.layout = QtGui.QGridLayout(widget)

 #        self.comboX = QtGui.QComboBox(parent=None)
 #        self.comboX.setMinimumWidth(250)
 #        self.comboX.setCurrentIndex(0)
 #        self.comboX.setToolTip('Choose the variable you want to put\
 # on the X-axis.')
 #        self.layout.addWidget(QtGui.QLabel('x: '),2,0)
 #        self.layout.addWidget(self.comboX, 2, 1)

 #        self.comboY = QtGui.QComboBox(parent=None)
 #        self.comboY.setMinimumWidth(250)
 #        self.comboY.setToolTip('Choose the variable you want to put\
 # on the Y-axis.')
 #        self.comboY.setCurrentIndex(0)
 #        self.layout.addWidget(QtGui.QLabel('y: '),3,0)
 #        self.layout.addWidget(self.comboY, 3, 1)

 #        self.graphStyles = ['sqrt','std dev','None']#, 'Point']
 #        self.layout.addWidget(QtGui.QLabel('Errors:'), 4, 0)
 #        self.error_box = QtGui.QComboBox(self)
 #        self.error_box.setToolTip('Choose how you want to calculate the errors:\
 # as the standard deviation within the bin or assuming poisson statistics.')
 #        self.error_box.addItems(['sqrt','std dev','None'])
 #        self.error_box.setMaximumWidth(110)
 #        self.error_box.setCurrentIndex(0)
 #        self.layout.addWidget(self.error_box, 4, 1)


        self.layout.addWidget(QtGui.QLabel(self, text="Bin size: "), 2, 0)
        self.binSpinBox = pg.SpinBox(value=10,
                                     suffix='MHz',
                                     bounds=(0, None),
                                     dec=False,
                                     minStep=1,step=1)
        self.binSpinBox.setToolTip('Choose the bin size\
 used to bin the data.')
        self.binSpinBox.setMaximumWidth(110)
        self.layout.addWidget(self.binSpinBox, 2, 1)

        self.plotButton = QtGui.QPushButton('Retrieve and plot!')
        self.plotButton.clicked.connect(self.retrieve)
        self.layout.addWidget(self.plotButton,5,19)

        self.layout.addWidget(QtGui.QLabel('Mass:'),2,3)
        self.mass_selector = QtGui.QComboBox()
        self.mass_selector.currentIndexChanged.connect(self.update_scan_selector)
        self.layout.addWidget(self.mass_selector,2,4)
        
        self.layout.addWidget(QtGui.QLabel('Scans:'),3,3)
        self.scan_selector = QtGui.QWidget()
        self.scan_layout = QtGui.QGridLayout(self.scan_selector)
        self.layout.addWidget(self.scan_selector,3,4,2,16)

        self.plotWidget = pg.PlotWidget()
        self.layout.addWidget(self.plotWidget,0,0,1,17)
        self.curve = pg.ErrorBarItem(x=np.array([]),y=np.array([]),
                    top=np.array([]),bottom=np.array([]),beam=0.)
        self.plotWidget.addItem(self.curve)
        self.points = pg.ScatterPlotItem()
        self.plotWidget.addItem(self.points)
        self.fit_curve = pg.PlotCurveItem()
        self.plotWidget.addItem(self.fit_curve)

        self.fitWidget = FitWidget()
        self.fitWidget.fit_ready.connect(self.plot_fit)
        self.layout.addWidget(self.fitWidget,0,17,1,3)

        self.progressBar = QtGui.QProgressBar()
        self.progressBar.setMinimum(0)
        self.progressBar.setMaximum(1000)
        self.layout.addWidget(self.progressBar, 1, 0, 1, 20)

        self.show()

    def stopIOLoop(self):
        self.looping = False

    def startIOLoop(self):
        while self.looping:
            asyncore.loop(count=1, timeout=0.01)
            time.sleep(0.03)

    def add_fileserver(self):
        try:
            self.file_server = Connector(name='R_to_FS',
                                         chan=fileServer_channel,
                                         callback=self.reply_cb,
                                         onCloseCallback=self.onCloseCallback,
                                         default_callback=self.default_cb)
        except Exception as e:
            print(e)

    def reply_cb(self,message):
        if message['reply']['parameters']['status'][0] == 0:
            function = message['reply']['op']
            args = message['reply']['parameters']
            track = message['track']

            params = getattr(self, function)(track, args)

        else:
            print('DataViewer received fail message', message)

    def default_cb(self):
        if self.holding:
            return 'get_status',{}
        else:
            return 'request_processed_data',{'scan_numbers':self.scan_numbers,
                               'x':self.xkey,
                               'y':self.ykey,
                               'bin_size':self.bin_size,
                               'error_mode':self.error_mode}

    def onCloseCallback(self,connector):
        print('lost connection')

    def get_status_reply(self,track,params):
        available_scans = params['available_scans']
        masses = params['masses']
        sorted_results = sorted(zip(available_scans,masses),key=lambda x:x[0])
        available_scans,masses = [[x[i] for x in sorted_results] for i in range(2)]

        self.available_scans = np.array(available_scans,dtype=int)
        self.masses = np.array(masses,dtype=int)
        formats = params['data_format']

        if not formats == {} and not formats == self.formats:
            self.formats = formats
            self.update_UI_sig.emit()

    def request_processed_data_reply(self,track,params):
        origin, track_id = track
        done = params['done'][0]
        if done:
            self.centers = np.array(params['centers'])*3 #Tripling!
            self.center_err = np.array(params['center_err'])*3 #Tripling!
            self.bin_means = np.array(params['bin_means'])
            self.err = np.array(params['err'])
            print(params.keys())

            #if 'wavenumber' in self.xkey[1]:
            #    self.centers *= c*100*10**-6 #now in MHz!
            #    self.center_err *= c*100*10**-6 #now in MHz!
            #if 'wavenumber' in self.ykey[1]:
            #    self.bin_means *= c*100*10**-6 #now in MHz!
            #    self.err *= c*100*10**-6 #now in MHz!


            self.fitWidget.define_data(self.centers,
                        self.bin_means,
                        self.err)

            self.update_progress_sig.emit(100)
            self.plot_sig.emit()
            self.holding = True
            self.switch_ui()

        else:
            self.update_progress_sig.emit(params['progress'][0])

    def update_progress(self,progress):
        progress *= 10
        self.progressBar.setValue(progress)

    def plot(self):
        if 'wavenumber' in self.xkey[1]:
            # offset = np.median(self.centers)
            offset = 40150.14883910584
            x = self.centers - offset
            self.plotWidget.setLabel(text='offset: {} MHz {} cm-1'.format(offset*c*100*10**-6,offset),
                                     axis='bottom')
        else:
            x = self.centers

        if not self.err == np.array([]):
            self.curve.setData(x=x, y=self.bin_means,
                left = self.center_err,right = self.center_err,
                top = self.err, bottom = self.err,
                beam=0.)
        else:
            self.curve.setData(x=x, y=self.bin_means,
                left = self.center_err,right = self.center_err,
                beam=0.)

        self.points.setData(x=x, y=self.bin_means)

    def plot_fit(self):
        if 'wavenumber' in self.xkey[1]:
            offset = np.median(self.centers)
            x = self.centers - offset
        else:
            x = self.centers
        self.fit_curve.setData(x,self.fitWidget.fit,pen='r')

    def retrieve(self):
        self.scan_numbers = [int(name) for name,check in self.scan_checks.items() \
                                if check.isChecked()]
        if self.scan_numbers == []:
            return

        # self.xkey = str(self.comboX.currentText()).split(': ')
        # self.ykey = str(self.comboY.currentText()).split(': ')

        self.xkey = ['wavemeter','wavenumber_1']
        self.ykey = ['CRIS','Counts']

        if 'device' in self.xkey or 'device' in self.ykey:
            return

        self.bin_size = float(self.binSpinBox.value())/30000
        if self.bin_size == 0:
            return

        # self.error_mode = str(self.error_box.currentText())
        self.error_mode = 'sqrt'
        self.holding = False

        self.switch_ui()

    def switch_ui(self):
        if self.holding:
            # self.comboY.setEnabled(True)
            # self.comboX.setEnabled(True)
            self.binSpinBox.setEnabled(True)
            self.plotButton.setEnabled(True)
            # self.error_box.setEnabled(True)
            for check_dict in self.checks.values():
                for check in check_dict.values():
                    check.setEnabled(True)
        else:
            # self.comboY.setDisabled(True)
            # self.comboX.setDisabled(True)
            self.binSpinBox.setDisabled(True)
            self.plotButton.setDisabled(True)
            # self.error_box.setDisabled(True)
            for check_dict in self.checks.values():
                for check in check_dict.values():
                    check.setDisabled(True)

    def update_ui(self):
        masses_list = sorted(list(set(self.masses)))
        self.mass_selector.clear()
        self.mass_selector.addItems([str(m) for m in masses_list])

        # options = ['device: parameter']
        # options.extend([key+': '+v for key,val in self.formats.items() for v in val])

        # self.comboX.clear()
        # self.comboX.addItems(options)
        # try:
        #     self.comboX.setCurrentIndex(options.index('wavemeter: wavenumber_1'))
        # except:
        #     self.comboX.setCurrentIndex(0)

        # self.comboY.clear()
        # self.comboY.addItems(options)
        # try:
        #     self.comboY.setCurrentIndex(options.index('CRIS: Counts'))
        # except:
        #     self.comboY.setCurrentIndex(0)

    def update_scan_selector(self):
        for i in reversed(range(self.scan_layout.count())): 
            self.scan_layout.itemAt(i).widget().setParent(None)

        mass = self.mass_selector.currentText()
        slicer = self.masses == int(mass)
        scans = self.available_scans[slicer]
        self.scan_checks = {}
        i = 0
        for scan in scans:
            if not scan == -1.0:
                self.scan_checks[scan]=QtGui.QCheckBox(str(scan))
                self.scan_layout.addWidget(self.scan_checks[scan],i//10,i%10)
                i=i+1

    def closeEvent(self,event):
        self.stopIOLoop()
        event.accept()

class FitWidget(QtGui.QWidget):
    fit_ready = QtCore.pyqtSignal()
    def __init__(self):
        super(FitWidget,self).__init__()
        self.x = []
        self.y = []
        self.yerr = []

        self.checks = {}

        self.layout = QtGui.QGridLayout(self)

        self.init_UI()

    def init_UI(self): 

        self.layout.addWidget(QtGui.QLabel('I'),0,1)
        self.I = pg.SpinBox(value=1.5,step=0.5)
        self.layout.addWidget(self.I,0,2)

        self.layout.addWidget(QtGui.QLabel('Jl'),1,1)
        self.J0 = pg.SpinBox(value=0.5,step=0.5)
        self.layout.addWidget(self.J0,1,2)

        self.layout.addWidget(QtGui.QLabel('Ju'),2,1)
        self.J1 = pg.SpinBox(value=1.5,step=0.5)
        self.layout.addWidget(self.J1,2,2)

        self.layout.addWidget(QtGui.QLabel('centr'),3,1)
        self.centroid = QtGui.QLineEdit(text=str(401.340000*3))

        self.layout.addWidget(self.centroid,3,2)
        
        self.vary_centroid = QtGui.QCheckBox()
        self.checks['Centroid'] = self.vary_centroid
        self.vary_centroid.setChecked(True)
        self.layout.addWidget(self.vary_centroid,3,0)

        self.layout.addWidget(QtGui.QLabel('Al'),4,1)
        self.Al = pg.SpinBox(value=6000*10**6, 
                                   suffix='Hz', siPrefix = True, dec = True, step = 0.01,
                                   minStep = 10**6)
        self.layout.addWidget(self.Al,4,2)
        
        self.vary_Al = QtGui.QCheckBox()
        self.checks['Al'] = self.vary_Al
        self.vary_Al.setChecked(True)
        self.layout.addWidget(self.vary_Al,4,0)

        self.layout.addWidget(QtGui.QLabel('Au'),5,1)
        self.Au = pg.SpinBox(value=2000*10**6, 
                                   suffix='Hz', siPrefix = True,
                                   dec = True, step = 0.01,
                                   minStep = 10**6)
        self.layout.addWidget(self.Au,5,2)
        
        self.vary_Au = QtGui.QCheckBox()
        self.checks['Au'] = self.vary_Au
        self.vary_Au.setChecked(True)
        self.layout.addWidget(self.vary_Au,5,0)

        self.layout.addWidget(QtGui.QLabel('Bl'),6,1)
        self.Bl = pg.SpinBox(value=0*10**6, 
                                   suffix='Hz', siPrefix = True,
                                   dec = True, step = 0.01,
                                   minStep = 10**6)
        self.layout.addWidget(self.Bl,6,2)
        
        self.vary_Bl = QtGui.QCheckBox()
        self.checks['Bl'] = self.vary_Bl
        self.vary_Bl.setChecked(True)
        self.layout.addWidget(self.vary_Bl,6,0)

        self.layout.addWidget(QtGui.QLabel('Bu'),7,1)
        self.Bu = pg.SpinBox(value=-35*10**6, 
                                   suffix='Hz', siPrefix = True,
                                   dec = True, step = 0.01,
                                   minStep = 10**6)
        self.layout.addWidget(self.Bu,7,2)
        
        self.vary_Bu = QtGui.QCheckBox()
        self.checks['Bu'] = self.vary_Bu
        self.vary_Bu.setChecked(True)
        self.layout.addWidget(self.vary_Bu,7,0)

        self.layout.addWidget(QtGui.QLabel('FWHMG'),8,1)
        self.FWHMG = pg.SpinBox(value=20*10**6, 
                                   suffix='Hz', siPrefix = True,
                                   dec = True, step = 0.01,
                                   minStep = 10**6)
        self.layout.addWidget(self.FWHMG,8,2)
        
        self.vary_FWHMG = QtGui.QCheckBox()
        self.checks['FWHMG'] = self.vary_FWHMG
        self.vary_FWHMG.setChecked(True)
        self.layout.addWidget(self.vary_FWHMG,8,0)

        self.layout.addWidget(QtGui.QLabel('FWHML'),9,1)
        self.FWHML = pg.SpinBox(value=20*10**6, 
                                   suffix='Hz', siPrefix = True,
                                   dec = True, step = 0.01,
                                   minStep = 10**6)
        self.layout.addWidget(self.FWHML,9,2)
        
        self.vary_FWHML = QtGui.QCheckBox()
        self.checks['FWHML'] = self.vary_FWHML
        self.vary_FWHML.setChecked(True)
        self.layout.addWidget(self.vary_FWHML,9,0)

        self.layout.addWidget(QtGui.QLabel('bkg'),10,1)
        self.bkg = pg.SpinBox(value=0, 
                               dec = True, step = 0.01,
                               minStep = 10**-6)
        self.layout.addWidget(self.bkg,10,2)
        
        self.vary_bkg = QtGui.QCheckBox()
        self.checks['Bacground0'] = self.vary_bkg
        self.vary_bkg.setChecked(True)
        self.layout.addWidget(self.vary_bkg,10,0)

        self.layout.addWidget(QtGui.QLabel('scale'),11,1)
        self.scale = pg.SpinBox(value=1, 
                               dec = True, step = 0.01,
                               minStep = 10**-6)
        self.layout.addWidget(self.scale,11,2)
        
        self.vary_scale = QtGui.QCheckBox()
        self.checks['Scale'] = self.vary_scale
        self.vary_scale.setChecked(True)
        self.layout.addWidget(self.vary_scale,11,0)

        self.fix_int = QtGui.QCheckBox('Fix intensities to Racah')
        self.fix_int.setChecked(True)
        self.layout.addWidget(self.fix_int,12,0,1,3)

        self.layout.addWidget(QtGui.QWidget(),13,1)

        self.plot_guess = QtGui.QPushButton('Plot guess')
        self.plot_guess.clicked.connect(self.update_guess)
        self.layout.addWidget(self.plot_guess,14,1)
        self.fit = QtGui.QPushButton('Fit')
        self.fit.clicked.connect(self.make_fit)
        self.layout.addWidget(self.fit,14,2)

    def make_spectrum(self):
        self.spectrum = sat.HFSModel(
            I=self.I.value(),
            J=[self.J0.value(),self.J1.value()],
            centroid = float(self.centroid.text())*10**(-12),
            ABC = [self.Al.value()*10**-6,self.Au.value()*10**-6,
                   self.Bl.value()*10**-6,self.Bu.value()*10**-6,
                   0,0],
            fwhm = [self.FWHMG.value()*10**-6,self.FWHMG.value()*10**-6],
            background_params = [self.bkg.value()],
            scale = self.scale.value())
        self.spectrum.saturation = 10**-10

    def update_guess(self):
        self.make_spectrum()
        self.fit = self.spectrum(self.x)
        self.fit_ready.emit()

    def make_fit(self):
        self.make_spectrum()
        vary_dict = {}
        for key,val in self.checks.items():
            vary_dict[key] = val.isChecked()

        for label in self.spectrum.ftof:
            vary_dict['Amp' + label] = not self.fix_int.isChecked()
        vary_dict['Cl']=False
        vary_dict['Cu']=False

        self.spectrum.set_variation(vary_dict)

        if np.any(self.yerr == 0):
            QtGui.QMessageBox.warning(self, 'Problem with errors',
'One or more of the error bars is zero. This will cause the chi square routine to fail spectacularly. Removing them.')
            sat.chisquare_fit(self.spectrum,self.x[self.yerr>0],self.y[self.yerr>0],self.yerr[self.yerr>0])
        
        else:
            sat.chisquare_fit(self.spectrum,self.x*c*100*10**-6,self.y,self.yerr)

        self.fit = self.spectrum(self.x*c*100*10**-6)
        self.fit_ready.emit()
        self.show_results_table()

    def show_results_table(self):
        self.resp = ResultsTable()

        self.resp.setColumnCount(2)
        self.resp.setHorizontalHeaderLabels(['Value','Error'])
        
        vert = []
        vert.append('Chi sqr:')
        vert.append('Reduced chi sqr:')
        for par in self.spectrum.params.values():
            if not par.name in ['Saturation','N','Cl','Cu']:
                vert.append(str(par.name))
        self.resp.setRowCount(len(vert))
        self.resp.setVerticalHeaderLabels(vert)
        
        self.resp.setItem(0, 0, QtGui.QTableWidgetItem(str(self.spectrum.chisqr)))
        self.resp.setItem(1, 0, QtGui.QTableWidgetItem(str(self.spectrum.redchi)))
        i=0
        for par in self.spectrum.params.values():
            if not par.name in ['Saturation','N','Cl','Cu']:
                self.resp.setItem(i+2, 0, QtGui.QTableWidgetItem(str(par.value)))
                self.resp.setItem(i+2, 1, QtGui.QTableWidgetItem(str(par.stderr)))
                i=i+1
        
        self.resp.resizeColumnsToContents()
        self.resp.setFixedSize(2*self.resp.horizontalHeader().length(),self.resp.verticalHeader().length()+60)
        
        self.resp.show()

    def define_data(self,x,y,yerr):
        self.x = x
        self.y = y
        self.yerr = yerr


class ResultsTable(QtGui.QTableWidget):
    def __init__(self):
        super(ResultsTable,self).__init__()
        self.clip = QtGui.QApplication.clipboard()

    def keyPressEvent(self, e):
        if (e.modifiers() & QtCore.Qt.ControlModifier):
            selected = self.selectedRanges()

            if e.key() == QtCore.Qt.Key_C: #copy
                s = '\t'+"\t".join([str(self.horizontalHeaderItem(i).text()) for i in xrange(selected[0].leftColumn(), selected[0].rightColumn()+1)])
                s = s + '\n'

                for r in xrange(selected[0].topRow(), selected[0].bottomRow()+1):
                    s += self.verticalHeaderItem(r).text() + '\t'
                    for c in xrange(selected[0].leftColumn(), selected[0].rightColumn()+1):
                        try:
                            s += str(self.item(r,c).text()) + "\t"
                        except AttributeError:
                            s += "\t"
                    s = s[:-1] + "\n" #eliminate last '\t'
                self.clip.setText(s)

def main():
    pg.setConfigOption('background', 'w')
    pg.setConfigOption('foreground', 'k')
    # add freeze support
    freeze_support()
    app = QtGui.QApplication(sys.argv)
    m = ScanRecaller()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()

