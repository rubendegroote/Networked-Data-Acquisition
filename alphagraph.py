import pyqtgraph as pg
from PyQt4 import QtCore,QtGui
import pyqtgraph.dockarea as da
import datetime
import numpy as np
import pandas as pd
from picbutton import PicButton

from backend.Helpers import calcHist

class AlphaGraph(QtGui.QWidget):
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

        self.graphStyles = ['sqrt','std dev','None']#, 'Point']

        self.graph = Graph()
        self.layout.addWidget(self.graph,0,0,1,10)

        self.binLabel = QtGui.QLabel(self, text="Bin size: ")
        self.binSpinBox = pg.SpinBox(value=1000,
                                     bounds=(0, None),
                                     dec=False)
        self.binSpinBox.setToolTip('Choose the bin size\
 used to bin the data.')
        self.binSpinBox.setMaximumWidth(110)
        self.layout.addWidget(self.binLabel, 3, 4)
        self.layout.addWidget(self.binSpinBox, 3, 5)

        self.layout.addWidget(QtGui.QLabel("y offset"),2,0)
        self.y_offset = QtGui.QLineEdit("0")
        self.layout.addWidget(self.y_offset, 2, 1)

        self.layout.addWidget(QtGui.QLabel("x offset"),2,2)
        self.x_offset = QtGui.QLineEdit("0")
        self.layout.addWidget(self.x_offset, 2, 3)

        self.layout.addWidget(QtGui.QLabel("x cut left"),3,0)
        self.x_cut_left = QtGui.QLineEdit("13095")
        self.layout.addWidget(self.x_cut_left, 3, 1)

        self.layout.addWidget(QtGui.QLabel("x cut right"),3,2)
        self.x_cut_right = QtGui.QLineEdit("13097")
        self.layout.addWidget(self.x_cut_right, 3, 3)

        self.clean_stream = QtGui.QPushButton('Reset data')
        self.layout.addWidget(self.clean_stream, 3, 6, 1, 1)
        self.clean_stream.clicked.connect(self.clean)

        self.layout.setColumnStretch(8, 1)

    def clean(self):
        self.data = self.data.iloc[-10:]

    def reset_data(self):
        self.no_of_rows = {k:0 for k in self.formats.keys()}
        
        self.data = pd.DataFrame({'time':[],
                                  'x':[],
                                  'y':[]})
        self.data.set_index(['time'],inplace=True)
                                
        self.reset = False

    def plot(self):
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

            self.graph.hfs_plot.data = data
            self.graph.hfs_plot.binsize = self.binSpinBox.value()
            
            binsize = 10
            alpha_bins = np.arange(np.min(data['y']), np.max(data['y'])+binsize, binsize)
            self.graph.alpha_plot.counts,self.graph.alpha_plot.energies = np.histogram(data['y'].values,alpha_bins)

        self.graph.update_plots()


class Graph(QtGui.QWidget):
    def __init__(self):
        super(Graph,self).__init__()

        self.layout = QtGui.QGridLayout(self)

        self.alpha_plot = AlphaPlot()
        self.layout.addWidget(self.alpha_plot,0,1)
        self.hfs_plot = HFSPlot()
        self.layout.addWidget(self.hfs_plot,0,0)

    def data_reply(self,track,params):
        self.data = params['data']
        self.alpha_plot.data = self.data
        self.hfs_plot.data = self.data

    def update_plots(self):
        self.alpha_plot.update_plot()

        gates = [region.getRegion() for region in self.alpha_plot.regions]
        for i,gate in enumerate(gates):
            self.hfs_plot.plot_gated(i,gate)

BRUSH = [(0, 255, 0, 100.),(0, 0, 255, 100.),(255,128,0,100),(255, 0, 0, 100.),(128,128,0,100),(128,0,128,100)]
class AlphaPlot(QtGui.QWidget):
    def __init__(self):
        super(AlphaPlot,self).__init__()
        self.layout = QtGui.QGridLayout(self)
        self.plot = pg.PlotWidget()
        self.layout.addWidget(self.plot, 0,0,1,10)

        self.regions = []

        self.add_region_button = QtGui.QPushButton('Add energy gate')
        self.add_region_button.clicked.connect(self.add_region)
        self.layout.addWidget(self.add_region_button, 1,0,1,1)

        self.curve = pg.PlotCurveItem()
        self.plot.addItem(self.curve)

    def add_region(self):
        bounds = [5000,5100]

        self.regions.append(pg.LinearRegionItem(values = bounds,
                    movable=True,
                    brush = pg.mkBrush(BRUSH[len(self.regions)%len(BRUSH)])))
        self.plot.addItem(self.regions[-1])

    def update_plot(self):
        try:
            self.curve.setData(self.energies,self.counts,stepMode = True,pen = 'r')
        except Exception as e:
            pass

PEN = [(0, 255, 0, 255.),(0, 0, 255, 255.),(255,128,0,255),(255, 0, 0, 255.),(128,128,0,255),(128,0,128,255)]
class HFSPlot(QtGui.QWidget):
    def __init__(self):
        super(HFSPlot,self).__init__()
        self.layout = QtGui.QGridLayout(self)
        self.plot = pg.PlotWidget()
        self.layout.addWidget(self.plot)

        self.curves = {}

        self.x_selector = QtGui.QComboBox()
        self.x_selector.addItems(['time','wavenumber_1'])
        self.layout.addWidget(self.x_selector,1,0,1,1)

    def plot_gated(self,index,gate):
        try:
            self.curves[index]
        except:
            self.curves[index] = pg.PlotCurveItem()
            self.plot.addItem(self.curves[index])
        
        data = self.data
        binsize = self.binsize

        data = data[data['y']>gate[0]]
        data = data[data['y']<gate[1]]

        if self.x_selector.currentText() == 'time':
            data['time'],data['x'] = data['x'],data.index.values

        bins = np.arange(np.min(data['x']), np.max(data['x'])+binsize, binsize)
        try:
            noe, x, x_err, y, y_err = calcHist(data, bins, 'sqrt', 'mean')
            noe, x, x_err, y, y_err = noe[noe>0], \
                                      x[noe>0], \
                                      x_err[noe>0], \
                                      y[noe>0], \
                                      y_err[noe>0]
     
            rate = noe / (data.index.values.max()-data.index.values.min())

            self.curves[index].setData(x = x, y = rate,pen = PEN[index%len(PEN)])
        except:
            self.curves[index].setData(x = [], y = [],pen = PEN[index%len(PEN)])
