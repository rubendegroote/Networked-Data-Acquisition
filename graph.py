import pyqtgraph as pg
from PyQt4 import QtCore,QtGui
import pyqtgraph.dockarea as da
import datetime
import numpy as np
import pandas as pd
from picbutton import PicButton


class GraphDock(pg.dockarea.Dock):

    def __init__(self, name):
        super(GraphDock, self).__init__(name)
        self.graph = MyGraph(name)
        self.layout.addWidget(self.graph)


class MyGraph(QtGui.QWidget):

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

        self.curve = pg.PlotCurveItem()
        self.graph.addItem(self.curve)


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

        self.graphStyles = ['Step (histogram)', 'Line']#, 'Point']

        self.graphBox = QtGui.QComboBox(self)
        self.graphBox.setToolTip('Choose how you want to plot the data:\
 as a binned histogram, or the raw data. The latter strains the pc a lot though!')
        self.graphBox.addItems(self.graphStyles)
        self.graphBox.setCurrentIndex(0)
        self.graphBox.setMaximumWidth(110)
        # self.graphBox.currentIndexChanged.connect(self.updatePlot)
        self.sublayout.addWidget(self.graphBox, 0, 5)

        self.binLabel = QtGui.QLabel(self, text="Bin size: ")
        self.binSpinBox = pg.SpinBox(value=1000,
                                     bounds=(0, None),
                                     dec=False)
        self.binSpinBox.setToolTip('Choose the bin size\
 used to bin the data.')
        self.binSpinBox.setMaximumWidth(110)
        # self.binSpinBox.sigValueChanged.connect(self.updatePlot)

        self.sublayout.addWidget(self.binLabel, 2, 4)
        self.sublayout.addWidget(self.binSpinBox, 2, 5)

        self.sublayout.addWidget(QtGui.QLabel("y offset"),2,0)
        self.y_offset = QtGui.QLineEdit("0")
        self.sublayout.addWidget(self.y_offset, 2, 1)

        self.sublayout.addWidget(QtGui.QLabel("x offset"),2,2)
        self.x_offset = QtGui.QLineEdit("0")
        self.sublayout.addWidget(self.x_offset, 2, 3)

        self.sublayout.setColumnStretch(6, 1)
        self.layout.addWidget(gView, 0, 0)

    def calcHist(self, x, y, binsize):

        binsize = binsize * 1.
        x, y = np.array(x, dtype=float), np.array(y, dtype=float)

        if x[0] < x[-1]:
            bins = np.arange(min(x)-binsize/2, max(x) + binsize/2, binsize)
        else:
            start = round(min(x)/binsize) * binsize
            bins = np.arange(start-binsize/2, max(x) + binsize/2, binsize)

        bin_means, edges = np.histogram(x, bins, weights=y)

        errors = np.sqrt(bin_means + 1)

        scale = np.histogram(x, bins)[0]

        bin_means = bin_means / scale
        errors = errors / scale

        return edges, bin_means, errors

    def setXYOptions(self, options):
        self.options = ['device: parameter']
        self.options.extend([key+': '+v for key,val in options.items() for v in val])

        self.comboX.addItems(self.options)
        self.comboY.addItems(self.options)

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
        histmode = str(self.graphBox.currentText()) == 'Step (histogram)'

        if len(self.data)>0:
            data = self.data.sort_index()
            data['x'].fillna(method='ffill', inplace=True)
            data.dropna(inplace=True)
            if 'timestamp' in self.x_key:
                data['x'] = data['x'] - data['x'].values[0]
            elif 'timestamp' in self.y_key:
                data['y'] = data['y'] - data['y'].values[0]
            
            x = data['x'].values - float(self.x_offset.text())
            y = data['y'].values - float(self.y_offset.text())

            print(len(x),len(y))

            if histmode:
                binsize = self.binSpinBox.value()
                x, y, errors = self.calcHist(x, y, binsize)

            self.curve.setData(x, y,
                               pen='r',
                               # fillLevel=0,
                               stepMode=histmode,
                               brush='g')
