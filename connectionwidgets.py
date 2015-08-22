from PyQt4 import QtCore, QtGui
import configparser
from connectiondialogs import ConnectionDialog


class ArtistConnections(QtGui.QWidget):
    connectSig = QtCore.Signal(tuple)
    removeSig = QtCore.Signal(tuple)

    def __init__(self, parent=None):
        super(ArtistConnections, self).__init__(parent)
        self.artistWidgets = {}
        self.l = 0
        self.layout = QtGui.QGridLayout(self)

        self.options = ['ABU', 'CRIS', 'Laser', 'Diodes','M2']
        self.address = {'ABU': ('PCCRIS15', 5005),
                        'CRIS': ('PCCRIS6', 5005),
                        'Laser': ('PCCRIS15', 5004),
                        'Diodes': ('PCCRIS15', 5003),
                        'M2': ('127.0.0.1', 5002)}
        self.artistSelection = QtGui.QComboBox()
        self.artistSelection.addItems(self.options)
        self.artistSelection.setCurrentIndex(0)
        self.layout.addWidget(self.artistSelection, 100, 0, 1, 1)

        self.addArtistButton = QtGui.QPushButton('Add Artist')
        self.addArtistButton.clicked.connect(lambda: self.addConnection())
        self.layout.addWidget(self.addArtistButton, 100, 1, 1, 1)

        self.removeArtistsButton = QtGui.QPushButton('Remove All Artists')
        self.removeArtistsButton.clicked.connect(lambda: self.removeAll())
        self.layout.addWidget(self.removeArtistsButton, 101, 0, 1, 2)

        self.ManArtists = []
        self.DSArtists = []

    def addConnection(self):
        selection = self.artistSelection.currentText()
        respons = self.address[selection]
        self.connectSig.emit(('Both', respons))

    def addArtistWidget(self, name='', IP='KSF402', PORT='5004'):
        self.artistWidgets[name] = ArtistWidget(self, name, IP, PORT)
        self.artistWidgets[name].removeSig.connect(self.remove)
        self.artistWidgets[name].reconnectSig.connect(self.reconnect)
        self.layout.addWidget(self.artistWidgets[name], self.l, 0, 1, 2)
        config = configparser.ConfigParser()
        for key in self.artistWidgets.keys():
            config[key] = {'IP': self.artistWidgets[name].IP,
                           'Port': self.artistWidgets[name].PORT}
        with open('ManagerArtistConnections.ini', 'w') as configfile:
            config.write(configfile)

        self.l += 1

    def remove(self, connWidget):
        self.removeSig.emit((connWidget.IP, connWidget.PORT))

    def removeAll(self):
        for name in self.artistWidgets:
            self.artistWidgets[name].removeArtist()

    def reconnect(self, info):
        self.connectSig.emit(info)

    def update(self, origin, params):
        print(origin,params)
        # update list of existing connections
        if origin == 'Manager':
            self.ManArtists = params.keys()
        elif origin == 'DataServer':
            self.DSArtists = params.keys()

        for key,val in params.items():
            # if there is a new artist, create a new widget
            if key not in self.artistWidgets.keys():
                self.addArtistWidget(name=key,
                    IP=str(val[1]), PORT=str(val[2]))
            # if it is not new: check if origin is still connected 
            # and update widget accordingly
            else:
                if not val[0]:
                    self.artistWidgets[key].set_disconnected(origin)

        # update the status of the widget, delete if needed
        toDelete = []
        for key,val in self.artistWidgets.items():
            if key not in self.ManArtists and key not in self.DSArtists:
                toDelete.append(val)
            else:
                if key not in params.keys():
                    val.set_disconnected(origin)
                elif params[key][0]:
                    val.set_connected(origin)

        for key in toDelete:
            self.artistWidgets[key].close()
            del self.artistWidgets[key]     

class ArtistWidget(QtGui.QWidget):
    removeSig = QtCore.Signal(object)
    reconnectSig = QtCore.Signal(object)

    def __init__(self, parent=None, name='', IP='KSF402', PORT='5004'):
        super(ArtistWidget, self).__init__(parent)
        self.IP = IP
        self.PORT = PORT
        self.name = name

        self.not_ok = "QLabel { background-color: red }"
        self.ok = "QLabel { background-color: green }"

        self.layout = QtGui.QGridLayout(self)

        self.label = QtGui.QLabel(' ' + str(name))
        self.layout.addWidget(self.label, 0, 0, 1, 1)

        self.ManLabel = QtGui.QLabel('Manager')
        self.ManLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.ManLabel.setMinimumWidth(50)
        self.ManLabel.setStyleSheet(self.not_ok)
        self.layout.addWidget(self.ManLabel, 0, 1, 1, 1)

        self.DSLabel = QtGui.QLabel('Data Server')
        self.DSLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.DSLabel.setMinimumWidth(50)
        self.DSLabel.setStyleSheet(self.not_ok)
        self.layout.addWidget(self.DSLabel, 0, 2, 1, 1)

        self.channel = QtGui.QLabel(self, text='IP: ' + IP)
        self.layout.addWidget(self.channel, 0, 3, 1, 1)

        self.portlabel = QtGui.QLabel(self, text='Port: ' + PORT)
        self.layout.addWidget(self.portlabel, 0, 4, 1, 1)

        self.ManReconnectButton = QtGui.QPushButton('Reconnect Manager')
        self.layout.addWidget(self.ManReconnectButton, 0, 1, 1, 1)
        self.ManReconnectButton.clicked.connect(
            lambda: self.reConnectArtist('Manager'))
        self.ManReconnectButton.setHidden(True)

        self.DSReconnectButton = QtGui.QPushButton('Reconnect Data Server')
        self.layout.addWidget(self.DSReconnectButton, 0, 2, 1, 1)
        self.DSReconnectButton.clicked.connect(
            lambda: self.reConnectArtist('Data Server'))
        self.DSReconnectButton.setHidden(True)

        self.removeButton = QtGui.QPushButton('Remove')
        self.removeButton.clicked.connect(self.removeArtist)
        self.layout.addWidget(self.removeButton, 0, 6, 1, 1)

    def removeArtist(self):
        self.removeSig.emit(self)

    def reConnectArtist(self, sender):
        self.IP = str(self.channel.text().split(': ')[-1])
        self.PORT = int(self.portlabel.text().split(': ')[-1])
        self.reconnectSig.emit((sender, (self.IP, self.PORT)))

    def set_disconnected(self,origin):
        print(0,origin)
        if origin == 'Manager':
            self.ManLabel.setStyleSheet(self.not_ok)
            self.ManReconnectButton.setVisible(True)
        else:
            self.DSLabel.setStyleSheet(self.not_ok)
            self.DSReconnectButton.setVisible(True)
            
    def set_connected(self,origin):
        print(1,origin)
        if origin == 'Manager':
            self.ManLabel.setStyleSheet(self.ok)
            self.ManReconnectButton.setHidden(True)
        else:
            self.DSLabel.setStyleSheet(self.ok)
            self.DSReconnectButton.setHidden(True)
           