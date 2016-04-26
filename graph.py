import pyqtgraph as pg
from PyQt4 import QtCore,QtGui
import pyqtgraph.dockarea as da
import datetime
import numpy as np
import pandas as pd
from picbutton import PicButton

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

        self.buffer_size = 10**6

        self.init_UI()
        
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.plot)
        self.timer.start(50)

    def init_UI(self):

        self.layout = QtGui.QGridLayout(self)

        self.labelStyle = {'font-size': '18pt'}

        gView = pg.GraphicsView()

        self.graph = pg.PlotWidget()
        self.graph.showGrid(x=True, y=True, alpha=0.7)

        self.error_curve = pg.ErrorBarItem(x=np.array([]),y=np.array([]),
                    top=np.array([]),bottom=np.array([]),beam=0.)
        self.graph.addItem(self.error_curve)

        self.points_curve = pg.ScatterPlotItem()
        self.graph.addItem(self.points_curve)

        layout = QtGui.QGridLayout(gView)
        layout.addWidget(self.graph, 0, 0, 1, 1)

        self.sublayout = QtGui.QGridLayout()
        layout.addLayout(self.sublayout, 1, 0)

        self.comboY = QtGui.QComboBox(parent=None)
        self.comboY.setMinimumWidth(250)
        self.comboY.setToolTip('Choose the variable you want to put\
 on the Y-axis.')
        self.sublayout.addWidget(self.comboY, 0, 1)

        label = QtGui.QLabel('vs')
        label.setStyleSheet("border: 0px;")
        self.sublayout.addWidget(label, 0, 2)

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
        self.data_box.setToolTip('Choose if you want the sum or mean of the data per bin')
        self.data_box.addItems(['sum','mean'])
        self.data_box.setCurrentIndex(0)
        self.data_box.setMaximumWidth(110)
        # self.error_box.currentIndexChanged.connect(self.updatePlot)
        self.sublayout.addWidget(self.data_box, 0, 7)

        self.binLabel = QtGui.QLabel(self, text="Bin size: ")
        self.binSpinBox = pg.SpinBox(value=1000,
                                     bounds=(0, None),
                                     dec=False)
        self.binSpinBox.setToolTip('Choose the bin size\
 used to bin the data.')
        self.binSpinBox.setMaximumWidth(110)
        self.sublayout.addWidget(self.binLabel, 2, 4)
        self.sublayout.addWidget(self.binSpinBox, 2, 5)

        self.sublayout.addWidget(QtGui.QLabel("y offset"),2,0)
        self.y_offset = QtGui.QLineEdit("0")
        self.sublayout.addWidget(self.y_offset, 2, 1)

        self.sublayout.addWidget(QtGui.QLabel("x offset"),2,2)
        self.x_offset = QtGui.QLineEdit("0")
        self.sublayout.addWidget(self.x_offset, 2, 3)

        self.sublayout.addWidget(QtGui.QLabel("x cut left"),3,0)
        self.x_cut_left = QtGui.QLineEdit("0")
        self.sublayout.addWidget(self.x_cut_left, 3, 1)

        self.sublayout.addWidget(QtGui.QLabel("x cut right"),3,2)
        self.x_cut_right = QtGui.QLineEdit("9000000")
        self.sublayout.addWidget(self.x_cut_right, 3, 3)

        self.clean_stream = QtGui.QPushButton('Reset data')
        self.sublayout.addWidget(self.clean_stream, 4, 5, 1, 1)
        self.clean_stream.clicked.connect(self.clean)

        self.sublayout.setColumnStretch(8, 1)
        self.layout.addWidget(gView, 0, 0)

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
        self.comboY.currentIndexChanged.connect(self.newXY)

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

    def reset_data(self):
        self.no_of_rows = {k:0 for k in self.formats.keys()}
        
        self.data = pd.DataFrame({'time':[],
                                  'x':[],
                                  'y':[]})
        self.data.set_index(['time'],inplace=True)
                                
        self.reset = False

    def plot(self):
        errormode = str(self.error_box.currentText())
        data_mode = str(self.data_box.currentText())

        if len(self.data)>0:
            if len(self.data) > self.buffer_size:
                self.data = self.data.iloc[-self.buffer_size:]
            data = self.data.sort_index()
            data['x'].fillna(method='ffill', inplace=True)
            data.dropna(inplace=True)
            if 'timestamp' in self.x_key:
                data['x'] = data['x'] - data['x'].values[0]
            elif 'timestamp' in self.y_key:
                data['y'] = data['y'] - data['y'].values[0]
            
            max_x = float(self.x_cut_right.text())
            min_x = float(self.x_cut_left.text())
            slicer = np.logical_and(data['x']<max_x,data['x']>min_x)
            data = data[slicer]
            
            binsize = self.binSpinBox.value()
            bins = np.arange(np.min(data['x']), np.max(data['x'])+binsize, binsize)
            noe, x, x_err, y, y_err = calcHist(data, bins, errormode, data_mode)
            noe, x, x_err, y, y_err = noe[noe>0], \
                                      x[noe>0], \
                                      x_err[noe>0], \
                                      y[noe>0], \
                                      y_err[noe>0]
            
            x = x - float(self.x_offset.text())
            y = y - float(self.y_offset.text())

            if not errormode == 'None':
                try:
                    self.error_curve.setData(x=x, y=y,top=y_err,bottom=y_err,
                                            left = x_err,right = x_err,
                                            pen='r',beam=0.,lw=3)
                except:
                    self.error_curve = pg.ErrorBarItem(x=x, y=y,top=y_err,bottom=y_err,
                                            left = x_err,right = x_err,
                                            pen='r',beam=0.,lw=3)
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
                    self.curve = pg.PlotCurveItem(x=x, y=y,pen='r',lw=3)
                    self.graph.addItem(self.curve)
                    self.graph.removeItem(self.error_curve)
                    self.graph.removeItem(self.points_curve)
                    del self.error_curve
                    del self.points_curve
