from PyQt4 import QtCore,QtGui
from connectiondialogs import ConnectionDialog

class ArtistConnections(QtGui.QWidget):
    connectSig = QtCore.Signal(tuple)
    removeSig = QtCore.Signal(tuple)
    def __init__(self, parent=None):
        super(ArtistConnections,self).__init__(parent)
        self.connections = {}
        self.l = 0
        self.layout = QtGui.QGridLayout(self)

        self.addArtistButton = QtGui.QPushButton('Add Artist')
        self.addArtistButton.clicked.connect(lambda:self.addConnection())
        self.layout.addWidget(self.addArtistButton,100,0,1,1)

    def addConnection(self):
        respons = ConnectionDialog.getInfo(self)
        if respons[1]:
            self.connectSig.emit(('Both',respons[0]))

    def addConnectionWidget(self,name='',IP='KSF402',PORT='5004'):
        self.connections[name] = ConnectionWidget(self,name,IP,PORT)
        self.connections[name].removeSig.connect(self.remove)
        self.connections[name].reconnectSig.connect(self.reconnect)
        self.layout.addWidget(self.connections[name],self.l,0,1,1)

        self.l += 1

    def remove(self,connWidget):
        self.removeSig.emit((connWidget.IP,connWidget.PORT))

    def reconnect(self,info):
        self.connectSig.emit(info)

    def update(self,artistInfo):
        for key,val in artistInfo.items():
            if not key in self.connections.keys():
                self.addConnectionWidget(name=key,
                            IP=str(val[2][0]),PORT=str(val[2][1]))
            else:
                self.connections[key].update(name=key,status=(val[0],val[1]))

        toDelete = []
        for name in self.connections.keys():
            if not name in artistInfo.keys():
                toDelete.append(name)

        for name in toDelete:
            self.connections[name].close()
            del self.connections[name]

class ConnectionWidget(QtGui.QWidget):
    removeSig = QtCore.Signal(object)
    reconnectSig = QtCore.Signal(object)
    def __init__(self, parent=None,name='',IP='KSF402',PORT='5004'):
        super(ConnectionWidget,self).__init__(parent)
        self.IP = IP
        self.PORT = PORT
        self.name = name

        self.layout = QtGui.QGridLayout(self)

        self.label = QtGui.QLabel(' ' + str(name))
        self.layout.addWidget(self.label,0,0,1,1)
        
        self.ManLabel = QtGui.QLabel('Manager')
        self.ManLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.ManLabel.setMinimumWidth(50)
        self.ManLabel.setStyleSheet("QLabel { background-color: red }")
        self.layout.addWidget(self.ManLabel,0,1,1,1)
        
        self.DSLabel = QtGui.QLabel('Data Server')
        self.DSLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.DSLabel.setMinimumWidth(50)
        self.DSLabel.setStyleSheet("QLabel { background-color: red }")
        self.layout.addWidget(self.DSLabel,0,2,1,1)

        self.channel = QtGui.QLabel(self,text='IP: ' + IP)
        self.layout.addWidget(self.channel,0,3,1,1)

        self.port = QtGui.QLabel(self,text='Port: ' + PORT)
        self.layout.addWidget(self.port,0,4,1,1)

        self.ManReconnectButton = QtGui.QPushButton('Reconnect Manager')
        self.layout.addWidget(self.ManReconnectButton,0,1,1,1)
        self.ManReconnectButton.clicked.connect(lambda: self.reConnectArtist('Manager'))
        self.ManReconnectButton.setHidden(True)

        self.DSReconnectButton = QtGui.QPushButton('Reconnect Data Server')
        self.layout.addWidget(self.DSReconnectButton,0,2,1,1)
        self.DSReconnectButton.clicked.connect(lambda: self.reConnectArtist('Data Server'))
        self.DSReconnectButton.setHidden(True)

        self.removeButton = QtGui.QPushButton('Remove')
        self.removeButton.clicked.connect(self.removeArtist)
        self.layout.addWidget(self.removeButton,0,6,1,1)
        
    def removeArtist(self):
        self.removeSig.emit(self)

    def reConnectArtist(self,sender):
        self.IP = str(self.channel.text().split(': ')[-1])
        self.PORT = int(self.port.text().split(': ')[-1])
        self.reconnectSig.emit((sender,(self.IP,self.PORT)))

    def update(self,name,status):
        self.label.setText(' '+ name)
        if status[0]:
            self.ManLabel.setStyleSheet("QLabel { background-color: green }")
            self.ManReconnectButton.setHidden(True)
        else:
            self.ManLabel.setStyleSheet("QLabel { background-color: red }")
            self.ManReconnectButton.setVisible(True)

        if status[1]:
            self.DSLabel.setStyleSheet("QLabel { background-color: green }")
            self.DSReconnectButton.setHidden(True)
        else:
            self.DSLabel.setStyleSheet("QLabel { background-color: red }")
            self.DSReconnectButton.setVisible(True)