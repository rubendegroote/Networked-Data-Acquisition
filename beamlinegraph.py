from PyQt4 import QtCore, QtGui
import pyqtgraph as pg
import numpy as np
from spin import Spin

pg.setConfigOption('background', 'w')
pg.setConfigOption('foreground', 'k')

class BeamlineGraph(QtGui.QWidget):
    def __init__(self):
        super(BeamlineGraph,self).__init__()

        self.init_UI()
        self.teller = 0
        self.curve = pg.PlotCurveItem()
        self.plotWidget.addItem(self.curve)

    def init_UI(self):
        self.layout = QtGui.QGridLayout(self)
        self.labelStyle = {'font-size': '18pt'}

        self.plotWidget = pg.PlotWidget()
        self.time_zoom = QtGui.QCheckBox("Time zoom")
        self.time_select = Spin(text = "60")

        self.layout.addWidget(self.plotWidget,0,0,100,100)
        self.layout.addWidget(self.time_zoom,100,0,1,1)
        self.layout.addWidget(self.time_select,100,1,1,1)

    def plot(self,x,y):
        if self.time_zoom.isChecked():
            x,y = x[-self.time_select.value:],y[-self.time_select.value:]
        self.curve.setData(x,y,pen = 'r')

    def update(self,track,params):
        self.teller+=10
        x = np.linspace(0,self.teller,self.teller)
        y = np.random.rand(len(x))
        self.plot(x,y)