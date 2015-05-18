from PyQt4 import QtCore,QtGui
import threading as th
import multiprocessing as mp
import time
import pickle
import asyncore

from backend.connectors import Connector
import backend.logbook as logbooks
from connectiondialogs import ConnectionDialog, FieldAdditionDialog
from logviewerwidgets import LogEntryWidget


class PassToLogbookApp(QtCore.QObject):
    
    changeOptions = QtCore.pyqtSignal(object)
    displayLog = QtCore.pyqtSignal(object)
    changeEntry = QtCore.pyqtSignal(object)


class LogbookApp(QtGui.QMainWindow):

    def __init__(self):

        super(LogbookApp, self).__init__()
        
        self.logbook = []

        self.looping = True
        t = th.Thread(target=self.startIOLoop).start()
        self.init_UI()
        self.options = tuple()

        self.man = None

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update)
        self.timer.start(50)

        self.show()

    def init_UI(self):
        self.central = QtGui.QWidget()
        layout = QtGui.QGridLayout(self.central)
        self.setCentralWidget(self.central)

        self.addManager = QtGui.QPushButton('Add Manager')
        self.addManager.clicked.connect(self.addConnection)
        layout.addWidget(self.addManager)

        self.logSelect = QtGui.QComboBox(parent=None)
        self.logSelect.setToolTip('Choose the logbook you want to load.')
        layout.addWidget(self.logSelect)

        self.getLogbook = QtGui.QPushButton('Get Logbook')
        self.getLogbook.clicked.connect(self.getLog)
        layout.addWidget(self.getLogbook)

        self.addEntryButton = QtGui.QPushButton('Add entry')
        self.addEntryButton.clicked.connect(self.addEntryToLog)
        self.addEntryButton.setDisabled(True)
        layout.addWidget(self.addEntryButton)

        self.scrollArea = QtGui.QScrollArea(self)
        self.scrollArea.setWidgetResizable(True)
        self.scrollAreaWidgetContents = QtGui.QWidget()
        self.scrollArea.setWidget(self.scrollAreaWidgetContents)
        layout.addWidget(self.scrollArea)

        self.entryContainersLayout = QtGui.QVBoxLayout(self.scrollAreaWidgetContents)
        self.entryContainers = []
        self.newEntryContainer()

    def newEntryContainer(self):
        entryContainer = QtGui.QGridLayout()
        self.entryContainersLayout.addLayout(entryContainer)
        entryContainer.setAlignment(QtCore.Qt.AlignTop)
        self.entryContainers.append(entryContainer)

    def getLog(self):
        log = str(self.logSelect.currentText())
        self.selectedLog = log
        self.man.send_instruction(['Get Logbook', log])
        self.addEntryButton.setEnabled(True)

    def addEntryToLog(self):
        self.man.send_instruction(['Add To Logbook', self.selectedLog])
        self.man.send_instruction(['Get Logbook', self.selectedLog])

    def addConnection(self):
        respons = ConnectionDialog.getInfo(self)
        if respons[1]:
            chan, port = respons[0]
            port = int(port)
            self.man = ManagerConnector((chan, port),
                                        callback=None,
                                        onCloseCallback=self.onClosedCallback,
                                        choicesCallback=self.changeLogbooks,
                                        logbookCallback=self.displayLogbook,
                                        changeCallback=self.changeEntry)

    def displayLogbook(self, log):
        for entryContainer in self.entryContainers:
            for i in reversed(range(entryContainer.count())):
                widget = entryContainer.itemAt(i).widget()
                widget.deleteLater()
                entryContainer.removeWidget(widget)
                widget.setParent(None)

        self.logEntryWidgets = {}
        log = sorted(log, key=lambda entry: entry[0]['Time'])
        for key, entry in enumerate(log):
            self.logEntryWidgets[key] = LogEntryWidget(text='Entry ' + str(int(key)),
                                                       entry=entry, number=key)
            self.logEntryWidgets[key].createFrame()
            self.entryContainers[-1].addWidget(self.logEntryWidgets[key], key, 0)
            self.logEntryWidgets[key].updated.connect(self.editEntry)
            self.logEntryWidgets[key].renew.connect(self.changeEntry)
            self.logEntryWidgets[key].addFieldButton.clicked.connect(self.addField)

            QtGui.QApplication.processEvents()

            if self.entryContainers[-1].count() > 100:
                self.newEntryContainer()

    def addField(self):
        fieldname, result = FieldAdditionDialog.getInfo()
        if result:
            self.man.send_instruction(['Add Field To Logbook', fieldname])

    def renewEntryWidget(self, key):
        self.logEntryWidgets[key].clearFrame()
        self.logEntryWidgets[key].createFrame()

    def editEntry(self, tup):
        entry, key = tup
        self.man.send_instruction(['Edit Logbook', int(key), entry])

    def changeEntry(self, entry_key):
        entry, key = entry_key

        try:
            self.logEntryWidgets[key].entry = entry
            self.logEntryWidgets[key].clearFrame()
            self.logEntryWidgets[key].createFrame()
            self.logEntryWidgets[key].showNew()
        except KeyError as e:
            self.logEntryWidgets[key] = LogEntryWidget(text='Entry ' + str(int(key)),
                                                       entry=entry, number=key)
            self.logEntryWidgets[key].createFrame()
            self.entryContainers[-1].addWidget(self.logEntryWidgets[key], key, 0)
            self.logEntryWidgets[key].updated.connect(self.editEntry)
            self.logEntryWidgets[key].renew.connect(self.changeEntry)
            self.logEntryWidgets[key].addFieldButton.clicked.connect(self.addField)
            self.logEntryWidgets[key].showNew()

            QtGui.QApplication.processEvents()

            if self.entryContainers[-1].count() > 100:
                self.newEntryContainer()

    def onClosedCallback(self, server):
        print(server, server.type)
        self.AppCallBack(server.type)

    def changeLogbooks(self, options):
        if not options == self.options:
            self.options = options
            curLog = int(self.logSelect.currentIndex())
            self.logSelect.clear()
            self.logSelect.addItems(options)
            self.logSelect.setCurrentIndex(curLog)

    def startIOLoop(self):
        while self.looping:
            asyncore.loop(count=1)
            time.sleep(0.1)

    def stopIOLoop(self):
        self.looping = False

    def update(self):
        pass

    def getLogbook(self):
        self.man.send_instruction('info')

    def closeEvent(self,event):
        self.timer.stop()
        self.stopIOLoop()
        event.accept()


class ManagerConnector(Connector):

    def __init__(self, chan, callback, onCloseCallback, choicesCallback, logbookCallback, changeCallback):
        super(ManagerConnector, self).__init__(chan, callback, onCloseCallback, t='LGui_to_M')

        self.logbookSignal = PassToLogbookApp()
        self.logbookSignal.changeOptions.connect(choicesCallback)
        self.logbookSignal.displayLog.connect(logbookCallback)
        self.logbookSignal.changeEntry.connect(changeCallback)
        self.send_next()

    def found_terminator(self):
        buff = self.buff
        self.buff = b''
        data = pickle.loads(buff)
        if type(data) == list:
            message = data[0]
            data = data[1:]
            if message == 'Choices':
                self.logbookSignal.changeOptions.emit(data[0])
            elif message == 'Logbook':
                self.logbookSignal.displayLog.emit(data[0])
            elif message == 'Notify':
                self.logbookSignal.changeEntry.emit(data)
            else:
                pass
        try:
            info = self.commQ.get_nowait()
            self.push(pickle.dumps(info))
            self.push('END_MESSAGE'.encode('UTF-8'))
        except:
            self.send_next()

    def send_instruction(self, instruction):
        self.push(pickle.dumps(instruction))
        self.push('END_MESSAGE'.encode('UTF-8'))