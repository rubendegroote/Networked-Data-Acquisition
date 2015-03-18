from PyQt4 import QtCore,QtGui
from scanner import ScannerWidget
from connect import ConnectionsWidget
from central import CentralDock

from backend.DataServer import DataServer

class Application(QtGui.QMainWindow):
    def __init__(self):
        super(Application, self).__init__()
        self.init_UI()

    def init_UI(self):

        self.connectToolBar = QtGui.QToolBar('Connections')
        self.connectToolBar.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.addToolBar(self.connectToolBar)

        self.connectionsWidget = ConnectionsWidget()
        self.connectionsWidget.newConn.connect(self.addConnection)
        self.connectToolBar.addWidget(self.connectionsWidget)

        self.centralDock = CentralDock()
        self.setCentralWidget(self.centralDock)

        self.show()

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.plot)
        self.timer.start(50)

    def addConnection(self,data):
        if data[0] == 'Server':
            self.dataServer = DataServer(artists=[(data[1],data[2])], 
                                         save=False, remember=True)
        
    def plot(self):
        try:
            for graph in self.centralDock.graphs:
                graph.plot(self.dataServer._data)
        except AttributeError:
            pass

    def closeEvent(self,event):
        try:
            self.dataServer.stop()
        except Exception as e:
            print(e)

        event.accept()