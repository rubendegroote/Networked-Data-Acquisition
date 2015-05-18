import pyqtgraph as pg
from PyQt4 import QtCore,QtGui
from graph import GraphDock

class CentralDock(pg.dockarea.DockArea):

    def __init__(self):
        super(CentralDock,self).__init__()
        self.createUIDocks()

    def createUIDocks(self):
        self.graphDocks = []
        self.graphDocks.append(GraphDock('Test'))
        self.addDock(self.graphDocks[-1])