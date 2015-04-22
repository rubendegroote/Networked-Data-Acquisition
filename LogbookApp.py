from PyQt4 import QtCore,QtGui
import threading as th
import multiprocessing as mp
import time
import pickle
import asyncore

from backend.Manager import Manager
from backend.connectors import Connector
from backend.logbook import *


class LogbookApp(QtGui.QMainWindow):
    def __init__(self):
        super(LogbookApp, self).__init__()
        
        self.logbook = Logbook()

        self.looping = True
        t = th.Thread(target = self.startIOLoop).start()
        self.init_UI()

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update)
        self.timer.start(50)

        self.show()

    def init_UI(self):
        self.central = QtGui.QWidget()
        layout = QtGui.QGridLayout(self.central)
        self.setCentralWidget(self.central)

        self.logPathButton = QtGui.QPushButton('Log Path')
        self.logPathButton.clicked.connect(self.defineLogbookPath)
        layout.addWidget(self.logPathButton)

    def startIOLoop(self):
        while self.looping:
            asyncore.loop(count=1)
            time.sleep(0.1)

    def stopIOLoop(self):
        self.looping = False

    def update(self):
        pass

    def defineLogbookPath(self):
        fileName = QtGui.QFileDialog.getExistingDirectory(self, 'Choose logbook file', os.getcwd())
        self.logPath = fileName

    def closeEvent(self,event):
        self.timer.stop()
        self.stopIOLoop()
        event.accept()
