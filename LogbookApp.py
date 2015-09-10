
import pandas as pd
from PyQt4 import QtCore, QtGui
import tables
import threading as th
import time
import pickle
import asyncore
import os
# import ScanViewer

from backend.connectors import Connector
from connectiondialogs import ConnectionDialog, FieldAdditionDialog
from logviewerwidgets import LogEntryWidget
from backend.Filereader import FileReader
SAVE_DIR = 'C:/Data/'


fileServer_channel = ('127.0.0.1', 5009)
manager_channel = ('127.0.0.1', 5004)


class LogbookApp(QtGui.QMainWindow):
    editSignal = QtCore.pyqtSignal(int,object)
    addSignal = QtCore.pyqtSignal(int,object)
    def __init__(self):
        super(LogbookApp, self).__init__()

        self.log_edits = []
        self.logEntryWidgets = {}
        self.tags = []

        self.looping = True
        t = th.Thread(target=self.startIOLoop).start()
        self.man = None
        self.init_UI()

        self.addConnection()
        # self.addFileConnection(auto=True)

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update)
        self.timer.start(50)

        self.editSignal.connect(self.edit_entry_ui)
        self.addSignal.connect(self.add_entry_to_ui)

        self.show()

    def startIOLoop(self):
        while self.looping:
            asyncore.loop(count=1)
            time.sleep(0.1)

    def stopIOLoop(self):
        self.looping = False

    def init_UI(self):
        self.central = QtGui.QWidget()
        layout = QtGui.QGridLayout(self.central)
        self.setCentralWidget(self.central)

        self.connectionLabel = QtGui.QLabel('Connections:')
        layout.addWidget(self.connectionLabel, 0, 0, 1, 1)

        self.managerLabel = QtGui.QLabel('Manager')
        self.managerLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.managerLabel.setMinimumWidth(50)
        self.managerLabel.setMinimumHeight(25)
        self.managerLabel.setStyleSheet("QLabel { background-color: red }")
        layout.addWidget(self.managerLabel, 1, 0, 1, 2)

        self.fileServerLabel = QtGui.QLabel('File Server')
        self.fileServerLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.managerLabel.setMinimumHeight(25)
        self.fileServerLabel.setMinimumWidth(50)
        self.fileServerLabel.setStyleSheet("QLabel { background-color: red }")
        layout.addWidget(self.fileServerLabel, 2, 0, 1, 2)

        self.addFileServer = QtGui.QPushButton('Add File server')
        # self.addFileServer.clicked.connect(self.addFileConnection)
        layout.addWidget(self.addFileServer, 2, 0, 1, 2)

        self.addManager = QtGui.QPushButton('Reconnect to Manager')
        self.addManager.clicked.connect(self.addConnection)
        layout.addWidget(self.addManager, 1, 0, 1, 2)

        self.editLabel = QtGui.QLabel('Logbook:')
        layout.addWidget(self.editLabel, 3, 0, 1, 1)

        self.addEntryButton = QtGui.QPushButton('Add entry')
        self.addEntryButton.clicked.connect(self.add_entry_to_log)
        layout.addWidget(self.addEntryButton, 5, 0, 1, 2)

        self.searchStringLabel = QtGui.QPushButton('String search')
        # self.searchStringLabel.clicked.connect(self.filterLogbookOnString)
        self.searchStringLabel.setDisabled(True)
        self.searchStringEdit = QtGui.QLineEdit('')
        layout.addWidget(self.searchStringLabel, 6, 0)
        layout.addWidget(self.searchStringEdit, 6, 1)

        self.searchTagLabel = QtGui.QPushButton('Tag search')
        # self.searchTagLabel.clicked.connect(self.filterLogbookOnTag)
        self.searchTagLabel.setDisabled(True)
        self.searchTagEdit = QtGui.QLineEdit('')
        layout.addWidget(self.searchTagLabel, 7, 0)
        layout.addWidget(self.searchTagEdit, 7, 1)

        self.scrollArea = QtGui.QScrollArea(self)
        self.scrollArea.setWidgetResizable(True)
        self.scrollAreaWidgetContents = QtGui.QWidget()
        self.scrollArea.setWidget(self.scrollAreaWidgetContents)
        layout.addWidget(self.scrollArea, 8, 0, 1, 2)

        self.entryContainersLayout = QtGui.QVBoxLayout(
            self.scrollAreaWidgetContents)
        self.entryContainers = []
        self.newEntryContainer()

    def newEntryContainer(self):
        entryContainer = QtGui.QGridLayout()
        self.entryContainersLayout.addLayout(entryContainer)
        entryContainer.setAlignment(QtCore.Qt.AlignTop)
        self.entryContainers.append(entryContainer)

    def add_entry_to_ui(self,number,entry):
        self.logEntryWidgets[number] = LogEntryWidget(text='Entry ' + str(int(number)),
                                                           entry=entry,
                                                           number=number)
        self.logEntryWidgets[number].createFrame()

        self.logEntryWidgets[number].submitSig.connect(self.submit_change)
        self.logEntryWidgets[number].submitTagSig.connect(self.submit_new_tag)
        self.logEntryWidgets[number].addFieldSig.connect(self.submit_new_field)
        # self.logEntryWidgets[number].dataRequest.connect(self.getData)
        
        self.entryContainers[-1].addWidget(self.logEntryWidgets[number], number, 0)
        # QtGui.QApplication.processEvents()

        if self.entryContainers[-1].count() > 20:
            self.newEntryContainer()

    def add_entry_to_log(self):
        self.man.add_request(('add_entry_to_log',{}))

    def add_entry_to_log_reply(self,track,params):
        print(track,params)

    def submit_change(self):
        number = self.sender().number
        entry = self.sender().entry
        self.man.add_request(('change_entry',{'number':[number],
                                              'entry':entry[-1]}))

    def change_entry_reply(self,track,params):
        print(track,params)

    def submit_new_field(self):
        field_name, result = FieldAdditionDialog.getInfo()
        if result:
            self.man.add_request(('add_new_field', {'field_name':field_name}))

    def add_new_field_reply(self,track,params):
        print(track,params)

    def submit_new_tag(self):
        number = self.sender().number
        tag_name, result = QtGui.QInputDialog.getItem(self, 'Tag Input Dialog', 
                'Choose a tag or enter new tag:', self.tags)

        if result:
            self.man.add_request(('add_new_tag', {'tag_name':tag_name,
                                                  'number':number}))

    def add_new_tag_reply(self,track,params):
        print(track,params)
        tag_name = params['tag_name']
        if not tag_name in self.tags:
            self.tags.append(tag_name)

    def edit_entry_ui(self,number,entry):
        self.logEntryWidgets[number].entry = entry
        self.logEntryWidgets[number].clearFrame()
        self.logEntryWidgets[number].createFrame()
        self.logEntryWidgets[number].showNew()

    def addConnection(self):
        try:
            self.man = Connector(name='LGUI_to_M',
                                        chan=manager_channel,
                                        callback=self.reply_cb,
                                        onCloseCallback=self.onCloseCallback,
                                        default_callback=self.default_cb)
            self.managerLabel.setStyleSheet("QLabel { background-color: green }")
            self.searchStringLabel.setEnabled(True)
            self.searchTagLabel.setEnabled(True)
            self.addManager.setHidden(True)
        except Exception as e:
            print(e)

    def reply_cb(self,message):
        track = message['track']
        if message['reply']['parameters']['status'][0] == 0:
            function = message['reply']['op']
            args = message['reply']['parameters']
            status_updates = message['status_updates']
            for status_update in status_updates:
                # self.messageUpdateSignal.emit({'track':track,'args':status_update})
                print(status_update)
            params = getattr(self, function)(track, args)

        else:
            exception = message['reply']['parameters']['exception']
            print("Reply cb exception: " + exception)

    def logbook_status_reply(self,track,params):
        log_edit_numbers = params['log_edit_numbers']
        log_edits = params['log_edits']
        self.log_edits.extend(log_edits)

        done = []
        # this way we immediately update to the latest version of the entry
        for number,edit in zip(reversed(log_edit_numbers),reversed(log_edits)):
            if not number in done: 
                done.append(number)
                    
                # add tags if there are any
                if 'Tags' in edit[-1].keys():
                    self.tags.extend(edit[-1]['Tags'])
                    self.tags = list(set(self.tags))

                if number in self.logEntryWidgets.keys():
                    self.editSignal.emit(number,edit)
                else: # entry is not yet in the logbook
                    self.addSignal.emit(number,edit)

    def default_cb(self):
        return 'logbook_status',{'no_of_log_edits':[len(self.log_edits)]}

    def onCloseCallback(self, connector):
        print(connector.acceptorName + ' connection failure')

    def closeEvent(self, event):
        self.timer.stop()
        self.stopIOLoop()
        event.accept()

