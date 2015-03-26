from PyQt4 import QtCore,QtGui
import threading as th
import multiprocessing as mp
import asynchat
import asyncore
import socket
import time
import pickle

from scanner import ScannerWidget
from connect import ConnectionsWidget
from central import CentralDock

from backend.DataServer import DataServer
from backend.Radio import Radio
from backend.Manager import Manager


class ManagerApp(QtGui.QMainWindow):
    def __init__(self):
        super(ManagerApp, self).__init__()
        self.looping = True
        t = th.Thread(target = self.startIOLoop).start()

        respons = ConnectionDialog.getInfo(self)
        if respons[1]:
            self.addConnection(respons[0])

        self.createActions()
        self.init_UI()

    def createActions(self):
        self.ManagerAct = QtGui.QAction(self.tr("M&anager"), self)
        self.ManagerAct.setShortcut(self.tr("Ctrl+M"))
        self.ManagerAct.setStatusTip(self.tr("Configure the manager"))
        self.ManagerAct.triggered.connect(self.configureManager)

        self.ServerAct = QtGui.QAction(self.tr("D&ataserver"), self)
        self.ServerAct.setShortcut(self.tr("Ctrl+D"))
        self.ServerAct.setStatusTip(self.tr("Configure the data server"))
        self.ServerAct.triggered.connect(self.configureDataServer)

    def init_UI(self):

        self.connMenu = self.menuBar().addMenu(self.tr("&Connections"))
        self.connMenu.addAction(self.ManagerAct)
        self.connMenu.addAction(self.ServerAct)

        self.scanner = ScannerWidget()
        self.scanner.scanInfo.connect(self.startScan)
        self.setCentralWidget(self.scanner)

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update)
        self.timer.start(50)

        self.show()

    def configureManager(self):
        respons = ArtistConnectionDialog.getInfo(self,self.conn.artists)
        if respons[1]:
            for info in respons[0]:
                self.addArtist(info)

    def configureDataServer(self):
        pass

    def addConnection(self,data):
        self.conn = ManagerConnection(data[0],int(data[1]))

    def startIOLoop(self):
        while self.looping:
            asyncore.loop(count=1)
            time.sleep(0.01)

    def stopIOLoop(self):
        self.looping = False

    def startScan(self,scanInfo):
        self.conn.connQ.put(['Scan',scanInfo])

    def addArtist(self,address):
        self.conn.connQ.put(['Add Artist',address])

    def update(self):
        try:
            self.scanner.setParCombo(self.conn.format)
            self.scanner.updateProgress(self.conn.progress)
            self.updateArtists()
            if self.scanner.state == 'START' and self.conn.scanning:
                self.scanner.changeControl()
            elif self.scanner.state == 'STOP' and not self.conn.scanning:
                self.scanner.changeControl()
        except AttributeError:
            pass

    def updateArtists(self):
        if not list(self.conn.artists.keys()) == []:
            text = "Connected to " + ", ".join(self.conn.artists.keys())
            self.statusBar().showMessage(text)

    def closeEvent(self,event):
        self.stopIOLoop()
        event.accept()


class ManagerConnection(asynchat.async_chat):
    def __init__(self,IP,PORT):
        super(ManagerConnection,self).__init__()
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        # self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self.connect((IP, PORT))

        self.IP = IP
        self.PORT = PORT

        self.set_terminator('STOP_DATA'.encode('UTF-8'))
        self._buffer = b''
        self.progress = 0
        self.scanning = False
        self.format = {}
        self.artists = []

        self.connQ = mp.Queue()

        self.push(pickle.dumps('ARTISTS?'))
        self.push('END_MESSAGE'.encode('UTF-8'))

    def collect_incoming_data(self, data):
        self._buffer += data

    def found_terminator(self):
        buff = self._buffer
        self._buffer = b''
        data = pickle.loads(buff)
        if type(data) == dict:
            self.artists = data
        else:
            self.scanning,self.progress,self.format = data
        try:
            info = self.connQ.get_nowait()
            self.push(pickle.dumps(info))
            self.push('END_MESSAGE'.encode('UTF-8'))
        except:
            pass

        self.send_next()

    def send_next(self):
        self.push(pickle.dumps('NEXT'))
        self.push('END_MESSAGE'.encode('UTF-8'))

class ConnectionDialog(QtGui.QDialog):
    def __init__(self, parent=None,artists={}):
        super(ConnectionDialog,self).__init__(parent)
        self.layout = QtGui.QGridLayout(self)
        buttons = QtGui.QDialogButtonBox(
            QtGui.QDialogButtonBox.Ok | QtGui.QDialogButtonBox.Cancel,
            QtCore.Qt.Horizontal)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        self.layout.addWidget(buttons,500,1,1,2)

        self.layout.addWidget(QtGui.QLabel('Manager Channel'),0,0,1,1)  
        
        self.channelBox = QtGui.QLineEdit(self,text='KSF402')
        self.layout.addWidget(self.channelBox,1,0,1,1)

        self.layout.addWidget(QtGui.QLabel('Manager Port'),0,1,1,1)
        self.portBox = QtGui.QLineEdit(self,text='5007')

        self.layout.addWidget(self.portBox,1,1,1,1)

    def getData(self):
        return [self.channelBox.text(),self.portBox.text()]
                
    @staticmethod
    def getInfo(parent = None):
        dialog = ConnectionDialog(parent)
        result = dialog.exec_()
        data = dialog.getData()
        return (data, result == QtGui.QDialog.Accepted)

class ArtistConnectionDialog(QtGui.QDialog):
    def __init__(self, parent=None,artists={}):
        super(ArtistConnectionDialog,self).__init__(parent)
        self.channelBoxes = []
        self.portBoxes = []

        self.layout = QtGui.QGridLayout(self)
        buttons = QtGui.QDialogButtonBox(
            QtGui.QDialogButtonBox.Ok | QtGui.QDialogButtonBox.Cancel,
            QtCore.Qt.Horizontal)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        self.layout.addWidget(buttons,500,1,1,2)

        self.addArtistButton = QtGui.QPushButton('Add Artist')
        self.addArtistButton.clicked.connect(self.addArtistSelector)
        self.layout.addWidget(self.addArtistButton,499,0,1,1)

        self.pos = 3

        for k,v in artists.items():
            self.layout.addWidget(QtGui.QLabel(str(k)),self.pos+1,0,1,1)
            self.addArtistSelector()
            self.channelBoxes[-1].setText(str(v[0]))
            self.portBoxes[-1].setText(str(v[1]))

    def addArtistSelector(self):
        self.layout.addWidget(QtGui.QLabel('Artist Channel'),self.pos,1,1,1)        
        self.channelBoxes.append(QtGui.QLineEdit(self,text='KSF402'))
        self.layout.addWidget(self.channelBoxes[-1],self.pos+1,1,1,1)

        self.layout.addWidget(QtGui.QLabel('Artist Port'),self.pos,2,1,1)
        self.portBoxes.append(QtGui.QLineEdit(self,text='5004'))
        self.layout.addWidget(self.portBoxes[-1],self.pos+1,2,1,1)

        self.pos += 2

    def getData(self):
        return [(k.text(),v.text()) for k,v in zip(self.channelBoxes,self.portBoxes)]
                

    @staticmethod
    def getInfo(parent = None,artists={}):
        print(artists)
        dialog = ArtistConnectionDialog(parent,artists)
        result = dialog.exec_()
        data = dialog.getData()
        return (data, result == QtGui.QDialog.Accepted)