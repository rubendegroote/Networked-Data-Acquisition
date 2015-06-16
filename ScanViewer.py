from PyQt4 import QtCore, QtGui
import threading as th
import asyncore
import time
import numpy as np
import pandas as pd
import pyqtgraph as pg

from central import CentralDock
from picbutton import PicButton


class ScanDisplayApp(QtGui.QMainWindow):

    def __init__(self, data, parent):
        super(ScanDisplayApp, self).__init__(parent)
        self.looping = True

        self.data = pd.read_hdf(data, key='ABU')

        self.init_UI()
        self.show()

    def init_UI(self):

        self.options = self.data.columns.tolist() + ['time']
        print(self.options)
        print(self.data.head())

        self.central = QtGui.QWidget()
        # self.layout = QtGui.QGridLayout(self.central)
        self.layout = pg.LayoutWidget(self.central)
        self.setCentralWidget(self.central)

        self.labelStyle = {'font-size': '18pt'}

        self.graph = pg.PlotWidget()
        self.graph.showGrid(x=True, y=True, alpha=0.2)
        self.layout.addWidget(self.graph)
        self.layout.nextRow()

        self.curve = pg.PlotCurveItem()

        self.comboY = QtGui.QComboBox(parent=None)
        self.comboY.setToolTip('Choose the variable you want to put\
 on the Y-axis.')
        self.comboY.addItems(self.options)
        self.layout.addWidget(self.comboY)

        label = QtGui.QLabel('vs')
        label.setStyleSheet("border: 0px;")
        self.layout.addWidget(label)

        self.comboX = QtGui.QComboBox(parent=None)
        self.comboX.setToolTip('Choose the variable you want to put\
 on the X-axis.')
        self.comboX.addItems(self.options)
        self.layout.addWidget(self.comboX)
        self.layout.nextRow()

 #        self.freqUnitSelector = QtGui.QComboBox(parent=None)
 #        self.freqUnitSelector.setToolTip('Choose the units you want to\
 # display the frequency in.')
 #        self.freqUnitSelector.addItems(['Frequency', 'Wavelength', 'Wavenumber'])
 #        self.freqUnitSelector.currentIndexChanged.connect(self.updatePlot)
 #        self.sublayout.addWidget(self.freqUnitSelector, 0, 5)

        self.graphStyles = ['Step (histogram)', 'Line']#, 'Point']

        self.graphBox = QtGui.QComboBox(self)
        self.graphBox.setToolTip('Choose how you want to plot the data:\
 as a binned histogram, or the raw data. The latter strains the pc a lot though!')
        self.graphBox.addItems(self.graphStyles)
        self.graphBox.setCurrentIndex(0)
        self.graphBox.setMaximumWidth(110)
        self.graphBox.currentIndexChanged.connect(self.newXY)
        self.layout.addWidget(self.graphBox)

        self.binLabel = QtGui.QLabel(self, text="Bin size: ")
        self.binSpinBox = pg.SpinBox(value=1000,
                                     bounds=(0, None),
                                     dec=False)
        self.binSpinBox.setToolTip('Choose the bin size\
 used to bin the data.')
        self.binSpinBox.setMaximumWidth(110)
        self.binSpinBox.sigValueChanged.connect(self.newXY)

        self.layout.addWidget(self.binLabel)
        self.layout.addWidget(self.binSpinBox)
        self.layout.nextRow()

        self.saveButton = PicButton('save', checkable=False, size=25)
        self.saveButton.setToolTip('Save the current graph to file.')
        # self.saveButton.clicked.connect(self.saveSpectrum)
        self.layout.addWidget(self.saveButton)

        self.settingsButton = PicButton('settings', checkable=True, size=25)
        self.settingsButton.setToolTip('Display the advanced plotting options.')
        # self.settingsButton.clicked.connect(self.showSettings)
        self.layout.addWidget(self.settingsButton)

        self.comboY.currentIndexChanged.connect(self.newXY)
        self.comboX.currentIndexChanged.connect(self.newXY)
        for i, opt in enumerate(self.options):
            if 'wavenumber' in opt:
                self.comboX.setCurrentIndex(i)
            elif 'count' in opt:
                self.comboY.setCurrentIndex(i)

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

    def plot(self, data):

        if (not self.xkey == '') and (not self.ykey == ''):
            timePlot = True
            if self.xkey == 'time':
                data = data[self.ykey]
            elif self.ykey == 'time':
                data = data[self.xkey]
            else:
                data = data[[self.xkey, self.ykey]]
                timePlot = False
            try:
                self.graph.clear()
                histmode = str(self.graphBox.currentText()) == 'Step (histogram)'
                if not timePlot:
                    columns = data.columns.values
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
                                       # fillLevel=0,
                                       stepMode=histmode,
                                       brush='g')
                else:
                    data.dropna(inplace=True)
                    times = np.array([t.item() / 10**9 for t in (data.index.values - np.datetime64('1970-01-01T00:00Z'))])
                    data = data.values
                    if histmode:
                        binsize = self.binSpinBox.value()
                        times, data, errors = self.calcHist(times, data, binsize)
                    times = times - np.min(times)

                    self.curve = pg.PlotCurveItem(times, data,
                                                  pen='r',
                                                  # fillLevel=0,
                                                  stepMode=histmode,
                                                  brush='g')
                self.graph.addItem(self.curve)
            except Exception as e:
                print(e)

    def newXY(self):
        self.xkey = str(self.comboX.currentText())
        self.ykey = str(self.comboY.currentText())
        self.plot(self.data)
