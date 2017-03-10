import pyqtgraph as pg
from PyQt4 import QtCore,QtGui
import pyqtgraph.dockarea as da
import datetime
import numpy as np
import pandas as pd
from picbutton import PicButton
import time
import pyqtgraph.exporters
import webbrowser
import lmfit as lm

from backend.Helpers import calcHist

class XYGraph(QtGui.QWidget):

    dataRequested = QtCore.pyqtSignal(str)
    scanRequested = QtCore.pyqtSignal(str)
    def __init__(self, name):
        super(QtGui.QWidget, self).__init__()

        self.reset = False
        self.options = []
        self.name = name
        self.formats = {}
        self.data = pd.DataFrame()
        self.x_key = []
        self.y_key = []

        self.bins = np.zeros(1)
        self.init_UI()
        
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.plot)
        self.timer.start(50)

        # self.timer2 = QtCore.QTimer()
        # self.timer2.timeout.connect(self.treat_data)
        # self.timer2.start(50)

    def init_UI(self):

        self.layout = QtGui.QGridLayout(self)

        self.labelStyle = {'font-size': '18pt'}

        gView = pg.GraphicsView()

        self.graph = pg.PlotWidget()
        self.graph.showGrid(x=True, y=True, alpha=0.2)

        self.error_curve = pg.ErrorBarItem(x=np.array([]),y=np.array([]),
                    top=np.array([]),bottom=np.array([]),beam=0.)
        self.graph.addItem(self.error_curve)

        self.points_curve = pg.ScatterPlotItem(x=np.array([]),y=np.array([]))
        self.graph.addItem(self.points_curve)

        layout = QtGui.QGridLayout(gView)
        layout.addWidget(self.graph, 0, 0, 1, 1)

        self.sublayout = QtGui.QGridLayout()
        layout.addLayout(self.sublayout, 1, 0)

        self.sublayout.addWidget(QtGui.QLabel('y: '),0,0)
        self.comboY = QtGui.QComboBox(parent=None)
        self.comboY.setMinimumWidth(250)
        self.comboY.setToolTip('Choose the variable you want to put\
 on the Y-axis.')
        self.sublayout.addWidget(self.comboY, 0, 1)

        self.sublayout.addWidget(QtGui.QLabel('x: '),0,2)
        self.comboX = QtGui.QComboBox(parent=None)
        self.comboX.setMinimumWidth(250)
        self.comboX.setToolTip('Choose the variable you want to put\
 on the X-axis.')
        self.sublayout.addWidget(self.comboX, 0, 3)


        self.graphStyles = ['sqrt','std dev','None']#, 'Point']

        label = QtGui.QLabel('Errors: ')
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

        label = QtGui.QLabel('data mode: ')
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

        self.binLabel = QtGui.QLabel(self, text="Bin size: ")
        self.prev_binsize = 1000
        self.binSpinBox = pg.SpinBox(value=self.prev_binsize,
                                     bounds=(0, None),
                                     dec=False)
        self.binSpinBox.setToolTip('Choose the bin size\
 used to bin the data.')
        self.binSpinBox.setMaximumWidth(110)
        self.sublayout.addWidget(self.binLabel, 2, 4)
        self.sublayout.addWidget(self.binSpinBox, 2, 5)

        self.sublayout.addWidget(QtGui.QLabel("y offset"),2,0)
        self.y_offset = QtGui.QLineEdit("0")
        self.y_offset.textChanged.connect(self.change_label)
        self.sublayout.addWidget(self.y_offset, 2, 1)

        self.sublayout.addWidget(QtGui.QLabel("x offset"),2,2)
        self.x_offset = QtGui.QLineEdit("0")
        self.x_offset.textChanged.connect(self.change_label)
        self.sublayout.addWidget(self.x_offset, 2, 3)

        self.sublayout.addWidget(QtGui.QLabel("x cut left"),3,0)
        self.x_cut_left = QtGui.QLineEdit("-10000000000")
        self.sublayout.addWidget(self.x_cut_left, 3, 1)

        self.sublayout.addWidget(QtGui.QLabel("x cut right"),3,2)
        self.x_cut_right = QtGui.QLineEdit("10000000000")
        self.sublayout.addWidget(self.x_cut_right, 3, 3)

        self.unit_check = QtGui.QCheckBox('Use MHz?')
        self.unit_check.stateChanged.connect(self.change_label)
        self.unit_check.setDisabled(True)
        self.sublayout.addWidget(self.unit_check, 2, 6)

        self.clean_stream = QtGui.QPushButton('Reset data')
        self.sublayout.addWidget(self.clean_stream, 2, 7, 1, 1)
        self.clean_stream.clicked.connect(self.clean)

        self.export_button = QtGui.QPushButton('Export (press ctrl+E!)')
        self.sublayout.addWidget(self.export_button, 3, 4, 1, 1)
        self.export_button.clicked.connect(self.export)
        QtGui.QShortcut(QtGui.QKeySequence("Ctrl+E"), self, self.export)

        self.fit_button = QtGui.QPushButton('Fitting Mode')
        self.fit_button.setCheckable(True)
        self.sublayout.addWidget(self.fit_button, 3, 5, 1, 1)
        self.fit_button.clicked.connect(self.fitting)


        self.sublayout.setColumnStretch(8, 1)
        self.layout.addWidget(gView, 0, 0)

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
                try:
                    if 'wavenumber' in self.x_key[1]:
                        x = curvePoint.x() + float(self.x_offset.text())
                        if self.unit_check.isChecked():
                            x = x / 29979.2458
                        self.posLabel.setHtml("<span style='font-size: 12pt'> <span style = 'color: black'> \
                            x=%0.5fcm-1,y=%0.5f</span>" % (x, curvePoint.y()))
                    else:
                        x = curvePoint.x()
                        self.posLabel.setHtml("<span style='font-size: 12pt'> <span style = 'color: black'> \
                            x=%0.5f,y=%0.5f</span>" % (x, curvePoint.y()))
                except:
                    x = curvePoint.x()
                    self.posLabel.setHtml("<span style='font-size: 12pt'> <span style = 'color: black'> \
                        x=%0.5f,y=%0.5f</span>" % (x, curvePoint.y()))
                vLine.setPos(curvePoint.x())
                hLine.setPos(curvePoint.y())
                self.posLabel.setPos(curvePoint.x(),curvePoint.y())
        self.graph.scene().sigMouseMoved.connect(mouseMoved)

        #####

    def clean(self):
        self.data = self.data.iloc[-10:]

    def setXYOptions(self, options):
        self.options = ['device: parameter']
        self.options.extend([key+': '+v for key,val in options.items() for v in val])

        self.comboX.addItems(self.options)
        try:
            self.comboX.setCurrentIndex(options.index('wavemeter: wavenumber_1'))
        except:
            self.comboX.setCurrentIndex(0)

        self.comboY.addItems(self.options)
        try:
            self.comboY.setCurrentIndex(options.index('CRIS: Counts'))
        except:
            self.comboY.setCurrentIndex(0)


        self.comboX.currentIndexChanged.connect(self.newXY)
        self.comboX.currentIndexChanged.connect(self.change_label)
        self.comboY.currentIndexChanged.connect(self.newXY)
        self.comboY.currentIndexChanged.connect(self.change_label)

    def newXY(self):
        new_xkey = str(self.comboX.currentText()).split(': ')
        new_ykey = str(self.comboY.currentText()).split(': ')

        if not 'device' in new_xkey and not 'device' in new_ykey:
            self.reset = True
            self.x_key = new_xkey
            self.y_key = new_ykey
        else:
            self.x_key = []
            self.y_key = []

        if 'wavenumber' in new_xkey[1] or 'wavenumber' in new_ykey[1]:
            self.unit_check.setEnabled(True)
        else:
            self.unit_check.setDisabled(True)
            self.unit_check.setChecked(False)

    def change_label(self):
        xkey = str(self.comboX.currentText()).split(': ')[1]
        ykey = str(self.comboY.currentText()).split(': ')[1]
        if 'wavenumber' in xkey:
            offset = float(self.x_offset.text())
            if self.unit_check.isChecked():
                offset = offset / 29979.2458
                self.graph.setLabel('bottom','Frequency (offset {} cm-1)'.format(offset),labelStyle = {'color': '#FFF', 'font-size': '24pt'})
            else:
                self.graph.setLabel('bottom','Wavenumber (offset {} cm-1)'.format(offset),labelStyle = {'color': '#FFF', 'font-size': '24pt'})
        else:
            self.graph.setLabel('bottom','',labelStyle = {'color': '#FFF', 'font-size': '24pt'})


        if 'wavenumber' in ykey:
            offset = float(self.y_offset.text())
            if self.unit_check.isChecked():
                offset = offset / 29979.2458
                self.graph.setLabel('left','Frequency (offset {} cm-1)'.format(offset),labelStyle = {'color': '#FFF', 'font-size': '24pt'})
            else:
                self.graph.setLabel('left','Wavenumber (offset {} cm-1)'.format(offset),labelStyle = {'color': '#FFF', 'font-size': '24pt'})
        elif 'Counts' in ykey:
            print(1)
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
                                
        self.reset = False

    def treat_data(self):
        data = self.data.sort_values(by='time')
        data['x'] = data['x'].fillna(method='ffill')
        data = data.dropna()

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

        start = np.min(data['x']) - np.min(data['x'])%binsize
        stop = np.max(data['x'])//binsize*binsize+binsize
        steps = np.round(abs(stop-start)/binsize,0)+1
        bins = np.linspace(start,stop,steps)

        self.bins = bins
        self.binned_data = calcHist(data, bins, self.errormode, self.data_mode)

    def plot(self):
        self.errormode = str(self.error_box.currentText())
        self.data_mode = str(self.data_box.currentText())

        if len(self.data)>0:
            self.treat_data()

            x = self.binned_data['x'].values - float(self.x_offset.text())
            y = self.binned_data['y'].values - float(self.y_offset.text())
            x_err = self.binned_data['xerr'].values
            y_err = self.binned_data['yerr'].values

            if not self.errormode == 'None':
                try:
                    self.error_curve.setData(x=x, y=y,top=y_err,bottom=y_err,
                                            left = x_err,right = x_err,
                                            pen='r',beam=0.)
                except:
                    self.error_curve = pg.ErrorBarItem(x=x, y=y,top=y_err,bottom=y_err,
                                            left = x_err,right = x_err,
                                            pen='r',beam=0.)
                    self.graph.addItem(self.error_curve)

                    self.graph.removeItem(self.curve)
                    del self.curve
                    
                try:
                    self.points_curve.setData(x=x, y=y)
                except:
                    self.points_curve = pg.ScatterPlotItem()
                    self.graph.addItem(self.points_curve)
                    self.points_curve.setData(x=x, y=y)
    
            else:
                try:
                    self.curve.setData(x=x, y=y,pen='r')
                except:
                    self.curve = pg.PlotCurveItem(x=x, y=y,pen='r')
                    self.graph.addItem(self.curve)
                    self.graph.removeItem(self.error_curve)
                    self.graph.removeItem(self.points_curve)
                    del self.error_curve
                    del self.points_curve


    def export(self):
        exporter = pg.exporters.ImageExporter(self.graph.plotItem)
        name = QtGui.QFileDialog.getSaveFileName(self, 'Save File')
        exporter.export(name)
        webbrowser.open(name)

    def peak_chooser(self,mousePoint):
        pos = self.graphvb.mapSceneToView(mousePoint.scenePos())
        self.peaks.append(pos.x())
        self.heights.append(pos.y())

        if len(self.peaks) == 1:
            self.fit_button.setChecked(False)
            self.do_fit()

    def fitting(self):
        if self.fit_button.isChecked():
            try:
                self.graph.removeItem(self.fitcurve)
                self.graph.removeItem(self.fit_text)
            except:
                pass

            self.peaks = []
            self.heights = []

            self.graph.scene().sigMouseClicked.connect(self.peak_chooser)


        else:
            self.do_fit()

    def do_fit(self):
        self.graph.scene().sigMouseClicked.disconnect(self.peak_chooser)

        x = self.binned_data['x'].values - float(self.x_offset.text())
        xerr = self.binned_data['xerr'].values
        y = self.binned_data['y'].values - float(self.y_offset.text())
        yerr = self.binned_data['yerr'].values

        w, ok = QtGui.QInputDialog.getText(self, 'FWHM Dialog', 'Enter estimated FHWM:')
        if not ok:
            return

        w = float(w)

        params = lm.Parameters()
        params.add('w',w)
        index = 0
        for p, h in zip(self.peaks,self.heights):
            params.add('p{}'.format(index),p)
            params.add('h{}'.format(index),h)

            index += 1

        def fitfunc(params,x):
            fit = np.zeros(len(x))
            for i in range(int((len(params)-1)/2)):
                fit += params['h{}'.format(i)].value*np.exp(-(x-params['p{}'.format(i)].value)**2/2/params['w'].value**2)

            return fit

        def resid(params,x,y,yerr):
            return (fitfunc(params,x) - y)/yerr

        x_fit = np.linspace(x.min(),x.max(),10**4)
        self.fitcurve = pg.PlotCurveItem(x=x_fit, y=fitfunc(params,x_fit),pen='b')
        self.graph.addItem(self.fitcurve)

        w, ok = QtGui.QInputDialog.getText(self, 'Fit Dialog', 'Fit?')
        if not ok:
            return

        results = lm.minimize(resid,params,args=(x,y,yerr))
        self.fitcurve.setData(x=x_fit,y=fitfunc(results.params,x_fit))
        html = '<div style="text-align: center">\
                <span>X:{}</span><br> \
                <span>Y:{}</span><br> \
                <span>W:{}</span>\
                </div>'.format(params['p0'].value, params['h0'].value,params['w'].value)

        self.fit_text = pg.TextItem(html=html, anchor=(-0.3,1.3), border='w', fill=(0, 0, 255, 100))
        self.graphvb.addItem(self.fit_text)
        self.fit_text.setPos(params['p0'].value, params['h0'].value)

