from PyQt4 import QtCore, QtGui
import threading as th
import time
import pickle
import asyncore
import os
import ScanViewer

from backend.connectors import Connector
from connectiondialogs import ConnectionDialog, FieldAdditionDialog
from logviewerwidgets import LogEntryWidget
from backend.Filereader import FileReader


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

        self.addFileServer = QtGui.QPushButton('Add File server')
        self.addFileServer.clicked.connect(self.addFileConnection)
        layout.addWidget(self.addFileServer, 0, 0, 1, 2)

        self.addManager = QtGui.QPushButton('Add Manager')
        self.addManager.clicked.connect(self.addConnection)
        layout.addWidget(self.addManager, 1, 0, 1, 2)

        self.getLogbook = QtGui.QPushButton('Get Logbook')
        self.getLogbook.clicked.connect(self.getLog)
        layout.addWidget(self.getLogbook, 2, 0, 1, 2)

        self.addEntryButton = QtGui.QPushButton('Add entry')
        self.addEntryButton.clicked.connect(self.addEntryToLog)
        self.addEntryButton.setDisabled(True)
        layout.addWidget(self.addEntryButton, 3, 0, 1, 2)

        self.searchStringLabel = QtGui.QPushButton('String search')
        self.searchStringLabel.clicked.connect(self.filterLogbookOnString)
        self.searchStringEdit = QtGui.QLineEdit('')
        layout.addWidget(self.searchStringLabel, 4, 0)
        layout.addWidget(self.searchStringEdit, 4, 1)

        self.searchTagLabel = QtGui.QPushButton('Tag search')
        self.searchTagLabel.clicked.connect(self.filterLogbookOnTag)
        self.searchTagEdit = QtGui.QLineEdit('')
        layout.addWidget(self.searchTagLabel, 5, 0)
        layout.addWidget(self.searchTagEdit, 5, 1)

        self.scrollArea = QtGui.QScrollArea(self)
        self.scrollArea.setWidgetResizable(True)
        self.scrollAreaWidgetContents = QtGui.QWidget()
        self.scrollArea.setWidget(self.scrollAreaWidgetContents)
        layout.addWidget(self.scrollArea, 6, 0, 1, 2)

        self.entryContainersLayout = QtGui.QVBoxLayout(
            self.scrollAreaWidgetContents)
        self.entryContainers = []
        self.newEntryContainer()

    def newEntryContainer(self):
        entryContainer = QtGui.QGridLayout()
        self.entryContainersLayout.addLayout(entryContainer)
        entryContainer.setAlignment(QtCore.Qt.AlignTop)
        self.entryContainers.append(entryContainer)

    def getLog(self):
        # log = str(self.logSelect.currentText())
        # self.selectedLog = log
        self.man.send_instruction(['Get Logbook', 'dummy'])
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
                                        logbookCallback=self.saveLog,
                                        changeCallback=self.changeEntry)
            self.getLog()

    def addFileConnection(self):
        respons = ConnectionDialog.getInfo(self)
        if respons[1]:
            chan, port = respons[0]
            port = int(port)
            self.fileServ = FileReader(IP=chan, PORT=port)

    def saveLog(self, log):
        self.logbook = sorted(log, key=lambda entry: entry[0]['Time'])
        self.displayLogbook(self.logbook)

    def displayLogbook(self, log, filter=None):
        for entryContainer in self.entryContainers:
            for i in reversed(range(entryContainer.count())):
                widget = entryContainer.itemAt(i).widget()
                widget.deleteLater()
                entryContainer.removeWidget(widget)
                widget.setParent(None)

        self.logEntryWidgets = {}
        if filter is None:
            filter = [True for key in log]
        for key, entry in enumerate(log):
            if filter[key]:
                self.logEntryWidgets[key] = LogEntryWidget(text='Entry ' + str(int(key)),
                                                           entry=entry,
                                                           number=key)
                self.logEntryWidgets[key].createFrame()
                self.entryContainers[-1].addWidget(self.logEntryWidgets[key], key, 0)
                self.logEntryWidgets[key].updated.connect(self.editEntry)
                self.logEntryWidgets[key].renew.connect(self.changeEntry)
                self.logEntryWidgets[key].fieldAdded.connect(self.addField)
                self.logEntryWidgets[key].tagAdded.connect(self.addTag)
                self.logEntryWidgets[key].dataRequest.connect(self.getData)

                QtGui.QApplication.processEvents()

                if self.entryContainers[-1].count() > 100:
                    self.newEntryContainer()

    def getData(self, value):
        filename = 'Server_scan_{}.h5'.format(value)
        if not os.path.isfile('copy_of_' + filename):
            self.fileServ.send_request(['SEND_FILE', filename])
        ScanViewer.ScanDisplayApp('copy_of_' + filename, self)


    def filterLogbookOnString(self):
        filterString = str(self.searchStringEdit.text())
        if filterString == '':
            self.displayLogbook(self.logbook, filter=None)
        else:
            filter = [False for entry in self.logbook]
            for key, entry in enumerate(self.logbook):
                for snapshot in entry:
                    for value in snapshot.values():
                        try:
                            if isinstance(value, str) and filterString.lower() in value.lower():
                                filter[key] = True
                            else:
                                pass
                        except:
                            raise
            self.displayLogbook(self.logbook, filter=filter)

    def filterLogbookOnTag(self):
        filterTag = str(self.searchTagEdit.text())
        if filterTag == '':
            self.displayLogbook(self.logbook, filter=None)
        else:
            filter = [False for entry in self.logbook]
            for key, entry in enumerate(self.logbook):
                for snapshot in entry:
                    if 'Tags' in snapshot and filterTag in snapshot['Tags'] and snapshot['Tags'][filterTag]:
                        filter[key] = True
            self.displayLogbook(self.logbook, filter=filter)

    def addField(self):
        fieldname, result = FieldAdditionDialog.getInfo()
        if result:
            self.man.send_instruction(['Add Field To Logbook', fieldname])

    def addTag(self):
        tagname, result = FieldAdditionDialog.getInfo()
        if result:
            self.man.send_instruction(['Add Tag To Logbook', tagname])

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
                                                       entry=entry,
                                                       number=key)
            self.logEntryWidgets[key].createFrame()
            self.entryContainers[-1].addWidget(self.logEntryWidgets[key], key, 0)
            self.logEntryWidgets[key].updated.connect(self.editEntry)
            self.logEntryWidgets[key].renew.connect(self.changeEntry)
            self.logEntryWidgets[key].fieldAdded.connect(self.addField)
            self.logEntryWidgets[key].tagAdded.connect(self.addTag)

            QtGui.QApplication.processEvents()

            if self.entryContainers[-1].count() > 100:
                self.newEntryContainer()

    def onClosedCallback(self, server):
        print(server, server.type)
        self.AppCallBack(server.type)

    def changeLogbooks(self, options):
        pass
        # if not options == self.options:
        #     self.options = options
        #     curLog = int(self.logSelect.currentIndex())
        #     self.logSelect.clear()
        #     self.logSelect.addItems(options)
        #     self.logSelect.setCurrentIndex(curLog)

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

    def closeEvent(self, event):
        self.timer.stop()
        self.stopIOLoop()
        event.accept()


class ManagerConnector(Connector):

    def __init__(self, chan, callback, onCloseCallback, choicesCallback, logbookCallback, changeCallback):
        super(ManagerConnector, self).__init__(
            chan, callback, onCloseCallback, t='LGui_to_M')

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
                pass
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
