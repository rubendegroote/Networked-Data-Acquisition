import pyqtgraph as pg
from spin import Spin

pg.setConfigOption('background', 'w')
pg.setConfigOption('foreground', 'k')

class BeamlineGraph(pg.PlotWidget):
    def __init__(self):
        super(BeamlineGraph,self).__init__()

        self.init_UI()

    def init_UI(self):
        self.layout = QtGui.QGridLayout(self)
        self.labelStyle = {'font-size': '18pt'}

        self.time_zoom = QtGui.QCheckBox()
        self.time_select = Spin()

    ### subclass the autorange or something? Or disable it 
    ### and manually do it?

