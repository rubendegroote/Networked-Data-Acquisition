import pyqtgraph as pg
from PyQt5 import QtCore, QtGui, QtWidgets
import pyqtgraph.dockarea as da
import datetime
import numpy as np
import pandas as pd
from picbutton import PicButton
import time
import pyqtgraph.exporters
import webbrowser
import lmfit as lm
import satlas as sat
from backend.helpers import calcHist
import uncertainties as unc


class XYGraph(QtWidgets.QWidget):
    dataRequested = QtCore.pyqtSignal(str)
    scanRequested = QtCore.pyqtSignal(str)
    def __init__(self, name):
        super(QtWidgets.QWidget, self).__init__()

        self.reset = False
        self.options = []
        self.name = name
        self.formats = {}
        self.x_key = []
        self.y_key = []
        self.fit_blobs = []

        self.mass = -1
        self.scan_number = -1

        self.mode = 'stream'

        self.bins = np.zeros(1)
        self.init_UI()

        self.logmode = False
        self.axis_in_log = False
        
        self.reset_data()
        
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.plot)
        self.timer.start(50)

        # self.timer2 = QtCore.QTimer()
        # self.timer2.timeout.connect(self.treat_data)
        # self.timer2.start(50)

    def init_UI(self):

        self.layout = QtWidgets.QGridLayout(self)

        self.labelStyle = {'font-size': '18pt'}

        gView = pg.GraphicsView()

        self.graph = pg.PlotWidget()
        self.graph.showGrid(x=True, y=True, alpha=0.1)

        self.error_curve = pg.ErrorBarItem(x=np.array([]),y=np.array([]),
                    top=np.array([]),bottom=np.array([]),beam=0.)
        self.graph.addItem(self.error_curve)

        self.points_curve = pg.ScatterPlotItem(x=np.array([]),y=np.array([]),brush='k')
        self.graph.addItem(self.points_curve)

        layout = QtWidgets.QGridLayout(gView)

        layout.addWidget(self.graph, 0, 0, 1, 1)
        self.sublayout = QtWidgets.QGridLayout()
        layout.addLayout(self.sublayout, 1, 0)


        self.sublayout.addWidget(QtWidgets.QLabel('y: '),0,0)
        self.comboY = QtGui.QComboBox(parent=None)
        self.comboY.setMinimumWidth(250)
        self.comboY.setToolTip('Choose the variable you want to put\
 on the Y-axis.')
        self.sublayout.addWidget(self.comboY, 0, 1)

        self.sublayout.addWidget(QtWidgets.QLabel('x: '),0,2)
        self.comboX = QtGui.QComboBox(parent=None)
        self.comboX.setMinimumWidth(250)
        self.comboX.setToolTip('Choose the variable you want to put\
 on the X-axis.')
        self.sublayout.addWidget(self.comboX, 0, 3)

        self.graphStyles = ['poisson','std dev','None']#, 'Point']

        label = QtWidgets.QLabel('Errors: ')
        label.setStyleSheet("border: 0px;")
        self.sublayout.addWidget(label, 0, 4)

        self.error_box = QtGui.QComboBox(self)
        self.error_box.setToolTip('Choose how you want to calculate the errors:\
 as the standard deviation within the bin or assuming poisson statistics.')
        self.error_box.addItems(self.graphStyles)
        self.error_box.setCurrentIndex(0)
        self.error_box.setMaximumWidth(110)
        # self.error_box.currentIndexChanged.connect(self.updatePlot)
        self.sublayout.addWidget(self.error_box, 0, 5)
        self.error_box.currentIndexChanged.connect(self.toggle_plot_needed)

        label = QtWidgets.QLabel('data mode: ')
        label.setStyleSheet("border: 0px;")
        self.sublayout.addWidget(label, 0, 6)

        self.data_box = QtGui.QComboBox(self)
        self.data_box.currentIndexChanged.connect(self.change_label)
        self.data_box.setToolTip('Choose if you want the sum or mean of the data per bin')
        self.data_box.addItems(['sum','mean'])
        self.data_box.setCurrentIndex(0)
        self.data_box.setMaximumWidth(110)
        # self.error_box.currentIndexChanged.connect(self.updatePlot)
        self.sublayout.addWidget(self.data_box, 0, 7)
        self.data_box.currentIndexChanged.connect(self.toggle_plot_needed)

        self.binLabel = QtWidgets.QLabel(self, text="Bin size: ")
        self.prev_binsize = 1000
        self.binSpinBox = pg.SpinBox(value=self.prev_binsize,
                                     bounds=(0, None),
                                     dec=False)
        self.binSpinBox.setToolTip('Choose the bin size used to bin the data.')
        self.binSpinBox.setMaximumWidth(110)
        self.sublayout.addWidget(self.binLabel, 2, 4)
        self.sublayout.addWidget(self.binSpinBox, 2, 5)
        self.binSpinBox.sigValueChanged.connect(self.toggle_plot_needed)

        self.sublayout.addWidget(QtWidgets.QLabel("y offset"),2,0)
        self.y_offset = QtWidgets.QLineEdit("0")
        self.y_offset.textChanged.connect(self.change_label)
        self.sublayout.addWidget(self.y_offset, 2, 1)

        self.sublayout.addWidget(QtWidgets.QLabel("x offset"),2,2)
        self.x_offset = QtWidgets.QLineEdit("0")
        self.x_offset.textChanged.connect(self.change_label)
        self.sublayout.addWidget(self.x_offset, 2, 3)

        self.sublayout.addWidget(QtWidgets.QLabel("x cut left"),3,0)
        self.x_cut_left = QtWidgets.QLineEdit("-10000000000")
        self.sublayout.addWidget(self.x_cut_left, 3, 1)
        self.x_cut_left.textChanged.connect(self.toggle_plot_needed)

        self.sublayout.addWidget(QtWidgets.QLabel("x cut right"),3,2)
        self.x_cut_right = QtWidgets.QLineEdit("10000000000")
        self.sublayout.addWidget(self.x_cut_right, 3, 3)
        self.x_cut_right.textChanged.connect(self.toggle_plot_needed)

        self.unit_check = QtGui.QCheckBox('Use MHz?')
        self.unit_check.stateChanged.connect(self.change_label)
        self.unit_check.stateChanged.connect(self.toggle_plot_needed)
        self.unit_check.setDisabled(True)
        self.sublayout.addWidget(self.unit_check, 2, 7)

        self.clean_stream = QtWidgets.QPushButton('Reset data')
        self.sublayout.addWidget(self.clean_stream, 3, 7, 1, 1)
        self.clean_stream.clicked.connect(self.clean)
        QtGui.QShortcut(QtGui.QKeySequence("Ctrl+R"), self, self.clean)

        self.log_button = QtWidgets.QPushButton('Semilog plot')
        self.log_button.setCheckable(True)
        self.sublayout.addWidget(self.log_button, 3, 6, 1, 1)
        self.log_button.clicked.connect(self.toggle_log)
        QtGui.QShortcut(QtGui.QKeySequence("Ctrl+L"), self, self.toggle_log)

        self.remove_blobs_button = QtWidgets.QPushButton('Remove fits')
        self.sublayout.addWidget(self.remove_blobs_button, 3, 5, 1, 1)
        self.remove_blobs_button.clicked.connect(self.clear_blobs)
        QtGui.QShortcut(QtGui.QKeySequence("Ctrl+C"), self, self.clear_blobs)

        self.save_button = QtWidgets.QPushButton('Save')
        self.sublayout.addWidget(self.save_button, 3, 4, 1, 1)
        self.save_button.clicked.connect(self.save)
        QtGui.QShortcut(QtGui.QKeySequence("Ctrl+S"), self, self.save)

        self.sublayout.setColumnStretch(8, 1)
        self.layout.addWidget(gView, 0, 0)

        self.fit_results = pg.TextItem()
        self.fit_results.setParentItem(self.graph.plotItem.vb)

        ###### crosshairs
        self.graphvb = self.graph.plotItem.vb
        self.posLabel = pg.TextItem('',anchor = (1,1))
        self.graphvb.addItem(self.posLabel, ignoreBounds=True)

        vLine = pg.InfiniteLine(angle=90, movable=False, pen='b')
        hLine = pg.InfiniteLine(angle=0, movable=False, pen='b')
        self.graph.addItem(vLine, ignoreBounds=True)
        self.graph.addItem(hLine, ignoreBounds=True)

        def mouseMoved(mousePoint):
            curvePoint = self.graphvb.mapSceneToView(mousePoint)
            if self.graph.sceneBoundingRect().contains(mousePoint):
                y = curvePoint.y()
                if self.logmode:
                    y = 10**y
                try:
                    if 'wavenumber' in self.x_key[1]:
                        x = curvePoint.x() 
                        if self.unit_check.isChecked():
                            x = x / 29979.2458 
                        x += float(self.x_offset.text())

                        self.posLabel.setHtml("<span style='font-size: 12pt'> <span style = 'color: red'> \
                            x=%0.5fcm-1,y=%0.5f</span>" % (x, y))
                    else:
                        x = curvePoint.x()
                        self.posLabel.setHtml("<span style='font-size: 12pt'> <span style = 'color: red'> \
                            x=%0.5f,y=%0.5f</span>" % (x, y))
                except:
                    x = curvePoint.x()
                    self.posLabel.setHtml("<span style='font-size: 12pt'> <span style = 'color: red'> \
                        x=%0.5f,y=%0.5f</span>" % (x, y))
                vLine.setPos(curvePoint.x())
                hLine.setPos(curvePoint.y())
                self.posLabel.setPos(curvePoint.x(),curvePoint.y())
        self.graph.scene().sigMouseMoved.connect(mouseMoved)

        #####
        self.fitter = Fitter(self)
        self.fitter.plotSignal.connect(self.plot_model)
        self.fitter.fitSignal.connect(self.fit_model)
        self.fitter.fitPeakSig.connect(self.start_peakfit)

        self.layout.addWidget(self.fitter,0,1)


    def clean(self):
        self.data = self.data.iloc[-10:]

    def toggle_plot_needed(self):
        self.plot_needed = True

    def setXYOptions(self, options):
        self.options = ['device: parameter']
        self.options.extend([key+': '+v for key,val in options.items() for v in val])

        self.comboX.addItems(self.options)
        try:
            self.comboX.setCurrentIndex(self.options.index('wavemeter: wavenumber_1'))
        except:
            self.comboX.setCurrentIndex(0)

        self.comboY.addItems(self.options)
        try:
            self.comboY.setCurrentIndex(self.options.index('cris: Counts'))
        except:
            self.comboY.setCurrentIndex(0)

        self.comboX.currentIndexChanged.connect(self.newXY)
        self.comboX.currentIndexChanged.connect(self.change_label)
        self.comboY.currentIndexChanged.connect(self.newXY)
        self.comboY.currentIndexChanged.connect(self.change_label)

        self.newXY()

    def newXY(self):
        new_xkey = str(self.comboX.currentText()).split(': ')
        new_ykey = str(self.comboY.currentText()).split(': ')

        if not 'device' in new_xkey and not 'device' in new_ykey:
            self.reset = True
            self.x_key = new_xkey
            self.y_key = new_ykey
            self.verify_unit_check()
            self.plot_needed = True

        else:
            self.x_key = []
            self.y_key = []

    def verify_unit_check(self):
        if 'wavenumber' in self.x_key[1] or 'wavenumber' in self.y_key[1]:
            self.unit_check.setEnabled(True)
        else:
            self.unit_check.setDisabled(True)
            self.unit_check.setChecked(False)

    def change_label(self):
        try:
            xkey = str(self.comboX.currentText()).split(': ')[1]
            ykey = str(self.comboY.currentText()).split(': ')[1]
        except:
            return
            
        if 'wavenumber' in xkey:
            try:
                offset = float(self.x_offset.text())
                if self.unit_check.isChecked():
                    self.graph.setLabel('bottom','Frequency (offset {} cm-1)'.format(offset),labelStyle = {'color': '#FFF', 'font-size': '24pt'})
                else:
                    self.graph.setLabel('bottom','Wavenumber (offset {} cm-1)'.format(offset),labelStyle = {'color': '#FFF', 'font-size': '24pt'})
            except:
                pass
        else:
            self.graph.setLabel('bottom','',labelStyle = {'color': '#FFF', 'font-size': '24pt'})


        if 'wavenumber' in ykey:
            offset = float(self.y_offset.text())
            if self.unit_check.isChecked():
                self.graph.setLabel('left','Frequency (offset {} cm-1)'.format(offset),labelStyle = {'color': '#FFF', 'font-size': '24pt'})
            else:
                self.graph.setLabel('left','Wavenumber (offset {} cm-1)'.format(offset),labelStyle = {'color': '#FFF', 'font-size': '24pt'})
        elif 'Counts' in ykey:
            if str(self.data_box.currentText()) == 'sum':
                self.graph.setLabel('left','Total counts per bin',labelStyle = {'color': '#FFF', 'font-size': '24pt'})
            else:
                self.graph.setLabel('left','Counts per trigger',labelStyle = {'color': '#FFF', 'font-size': '24pt'})

        else:
            self.graph.setLabel('left','',labelStyle = {'color': '#FFF', 'font-size': '24pt'})


    def reset_data(self):
        self.no_of_rows = {k:0 for k in self.formats.keys()}
        
        self.data = pd.DataFrame({'time':[],
                                  'x':[],
                                  'y':[]})
        self.binned_data = pd.DataFrame({'time':[],
                                  'x':[],
                                  'xerr':[],
                                  'yerr_t':[],
                                  'yerr_b':[],
                                  'noe':[],
                                  'y':[]})
                                
        self.reset = False
        self.plot_needed = True

    def toggle_log(self):
        self.logmode = not self.logmode
        self.axis_in_log = False
        self.graph.setLogMode(y=False)


    def treat_data(self):
        if not self.mode == 'fs':
            data = self.data.sort_values(by='time')
            data['x'] = data['x'].fillna(method='bfill')
            data = data.dropna()
        else:
            data = self.data.sort_values(by='time')

        if 'timestamp' in self.x_key:
            data['x'] = data['x'] - data['x'].values.min()
        elif 'timestamp' in self.y_key:
            data['y'] = data['y'] - data['y'].values.min()

        if 'wavenumber' in self.x_key[1]:
            if self.unit_check.isChecked():
                data['x'] = data['x'] * 29979.2458

        elif 'wavenumber' in self.y_key[1]:
            if self.unit_check.isChecked():
                data['y'] = data['y'] * 29979.2458

        max_x = float(self.x_cut_right.text())
        min_x = float(self.x_cut_left.text())
        slicer = np.logical_and(data['x']<max_x,data['x']>min_x)
        data = data[slicer]   
        binsize = self.binSpinBox.value()    
        if 'wavenumber' in self.x_key[1] and not self.unit_check.isChecked():
            binsize = self.binSpinBox.value() / 29979.2458

        start = np.min(data['x']) - np.min(data['x'])%binsize
        stop = np.max(data['x'])//binsize*binsize+binsize
        steps = np.round(abs(stop-start)/binsize,0)+1
        bins = np.linspace(start,stop,steps)

        self.bins = bins
        self.binned_data = calcHist(data, bins, self.errormode, self.data_mode)

    def plot(self):
        self.errormode = str(self.error_box.currentText())
        self.data_mode = str(self.data_box.currentText())

        self.graph.setTitle('Scan: {} \t Mass: {}'.format(self.scan_number,self.mass))

        if not self.plot_needed:
            return

        if len(self.data['time'])>0:
            try:
                self.treat_data()
            except:
                pass

            x,y,xerr,yerr_t,yerr_b = self.get_x_y()

            if self.logmode:
                log_y = np.log10(y)
                yerr_t = np.log10(y+yerr_t) - log_y
                yerr_t[np.isnan(yerr_t)] = 0
                yerr_b = log_y - np.log10(y-yerr_b)
                yerr_b[np.isnan(yerr_b)] = 0
                y = log_y

            if not self.errormode == 'None':
                try:
                    self.error_curve.setData(x=x, y=y,top=yerr_t,bottom=yerr_b,
                                            left = xerr,right = xerr,
                                            pen='k',beam=0.)
                except:
                    self.error_curve = pg.ErrorBarItem(x=x, y=y,top=yerr_t,bottom=yerr_b,
                                            left = xerr,right = xerr,
                                            pen='k',beam=0.)
                    self.graph.addItem(self.error_curve)

                    self.graph.removeItem(self.curve)
                    del self.curve
                    
                try:
                    self.points_curve.setData(x=x, y=y)
                except:
                    self.points_curve = pg.ScatterPlotItem(brush='k')
                    self.graph.addItem(self.points_curve)
                    self.points_curve.setData(x=x, y=y)
    
            else:
                try:
                    self.curve.setData(x=x, y=y,pen='k')
                except:
                    self.curve = pg.PlotCurveItem(x=x, y=y,pen='k')
                    self.graph.addItem(self.curve)
                    self.graph.removeItem(self.error_curve)
                    self.graph.removeItem(self.points_curve)
                    del self.error_curve
                    del self.points_curve

        if self.logmode and not self.axis_in_log:
            self.graph.setLogMode(y=True)
            self.axis_in_log = True


    def get_x_y(self):
        if self.unit_check.isChecked():
            if 'wavenumber' in self.x_key[1]:
                x = self.binned_data['x'].values - float(self.x_offset.text())*29979.2458
            else:
                x = self.binned_data['x'].values - float(self.x_offset.text())
            if 'wavenumber' in self.y_key[1]:
                y = self.binned_data['y'].values - float(self.y_offset.text())*29979.2458
            else:
                y = self.binned_data['y'].values - float(self.y_offset.text())
        else:
            x = self.binned_data['x'].values - float(self.x_offset.text())
            y = self.binned_data['y'].values - float(self.y_offset.text())

        xerr,yerr_t,yerr_b = self.binned_data['xerr'].values,\
                             self.binned_data['yerr_t'].values,\
                             self.binned_data['yerr_b'].values

        return x,y,xerr,yerr_t,yerr_b

    def save(self):
        exporter = pg.exporters.ImageExporter(self.graph.plotItem)
        name = QtGui.QFileDialog.getSaveFileName(self, 'Save File')
        exporter.export(name)
        webbrowser.open(name)

    def clear_blobs(self):
        for ft in self.fit_blobs:
            self.graphvb.removeItem(ft)
        try:
            del self.single_peak_curve
        except:
            pass
        try:
            del self.hfs_fit_curve
        except:
            pass

        self.fit_blobs = []
        self.fit_results.setHtml('')

    def pos_chooser(self,mousePoint):
        if mousePoint.double():
            pos = self.graphvb.mapSceneToView(mousePoint.scenePos())
            self.peaks.append(pos.x())
            self.heights.append(pos.y())

    def plot_model(self,model):
        x,y,xerr,yerr_t,yerr_b = self.get_x_y()
        # x_plot = np.linspace(x.min(),x.max(),10**4)

        ranges = []
        for pos in model.locations:
            r = np.linspace(pos - 5 * model.params['TotalFWHM'].value,
                            pos + 5 * model.params['TotalFWHM'].value,
                            200)
            ranges.append(r)
        x_fit = np.sort(np.concatenate(ranges))
        if self.unit_check.isChecked():
            x_plot = x_fit - float(self.x_offset.text())* 29979.2458 
        else:
            x_plot = x_fit / 29979.2458 - float(self.x_offset.text())

        try:
            self.hfs_fit_curve
        except:
            self.hfs_fit_curve = pg.PlotCurveItem(pen='r')

        self.hfs_fit_curve.setData(x=x_plot, y=model(x=x_fit))
        self.fit_blobs.append(self.hfs_fit_curve)
        self.graphvb.addItem(self.hfs_fit_curve)
    
    def satlas_fit(model,x,y,yerr):
        nan_slicer = np.isnan[yerr]
        yerr[nan_slicer] = y[nan_slicer]
        sat.chisquare_fit(model,x,y,yerr)

    def fit_model(self,model):
        x,y,xerr,yerr_t,yerr_b = self.get_x_y()
        if self.unit_check.isChecked():
            x = x + float(self.x_offset.text())*29979.2458
        else:
            x = (x + float(self.x_offset.text()))*29979.2458
        off = x.min()

        model.set_value({'Centroid':model.params['Centroid'].value-off})

        self.satlas_fit(model,x=x-off,y=y,yerr=yerr_t)

        model.set_value({'Centroid':model.params['Centroid'].value+off})

        self.plot_model(model)
        
        self.fitter.set_fit(model)

        pars = model.params

        html = '<div style="text-align: center">\
                <div style = "color: black"> \
                <div style = "font-size: 14px"> \
                <span><span style="font-size: 20pt;">Al:{}</span><br> \
                <span><span style="font-size: 20pt;">Au:{}</span><br> \
                <span><span style="font-size: 20pt;">Bl:{}</span><br> \
                <span><span style="font-size: 20pt;">Bu:{}</span><br> \
                <span><span style="font-size: 20pt;">Centr:{}</span><br>\
                <span><span style="font-size: 20pt;">FWHMG:{}</span><br> \
                <span><span style="font-size: 20pt;">FWHML:{}</span> \
                </div>'.format(str(unc.ufloat(pars['Al'].value,pars['Al'].stderr)),
                               str(unc.ufloat(pars['Au'].value,pars['Au'].stderr)),
                               str(unc.ufloat(pars['Bl'].value,pars['Bl'].stderr)),
                               str(unc.ufloat(pars['Bu'].value,pars['Bu'].stderr)),
                               str(unc.ufloat(pars['Centroid'].value,pars['Centroid'].stderr)/29979.2458),
                               str(unc.ufloat(pars['FWHMG'].value,pars['FWHMG'].stderr)),
                               str(unc.ufloat(pars['FWHML'].value,pars['FWHML'].stderr)))
        self.fit_results.setHtml(html)

    def start_peakfit(self):
        if self.fitter.fit_button.isChecked():
            self.peaks = []
            self.heights = []

            self.graph.scene().sigMouseClicked.connect(self.pos_chooser)

        else:
            self.do_peak_fit()

    def do_peak_fit(self):
        self.graph.scene().sigMouseClicked.disconnect(self.pos_chooser)

        x,y,xerr,yerr_t,yerr_b = self.get_x_y()
        yerr = yerr_t

        w, ok = QtGui.QInputDialog.getText(self, 'FWHM Dialog', 'Enter estimated FHWM (MHz):')
        if not ok:
            return

        w = float(w)
        if not self.unit_check.isChecked():
            w /= 29979.2458

        params = lm.Parameters()
        params.add('w',w)
        params.add('bkg',0.000001)
        index = 0
        for p, h in zip(self.peaks,self.heights):
            params.add('p{}'.format(index),p)
            params.add('h{}'.format(index),h)
            index += 1

        def fitfunc(params,x):
            fit = np.zeros(len(x))
            for i in range(int((len(params)-2)/2)):
                fit += params['h{}'.format(i)].value*np.exp(-(x-params['p{}'.format(i)].value)**2/2/params['w'].value**2)

            return fit + params['bkg'].value

        def resid(params,x,y,yerr):
            return (fitfunc(params,x) - y)/yerr

        x_fit = np.linspace(x.min(),x.max(),10**4)
        self.single_peak_curve = pg.PlotCurveItem(x=x_fit, y=fitfunc(params,x_fit),pen='r')
        self.fit_blobs.append(self.single_peak_curve)
        self.graph.addItem(self.single_peak_curve)

        reply = QtGui.QMessageBox.question(self, 'Fit?', 
                     'Proceed with fit?', QtGui.QMessageBox.Yes, QtGui.QMessageBox.No)
        if not reply == QtGui.QMessageBox.Yes:
            return

        results = lm.minimize(resid,params,args=(x,y,yerr))
        respar = results.params

        fit = fitfunc(results.params,x_fit)
        if self.logmode:
            fit = np.log10(fit)
        self.single_peak_curve.setData(x=x_fit,y=fit)

        for i in range(int((len(params)-2)/2)):
            pos = respar['p{}'.format(i)].value + float(self.x_offset.text())
            w = respar['w'].value * 2.3548
            if self.unit_check.isChecked():
                pos /= 29979.2458
            else:
                w *= 29979.2458
                
            html = '<div style="text-align: center">\
                    <span><span style="font-size: 14pt;">POS:{}</span><br> \
                    <span><span style="font-size: 14pt;">HGHT:{}</span><br> \
                    <span><span style="font-size: 14pt;">FWHM:{}</span><br>\
                    <span><span style="font-size: 14pt;">BKG:{}</span><br>\
                    <span><span style="font-size: 14pt;">S/B:{}</span>\
                    </div>'.format(pos,respar['h{}'.format(i)].value,w,respar['bkg'].value,
                                   respar['h{}'.format(i)].value/respar['bkg'].value)

            self.fit_blobs.append(pg.TextItem(html=html, anchor=(-0.3,1.3), border='k', fill=(0, 0, 0, 0)))
            self.graphvb.addItem(self.fit_blobs[-1])
            height = respar['h{}'.format(i)]
            if self.logmode:
                height = np.log10(height)
            self.fit_blobs[-1].setPos(respar['p{}'.format(i)].value,height)

class Fitter(QtWidgets.QWidget):
    plotSignal = QtCore.pyqtSignal(object)
    fitSignal = QtCore.pyqtSignal(object)
    fitPeakSig = QtCore.pyqtSignal()
    def __init__(self,parent):
        super(QtWidgets.QWidget, self).__init__(parent)
        self.setMaximumWidth(350)
        self.setMinimumWidth(350)

        self.layout = QtWidgets.QGridLayout(self)

        self.fit_button = QtWidgets.QPushButton('Fit Single Peak')
        self.fit_button.setCheckable(True)
        self.layout.addWidget(self.fit_button, 0,0, 1, 1)
        self.fit_button.clicked.connect(self.do_fitting)
        QtGui.QShortcut(QtGui.QKeySequence("Ctrl+F"), self, self.toggle_fit)


        filler = QtWidgets.QLabel('Fit Hyperfine Structure')
        filler.setMinimumHeight(25)
        self.layout.addWidget(filler,1,0,1,4)

        self.layout.addWidget(QtWidgets.QLabel('I'),3,0)
        self.IBox = QtWidgets.QLineEdit()
        self.layout.addWidget(self.IBox,3,2)

        self.layout.addWidget(QtWidgets.QLabel('J'),4,0)
        self.JBox1 = QtWidgets.QLineEdit(placeholderText='lower')
        self.layout.addWidget(self.JBox1,4,2)
        self.JBox2 = QtWidgets.QLineEdit(placeholderText='upper')
        self.layout.addWidget(self.JBox2,4,4)

        self.layout.addWidget(QtWidgets.QLabel('Centroid'),5,0)
        self.CentroidBox = QtWidgets.QLineEdit(placeholderText='Absolute value (cm-1)')
        self.layout.addWidget(self.CentroidBox,5,2)
        self.varyCentroidCheck = QtGui.QCheckBox()
        self.varyCentroidCheck.setChecked(True)
        self.layout.addWidget(self.varyCentroidCheck,5,1)

        self.layout.addWidget(QtWidgets.QLabel('A'),6,0)
        self.ABox1 = QtWidgets.QLineEdit(placeholderText='lower (MHz)')
        self.layout.addWidget(self.ABox1,6,2)
        self.varyA1Check = QtGui.QCheckBox()
        self.varyA1Check.setChecked(True)
        self.layout.addWidget(self.varyA1Check,6,1)
        self.ABox2 = QtWidgets.QLineEdit(placeholderText='upper (MHz)')
        self.layout.addWidget(self.ABox2,6,4)
        self.varyA2Check = QtGui.QCheckBox()
        self.varyA2Check.setChecked(True)
        self.layout.addWidget(self.varyA2Check,6,3)

        self.layout.addWidget(QtWidgets.QLabel('B'),7,0)
        self.BBox1 = QtWidgets.QLineEdit(placeholderText='lower (MHz)')
        self.layout.addWidget(self.BBox1,7,2)
        self.varyB1Check = QtGui.QCheckBox()
        self.varyB1Check.setChecked(True)
        self.layout.addWidget(self.varyB1Check,7,1)
        self.BBox2 = QtWidgets.QLineEdit(placeholderText='upper (MHz)')
        self.layout.addWidget(self.BBox2,7,4)
        self.varyB2Check = QtGui.QCheckBox()
        self.varyB2Check.setChecked(True)
        self.layout.addWidget(self.varyB2Check,7,3)

        self.layout.addWidget(QtWidgets.QLabel('Width'),8,0)
        self.WidthBox1 = QtWidgets.QLineEdit(placeholderText='Gaussian (MHz)')
        self.layout.addWidget(self.WidthBox1,8,2)
        self.varyWidth1Check = QtGui.QCheckBox()
        self.varyWidth1Check.setChecked(True)
        self.layout.addWidget(self.varyWidth1Check,8,1)
        self.WidthBox2 = QtWidgets.QLineEdit(placeholderText='Lorentzian (MHz)')
        self.layout.addWidget(self.WidthBox2,8,4)
        self.varyWidth2Check = QtGui.QCheckBox()
        self.varyWidth2Check.setChecked(True)
        self.layout.addWidget(self.varyWidth2Check,8,3)

        self.layout.addWidget(QtWidgets.QLabel('Scale'),9,0)
        self.ScaleBox = QtWidgets.QLineEdit(placeholderText='')
        self.layout.addWidget(self.ScaleBox,9,2)
        self.varyScaleCheck = QtGui.QCheckBox()
        self.varyScaleCheck.setChecked(True)
        self.layout.addWidget(self.varyScaleCheck,9,1)

        self.layout.addWidget(QtWidgets.QLabel('Intensities'),10,0)
        self.varyIntCheck = QtGui.QCheckBox()
        self.layout.addWidget(self.varyIntCheck,10,1)
        self.layout.addWidget(QtWidgets.QLabel('Check to fix'),10,2)

        self.layout.addWidget(QtWidgets.QLabel('Background'),11,0)
        self.BkgBox = QtWidgets.QLineEdit(placeholderText='')
        self.layout.addWidget(self.BkgBox,11,2)
        self.varyBkgCheck = QtGui.QCheckBox()
        self.varyBkgCheck.setChecked(True)
        self.layout.addWidget(self.varyBkgCheck,11,1)


        self.plotButton = QtWidgets.QPushButton('Plot')
        self.layout.addWidget(self.plotButton,12,2)
        self.plotButton.clicked.connect(self.make_plot)

        self.fitButton = QtWidgets.QPushButton('Fit')
        self.layout.addWidget(self.fitButton,12,4)
        self.fitButton.clicked.connect(self.fit_model)

        filler = QtWidgets.QLabel('Hyperfine fit results')
        filler.setMinimumHeight(25)
        self.layout.addWidget(filler,13,0,1,4)


        self.layout.addWidget(QtWidgets.QLabel('Centroid'),15,0)
        self.CentroidBox_fit = QtWidgets.QLineEdit(placeholderText='To be fitted...')
        self.layout.addWidget(self.CentroidBox_fit,15,2,1,3)

        self.layout.addWidget(QtWidgets.QLabel('A'),16,0)
        self.ABox1_fit = QtWidgets.QLineEdit(placeholderText='To be fitted...')
        self.layout.addWidget(self.ABox1_fit,16,2)
        self.ABox2_fit = QtWidgets.QLineEdit(placeholderText='To be fitted...')
        self.layout.addWidget(self.ABox2_fit,16,4)

        self.layout.addWidget(QtWidgets.QLabel('B'),17,0)
        self.BBox1_fit = QtWidgets.QLineEdit(placeholderText='To be fitted...')
        self.layout.addWidget(self.BBox1_fit,17,2)
        self.BBox2_fit = QtWidgets.QLineEdit(placeholderText='To be fitted...')
        self.layout.addWidget(self.BBox2_fit,17,4)

        self.layout.addWidget(QtWidgets.QLabel('Width'),18,0)
        self.WidthBox1_fit = QtWidgets.QLineEdit(placeholderText='To be fitted...')
        self.layout.addWidget(self.WidthBox1_fit,18,2)
        self.WidthBox2_fit = QtWidgets.QLineEdit(placeholderText='To be fitted...')
        self.layout.addWidget(self.WidthBox2_fit,18,4)

        self.layout.addWidget(QtWidgets.QLabel('Scale'),19,0)
        self.ScaleBox_fit = QtWidgets.QLineEdit(placeholderText='To be fitted...')
        self.layout.addWidget(self.ScaleBox_fit,19,2)

        self.layout.addWidget(QtWidgets.QLabel('Intensities'),20,0)

        self.layout.addWidget(QtWidgets.QLabel('Background'),21,0)
        self.BkgBox_fit = QtWidgets.QLineEdit(placeholderText='To be fitted...')
        self.layout.addWidget(self.BkgBox_fit,21,2)

        self.layout.setColumnStretch(5, 1)
        self.layout.setRowStretch(100, 1)

        self.setGeometry(1400,100,400,800)
        self.show()

    def make_plot(self):
        model = self.make_model()
        self.plotSignal.emit(model)

    def fit_model(self):
        model = self.make_model()
        self.fitSignal.emit(model)

    def make_model(self):
        I = float(self.IBox.text())
        J = [float(self.JBox1.text()),float(self.JBox2.text())]
        ABC = [float(self.ABox1.text()),float(self.ABox2.text()),float(self.BBox1.text()),float(self.BBox2.text()),0,0]
        centroid = float(self.CentroidBox.text()) * 29979.2458 
        fwhm = [float(self.WidthBox1.text()),float(self.WidthBox2.text())]
        bkg = [float(self.BkgBox.text())]
        scale = float(self.ScaleBox.text())

        model = sat.HFSModel(I=I,J=J,ABC=ABC,centroid=centroid,background_params=bkg,scale=scale,fwhm=fwhm)
        if self.varyIntCheck.isChecked():
            model.use_racah = True

        variation = {'Centroid':self.varyCentroidCheck.isChecked(),
                     'Al':self.varyA1Check.isChecked(),
                     'Au':self.varyA2Check.isChecked(),
                     'Bl':self.varyB1Check.isChecked(),
                     'Bu':self.varyB2Check.isChecked(),
                     'FWHMG':self.varyWidth1Check.isChecked(),
                     'FWHML':self.varyWidth2Check.isChecked(),
                     'Scale': self.varyIntCheck.isChecked() and self.varyScaleCheck.isChecked(),
                     'Background0':self.varyBkgCheck.isChecked(),
                     'Cu':False,'Cl':False}
        model.set_variation(variation)

        return model

    def set_fit(self,model):
        self.fitted_model = model

        val = unc.ufloat(self.fitted_model.params['Centroid'].value,self.fitted_model.params['Centroid'].stderr)/29979.2458
        self.CentroidBox_fit.setText(str(val))
        val = unc.ufloat(self.fitted_model.params['Al'].value,self.fitted_model.params['Al'].stderr)
        self.ABox1_fit.setText(str(val))
        val = unc.ufloat(self.fitted_model.params['Au'].value,self.fitted_model.params['Au'].stderr)
        self.ABox2_fit.setText(str(val))
        val = unc.ufloat(self.fitted_model.params['Bl'].value,self.fitted_model.params['Bl'].stderr)
        self.BBox1_fit.setText(str(val))
        val = unc.ufloat(self.fitted_model.params['Bu'].value,self.fitted_model.params['Bu'].stderr)
        self.BBox2_fit.setText(str(val))
        val = unc.ufloat(self.fitted_model.params['FWHMG'].value,self.fitted_model.params['FWHMG'].stderr)
        self.WidthBox1_fit.setText(str(val))
        val = unc.ufloat(self.fitted_model.params['FWHML'].value,self.fitted_model.params['FWHML'].stderr)
        self.WidthBox2_fit.setText(str(val))
        val = unc.ufloat(self.fitted_model.params['Scale'].value,self.fitted_model.params['Scale'].stderr)
        self.ScaleBox_fit.setText(str(val))
        val = unc.ufloat(self.fitted_model.params['Background0'].value,self.fitted_model.params['Background0'].stderr)
        self.BkgBox_fit.setText(str(val))

    def toggle_fit(self):
        self.fit_button.setChecked(not self.fit_button.isChecked())
        self.do_fitting()

    def do_fitting(self):
        self.fitPeakSig.emit()
