import pyqtgraph as pg
from PyQt4 import QtCore,QtGui
import pyqtgraph.dockarea as da
import datetime
import numpy as np

from picbutton import PicButton


class GraphDock(pg.dockarea.Dock):
    
    def __init__(self, name):
        super(GraphDock,self).__init__(name)
        self.graph = MyGraph(name)
        self.layout.addWidget(self.graph)


class MyGraph(QtGui.QWidget):

    dataRequested = QtCore.pyqtSignal(str)
    
    def __init__(self, name):
        super(QtGui.QWidget,self).__init__()

        self.options = []
        self.name = name
        self.xkey = ''
        self.ykey = ''

        self.layout = QtGui.QGridLayout(self)

        self.labelStyle = {'font-size': '18pt'}

        gView = pg.GraphicsView()

        self.graph = pg.PlotWidget()
        self.graph.showGrid(x=True, y=True, alpha=0.7)

        self.curve = pg.PlotCurveItem()

        layout = QtGui.QGridLayout(gView)
        layout.addWidget(self.graph, 0, 0, 1, 1)

        self.sublayout = QtGui.QGridLayout()
        layout.addLayout(self.sublayout, 1, 0)

        self.comboY = QtGui.QComboBox(parent=None)
        self.comboY.setToolTip('Choose the variable you want to put\
 on the Y-axis.')
        self.comboY.currentIndexChanged.connect(self.newXY)
        self.sublayout.addWidget(self.comboY, 0, 1)

        label = QtGui.QLabel('vs')
        label.setStyleSheet("border: 0px;");
        self.sublayout.addWidget(label, 0, 2)

        self.comboX = QtGui.QComboBox(parent=None)
        self.comboX.setToolTip('Choose the variable you want to put\
 on the X-axis.')
        self.comboX.currentIndexChanged.connect(self.newXY)
        self.sublayout.addWidget(self.comboX, 0, 3)

 #        self.mathCheckBox = QtGui.QCheckBox('Mathy math math')
 #        self.mathCheckBox.setToolTip('Check this box if you want to do some\
 # math on the data before it is plotted.')
 #        self.mathCheckBox.stateChanged.connect(self.enableMathPanel)
 #        self.sublayout.addWidget(self.mathCheckBox, 1, 0)

        self.freqUnitSelector = QtGui.QComboBox(parent=None)
        self.freqUnitSelector.setToolTip('Choose the units you want to\
 display the frequency in.')
        self.freqUnitSelector.addItems(['Frequency','Wavelength','Wavenumber'])
        # self.freqUnitSelector.currentIndexChanged.connect(self.updatePlot)
        self.sublayout.addWidget(self.freqUnitSelector, 0, 5)

        self.meanStyles = ['Combined', 'Per Capture', 'Per Scan']
        self.meanBox = QtGui.QComboBox(self)
        self.meanBox.setToolTip('Choose how you want to combine data\
 from all of the scans in the captures this graph plots.')
        self.meanBox.addItems(self.meanStyles)
        self.meanBox.setCurrentIndex(1)
        self.meanBox.setMaximumWidth(110)
        # self.meanBox.currentIndexChanged.connect(self.updatePlot)
        self.meanBox.currentIndexChanged.connect(lambda: self.dataRequested.emit(str(self.meanBox.currentText())))
        self.dataRequested.emit(str(self.meanBox.currentText()))
        self.sublayout.addWidget(self.meanBox, 2, 1)

        self.graphStyles = ['Step (histogram)', 'Line']#, 'Point']

        self.graphBox = QtGui.QComboBox(self)
        self.graphBox.setToolTip('Choose how you want to plot the data:\
 as a binned histogram, or the raw data. The latter strains the a lot pc though!')
        self.graphBox.addItems(self.graphStyles)
        self.graphBox.setCurrentIndex(0)
        self.graphBox.setMaximumWidth(110)
        # self.graphBox.currentIndexChanged.connect(self.updatePlot)
        self.sublayout.addWidget(self.graphBox, 2, 2)

        self.binLabel = QtGui.QLabel(self, text="Bin size: ")
        self.binSpinBox = pg.SpinBox(value=1000,
                                     bounds=(0, None),
                                     dec=False)
        self.binSpinBox.setToolTip('Choose the bin size\
 used to bin the data.')
        self.binSpinBox.setMaximumWidth(110)
        # self.binSpinBox.sigValueChanged.connect(self.updatePlot)
        
        self.sublayout.addWidget(self.binLabel, 2, 3)
        self.sublayout.addWidget(self.binSpinBox, 2, 4)

        self.saveButton = PicButton('save', checkable=False, size=25)
        self.saveButton.setToolTip('Save the current graph to file.')
        # self.saveButton.clicked.connect(self.saveSpectrum)
        self.sublayout.addWidget(self.saveButton, 0, 7, 1, 1)

        self.settingsButton = PicButton('settings', checkable=True, size=25)
        self.settingsButton.setToolTip('Display the advanced plotting options.')
        # self.settingsButton.clicked.connect(self.showSettings)
        self.sublayout.addWidget(self.settingsButton, 0, 8, 1, 1)

        self.sublayout.setColumnStretch(6, 1)

        # self.settingsWidget = GraphSettingsWidget()
        # self.settingsWidget.updatePlot.connect(self.updatePlot)
        # self.meanBox.currentIndexChanged.connect(self.settingsWidget.onStyleChanged) 
            #line above is MEGAHACK to have updating results table in analysiswidget
        # self.settingsWidget.setVisible(False)

        self.layout.addWidget(gView, 0, 0)
        # self.layout.addWidget(self.settingsWidget,0,1)

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

        return edges,bin_means,errors

    def plot(self, data):
        try:
            self.graph.clear()
            columns = data.columns.values
            histmode = str(self.graphBox.currentText()) == 'Step (histogram)'
            if len(columns) == 2:
                data.sort_index(inplace=True)
                data[columns[0]].fillna(method='bfill', inplace=True)
                data.dropna(inplace=True)
                x = data[columns[0]].values
                y = data[columns[1]].values
                if histmode:
                    binsize = self.binSpinBox.value()
                    x, y, errors = self.calcHist(x, y, binsize)
                self.curve.setData(x, y,
                                   pen='r',
                                   fillLevel=0,
                                   stepMode=histmode,
                                   brush='g')
            elif len(columns) == 1:
                data.dropna(inplace=True)
                time = np.array([t.item() / 10**9 for t in (data.index.values - np.datetime64('1970-01-01T00:00Z'))])
                data = data[columns[0]].values
                if histmode:
                    binsize = self.binSpinBox.value()
                    time, data, errors = self.calcHist(time, data, binsize)
                self.curve = pg.PlotCurveItem(time, data,
                                              pen='r',
                                              fillLevel=0,
                                              stepMode=histmode,
                                              brush='g')
            self.graph.addItem(self.curve)
        except Exception as e:
            print(e)

    def setXYOptions(self, options):
        options.append('time')
        if not options == self.options:
            self.options = options
            curX = int(self.comboX.currentIndex())
            curY = int(self.comboY.currentIndex())
            self.comboX.clear()
            self.comboX.addItems(options)

            self.comboY.clear()
            self.comboY.addItems(options)

            self.comboX.setCurrentIndex(curX)
            self.comboY.setCurrentIndex(curY)

        else:
            pass

    def newXY(self):
        self.xkey = str(self.comboX.currentText())
        self.ykey = str(self.comboY.currentText())

    def updatePlot(self):
        self.clearPlot()
        self.setXY()
        self.plot()
