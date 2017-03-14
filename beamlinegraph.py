from PyQt5 import QtCore, QtGui, QtWidgets
import pyqtgraph as pg
import numpy as np
from spin import Spin
import time
import pandas as pd

pg.setConfigOption('background', 'w')
pg.setConfigOption('foreground', 'k')


class BeamlineGraph(QtWidgets.QWidget):
    def __init__(self):
        super(BeamlineGraph,self).__init__()

        self.init_UI()
        self.curve = pg.PlotCurveItem()
        self.avCurve = pg.PlotCurveItem()
        self.plotWidget.addItem(self.curve)
        self.plotWidget.addItem(self.avCurve)

        self.current_mode = True

        self.data = pd.DataFrame({'t_curr':[],'t_c':[],'current':[], 'counts':[]})

    def init_UI(self):
        self.layout = QtWidgets.QGridLayout(self)
        self.labelStyle = {'font-size': '18pt'}

        self.plotWidget = pg.PlotWidget()
        self.time_zoom = QtGui.QCheckBox("Time zoom")
        self.time_select = Spin()
        self.window_select = Spin()

        self.layout.addWidget(self.plotWidget,0,0,100,100)
        self.layout.addWidget(self.time_zoom,100,0,1,1)
        self.layout.addWidget(self.time_select,100,1,1,1)
        self.layout.addWidget(QtWidgets.QLabel("Mean window size"),100,2,1,1)
        self.layout.addWidget(self.window_select,100,3,1,1)

        self.layout.addWidget(QtWidgets.QLabel('Current'),101,0,1,1)
        self.current_value = pg.SpinBox(suffix='A', siPrefix=True)
        self.layout.addWidget(self.current_value,101,1,1,2)


    def plot(self,track,params):
        
        if self.current_mode:
            y_str = 'current'
            x_str = 't_curr'
        else:
            y_str = 'counts'
            x_str = 't_c'

        window_size = int(self.window_select.value)
        offset = self.data[x_str].values[-1]

        if self.time_zoom.isChecked():
            t_val = int(self.time_select.value)

            x,y = self.data[x_str][-t_val:].values,\
                  self.data[y_str][-t_val:].values
        else:
            t_val = 0
            x,y = self.data[x_str].values,self.data[y_str].values
        self.curve.setData(x - offset,y,pen = 'b')

        if window_size > 0:
            x = self.data[x_str][-t_val+window_size:].values
            y = self.data[y_str][-t_val+window_size:].values
            self.current_value.setValue(y[-1])
            y_av = pd.rolling_mean(y, window_size)

            self.avCurve.setData(x[-t_val:] - offset,y_av[-t_val:],pen = pg.mkPen('r', width=3))


