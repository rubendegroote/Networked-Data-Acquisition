from PyQt4 import QtCore, QtGui
import threading as th
import asyncore
import time
from multiprocessing import freeze_support
import os,sys
import configparser

from backend.connectors import Connector
from connectiondialogs import ConnectionDialog, FieldAdditionDialog
from logviewerwidgets import LogEntryWidget

CONFIG_PATH = os.getcwd() + "\\Config files\\config.ini"

class LogbookApp(QtGui.QWidget):
    editSignal = QtCore.pyqtSignal(int,object)
    addSignal = QtCore.pyqtSignal(int,object)
    messageUpdateSignal = QtCore.pyqtSignal(dict)
    
    ### get configuration details
    config_parser = configparser.ConfigParser()
    config_parser.read(CONFIG_PATH)
    log_per_page = int(config_parser['other']['log_per_page'])
    controller_channel = (config_parser['IPs']['controller'],
                          int(config_parser['ports']['controller']))
    def __init__(self):
        super(LogbookApp, self).__init__()

        self.log_edits = []
        self.logEntryWidgets = {}
        self.tags = []

        self.controller = None

        self.init_UI()

        self.editSignal.connect(self.edit_entry_ui)
        self.addSignal.connect(self.add_entry_to_ui)

    def define_controller(self,controller):
        self.controller = controller
        self.log_timer = QtCore.QTimer()
        self.log_timer.timeout.connect(self.add_log_request)
        self.log_timer.start(500)

    def add_log_request(self):
        req = 'logbook_status',{'no_of_log_edits':[len(self.log_edits)]}
        self.controller.add_request(req)

    def init_UI(self):
        layout = QtGui.QGridLayout(self)

        self.searchStringLabel = QtGui.QPushButton('String search')
        self.searchStringLabel.clicked.connect(self.filterLogbookOnString)
        self.searchStringEdit = QtGui.QLineEdit('')
        layout.addWidget(self.searchStringEdit, 1, 0)
        layout.addWidget(self.searchStringLabel, 1, 1)

        self.searchTagLabel = QtGui.QPushButton('Tag search')
        self.searchTagLabel.clicked.connect(self.filterLogbookOnTag)
        self.searchTagEdit = QtGui.QLineEdit('')
        layout.addWidget(self.searchTagEdit, 2, 0)
        layout.addWidget(self.searchTagLabel, 2, 1)

        self.searchTagLabel = QtGui.QPushButton('Mass search')
        self.searchTagLabel.clicked.connect(self.filterLogbookOnMass)
        self.searchMassEdit = QtGui.QLineEdit('')
        layout.addWidget(self.searchMassEdit, 3, 0)
        layout.addWidget(self.searchTagLabel, 3, 1)

        self.page_widget = QtGui.QTabWidget()
        layout.addWidget(self.page_widget,4,0,1,2)
        self.pages = []
        self.new_log_page()

        self.addEntryButton = QtGui.QPushButton('Add entry')
        self.addEntryButton.clicked.connect(self.add_entry_to_log)
        layout.addWidget(self.addEntryButton, 5, 0, 1, 2)

    def new_log_page(self):
        new_page_widget = QtGui.QWidget()
        layout = QtGui.QGridLayout(new_page_widget)

        scrollArea = QtGui.QScrollArea(new_page_widget)
        scrollArea.setWidgetResizable(True)
        scrollAreaWidgetContents = QtGui.QWidget()
        scrollArea.setWidget(scrollAreaWidgetContents)
        layout.addWidget(scrollArea)

        new_page = QtGui.QGridLayout(scrollAreaWidgetContents)
        fr = len(self.pages)*self.log_per_page
        to = fr+self.log_per_page
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
                snapshot = entry[-1]
                if 'Tags' in snapshot and \
                        filterTag in snapshot['Tags'] and \
                        snapshot['Tags'][filterTag]:
                    filter_dict[number] = True
            self.filter_logbook(filter_dict=filter_dict)

    def filterLogbookOnMass(self):
        filterMass = str(self.searchMassEdit.text())
        if filterMass == '':
            filter_dict = dict.fromkeys(self.logEntryWidgets, True)
            self.filter_logbook(filter_dict=filter_dict)
        else:
            filter_dict = dict.fromkeys(self.logEntryWidgets, False)
            for number, widget in self.logEntryWidgets.items():
                entry = widget.entry
                snapshot = entry[-1]
                if 'Mass' in snapshot and \
                   filterMass == snapshot['Mass']:
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

            if self.pages[-1].count() >= self.log_per_page:
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
        self.controller.add_request(('add_entry_to_log',{}))

    def add_entry_to_log_reply(self,track,params):
        self.messageUpdateSignal.emit(
            {'track':track,'args':[[0],"Add entry instruction received"]})

    def submit_change(self):
        number = self.sender().number
        entry = self.sender().entry
        self.controller.add_request(('change_entry',{'number':[number],
                                              'entry':entry[-1]}))

    def change_entry_reply(self,track,params):
        self.messageUpdateSignal.emit(
            {'track':track,'args':[[0],"Change entry instruction received"]})

    def submit_new_field(self):
        field_name, result = FieldAdditionDialog.getInfo()
        if result:
            self.controller.add_request(('add_new_field', {'field_name':field_name}))

    def add_new_field_reply(self,track,params):
        self.messageUpdateSignal.emit(
            {'track':track,'args':[[0],"Add field instruction received"]})

    def submit_new_tag(self):
        number = self.sender().number
        tag_name, result = QtGui.QInputDialog.getItem(self, 'Tag Input Dialog', 
                'Choose a tag or enter new tag:', self.tags)

        if result:
            self.controller.add_request(('add_new_tag', {'tag_name':tag_name,
                                                  'number':number}))

    def add_new_tag_reply(self,track,params):
        tag_name = params['tag_name']
        if not tag_name in self.tags:
            self.tags.append(tag_name)

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
    
    def logbook_status_reply(self,track,params):
        log_edit_numbers = params['log_edit_numbers']
        log_edits = params['log_edits']
        log_edits = log_edits[:20]
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

    def closeEvent(self, event):
        self.timer.stop()
        self.stopIOLoop()
        event.accept()

def main():
    # add freeze support
    app = QtGui.QApplication(sys.argv)
    m = LogbookApp()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()