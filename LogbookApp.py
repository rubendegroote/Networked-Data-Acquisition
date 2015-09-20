from PyQt4 import QtCore, QtGui
import threading as th
import asyncore
import time

from backend.connectors import Connector
from connectiondialogs import ConnectionDialog, FieldAdditionDialog
from logviewerwidgets import LogEntryWidget

SAVE_DIR = 'C:/Data/'
LOG_PER_PAGE = 50

manager_channel = ('127.0.0.1', 5004)

class LogbookApp(QtGui.QMainWindow):
    editSignal = QtCore.pyqtSignal(int,object)
    addSignal = QtCore.pyqtSignal(int,object)
    messageUpdateSignal = QtCore.pyqtSignal(dict)

    def __init__(self):
        super(LogbookApp, self).__init__()

        self.log_edits = []
        self.logEntryWidgets = {}
        self.tags = []

        self.looping = True
        t = th.Thread(target=self.startIOLoop).start()
        self.man = None
        self.init_UI()

        self.add_manager()

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update)
        self.timer.start(50)

        self.editSignal.connect(self.edit_entry_ui)
        self.addSignal.connect(self.add_entry_to_ui)
        self.messageUpdateSignal.connect(self.updateMessages)

        self.show()

    def startIOLoop(self):
        while self.looping:
            asyncore.loop(count=1)
            time.sleep(0.2)

    def stopIOLoop(self):
        self.looping = False

    def init_UI(self):
        self.central = QtGui.QSplitter()
        widget = QtGui.QWidget()
        self.central.addWidget(widget)
        layout = QtGui.QGridLayout(widget)
        self.setCentralWidget(self.central)

        self.connectionLabel = QtGui.QLabel('Connections:')
        layout.addWidget(self.connectionLabel, 0, 0, 1, 1)

        self.managerLabel = QtGui.QLabel('Manager')
        self.managerLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.managerLabel.setMinimumWidth(50)
        self.managerLabel.setMinimumHeight(25)
        self.managerLabel.setStyleSheet("QLabel { background-color: red }")
        layout.addWidget(self.managerLabel, 1, 0, 1, 2)

        self.addManager = QtGui.QPushButton('Reconnect to Manager')
        self.addManager.clicked.connect(self.add_manager)
        layout.addWidget(self.addManager, 1, 0, 1, 2)

        self.editLabel = QtGui.QLabel('Logbook:')
        layout.addWidget(self.editLabel, 3, 0, 1, 1)

        self.addEntryButton = QtGui.QPushButton('Add entry')
        self.addEntryButton.clicked.connect(self.add_entry_to_log)
        layout.addWidget(self.addEntryButton, 5, 0, 1, 2)

        self.searchStringLabel = QtGui.QPushButton('String search')
        self.searchStringLabel.clicked.connect(self.filterLogbookOnString)
        self.searchStringLabel.setDisabled(True)
        self.searchStringEdit = QtGui.QLineEdit('')
        layout.addWidget(self.searchStringLabel, 6, 0)
        layout.addWidget(self.searchStringEdit, 6, 1)

        self.searchTagLabel = QtGui.QPushButton('Tag search')
        self.searchTagLabel.clicked.connect(self.filterLogbookOnTag)
        self.searchTagLabel.setDisabled(True)
        self.searchTagEdit = QtGui.QLineEdit('')
        layout.addWidget(self.searchTagLabel, 7, 0)
        layout.addWidget(self.searchTagEdit, 7, 1)

        self.page_widget = QtGui.QTabWidget()
        layout.addWidget(self.page_widget,8,0,1,2)
        self.pages = []
        self.new_log_page()

        self.messageLog = QtGui.QPlainTextEdit()
        self.central.addWidget(self.messageLog)

    def new_log_page(self):
        new_page_widget = QtGui.QWidget()
        layout = QtGui.QGridLayout(new_page_widget)

        scrollArea = QtGui.QScrollArea(new_page_widget)
        scrollArea.setWidgetResizable(True)
        scrollAreaWidgetContents = QtGui.QWidget()
        scrollArea.setWidget(scrollAreaWidgetContents)
        layout.addWidget(scrollArea)

        new_page = QtGui.QGridLayout(scrollAreaWidgetContents)
        fr = len(self.pages)*LOG_PER_PAGE
        to = fr+LOG_PER_PAGE
        self.page_widget.addTab(new_page_widget,str(fr)+' - '+str(to))
        new_page.setAlignment(QtCore.Qt.AlignTop)
        self.pages.append(new_page)

    def filterLogbookOnString(self):
        filterString = str(self.searchStringEdit.text())
        if filterString == '':
            filter_dict = dict.fromkeys(self.logEntryWidgets, True)
            self.filter_logbook(filter_dict=filter_dict)
        else:
            filter_dict = dict.fromkeys(self.logEntryWidgets, False)
            for number, widget in self.logEntryWidgets.items():
                entry = widget.entry
                for snapshot in entry:
                    for value in snapshot.values():
                        try:
                            if isinstance(value, str) and filterString.lower() in value.lower():
                                filter_dict[number] = True
                            else:
                                pass
                        except:
                            raise
            self.filter_logbook(filter_dict=filter_dict)

    def filterLogbookOnTag(self):
        filterTag = str(self.searchTagEdit.text())
        if filterTag == '':
            filter_dict = dict.fromkeys(self.logEntryWidgets, True)
            self.filter_logbook(filter_dict=filter_dict)
        else:
            filter_dict = dict.fromkeys(self.logEntryWidgets, False)
            for number, widget in self.logEntryWidgets.items():
                entry = widget.entry
                for snapshot in entry:
                    if 'Tags' in snapshot and \
                       filterTag in snapshot['Tags'] and \
                       snapshot['Tags'][filterTag]:
                        filter_dict[number] = True
            self.filter_logbook(filter_dict=filter_dict)

    def filter_logbook(self,filter_dict):
        for key,val in filter_dict.items():
            if val:
                self.logEntryWidgets[key].setVisible(True)
            else:
                self.logEntryWidgets[key].setHidden(True)

    def add_entry_to_ui(self,number,entry):
        if not number in self.logEntryWidgets.keys():
            widget = LogEntryWidget(text='Entry ' + str(int(number)),
                                    entry=entry,
                                    number=number)
            self.logEntryWidgets[number] = widget

            self.logEntryWidgets[number].createFrame()

            self.logEntryWidgets[number].submitSig.connect(self.submit_change)
            self.logEntryWidgets[number].submitTagSig.connect(self.submit_new_tag)
            self.logEntryWidgets[number].addFieldSig.connect(self.submit_new_field)
        
            self.pages[-1].addWidget(self.logEntryWidgets[number], number, 0)

            if self.pages[-1].count() >= LOG_PER_PAGE:
                self.new_log_page()
        else:
            self.edit_entry_ui(number,entry,suppress_new = True)

    def edit_entry_ui(self,number,entry,suppress_new = False):
        self.logEntryWidgets[number].entry = entry
        self.logEntryWidgets[number].clearFrame()
        self.logEntryWidgets[number].createFrame()
        if not suppress_new:
            self.logEntryWidgets[number].showNew()

    def add_entry_to_log(self):
        self.man.add_request(('add_entry_to_log',{}))

    def add_entry_to_log_reply(self,track,params):
        self.messageUpdateSignal.emit(
            {'track':track,'args':[[0],"Add entry instruction received"]})

    def submit_change(self):
        number = self.sender().number
        entry = self.sender().entry
        self.man.add_request(('change_entry',{'number':[number],
                                              'entry':entry[-1]}))

    def change_entry_reply(self,track,params):
        self.messageUpdateSignal.emit(
            {'track':track,'args':[[0],"Change entry instruction received"]})

    def submit_new_field(self):
        field_name, result = FieldAdditionDialog.getInfo()
        if result:
            self.man.add_request(('add_new_field', {'field_name':field_name}))

    def add_new_field_reply(self,track,params):
        self.messageUpdateSignal.emit(
            {'track':track,'args':[[0],"Add field instruction received"]})

    def submit_new_tag(self):
        number = self.sender().number
        tag_name, result = QtGui.QInputDialog.getItem(self, 'Tag Input Dialog', 
                'Choose a tag or enter new tag:', self.tags)

        if result:
            self.man.add_request(('add_new_tag', {'tag_name':tag_name,
                                                  'number':number}))

    def add_new_tag_reply(self,track,params):
        tag_name = params['tag_name']
        if not tag_name in self.tags:
            self.tags.append(tag_name)

    def add_manager(self):
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
                self.messageUpdateSignal.emit({'track':track,'args':status_update})
            params = getattr(self, function)(track, args)

        else:
            exception = message['reply']['parameters']['exception']
            self.messageUpdateSignal.emit(
                {'track':track,'args':[[1],"Received status fail in reply\n:{}".format(exception)]})
    
    def updateMessages(self,info):
        track,message = info['track'],info['args']
        text = '{}: {} reports {}'.format(track[-1][1],track[-1][0],message[1])
        if message[0][0] == 0:
            self.messageLog.appendPlainText(text)        
        else:
            error_dialog = QtGui.QErrorMessage(self)
            error_dialog.showMessage(text)
            error_dialog.exec_()

    def logbook_status_reply(self,track,params):
        log_edit_numbers = params['log_edit_numbers']
        log_edits = params['log_edits']
        self.log_edits.extend(log_edits)

        for number,edit in zip(log_edit_numbers,log_edits):
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
        print(connector.acceptor_name + ' connection failure')

    def closeEvent(self, event):
        self.timer.stop()
        self.stopIOLoop()
        event.accept()

