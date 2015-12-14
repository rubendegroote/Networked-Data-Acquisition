from PyQt4 import QtCore, QtGui
import pyqtgraph as pg
import numpy as np
from spin import Spin
import time
import pandas as pd

pg.setConfigOption('background', 'w')
pg.setConfigOption('foreground', 'k')


class BeamlineGraph(QtGui.QWidget):
    def __init__(self):
        super(BeamlineGraph,self).__init__()


        self.init_UI()
        self.curve = pg.PlotCurveItem()
        self.avCurve = pg.PlotCurveItem()
        self.plotWidget.addItem(self.curve)
        self.plotWidget.addItem(self.avCurve)

        self.data = pd.DataFrame({'x':[],'y':[]})

    def init_UI(self):
        self.layout = QtGui.QGridLayout(self)
        self.labelStyle = {'font-size': '18pt'}

        self.plotWidget = pg.PlotWidget()
        self.time_zoom = QtGui.QCheckBox("Time zoom")
        self.time_select = Spin()
        self.window_select = Spin()

        self.layout.addWidget(self.plotWidget,0,0,100,100)
        self.layout.addWidget(self.time_zoom,100,0,1,1)
        self.layout.addWidget(self.time_select,100,1,1,1)
        self.layout.addWidget(QtGui.QLabel("Mean window size"),100,2,1,1)
        self.layout.addWidget(self.window_select,100,3,1,1)

    def plot(self,track,params):
        if self.time_zoom.isChecked():
            x,y = self.data['x'][-self.time_select.value:].values,\
                  self.data['y'][-self.time_select.value:].values
        else:
            x,y = self.data['x'].values,self.data['y'].values
        self.curve.setData(x,y,pen = 'b')

        #calculate rolling average!
        y = pd.rolling_mean(y, self.window_select.value)
        self.avCurve.setData(x,y,pen = 'r')


