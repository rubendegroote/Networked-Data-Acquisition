from PyQt5 import QtCore, QtGui, QtWidgets
import os
import configparser
from config.absolute_paths import CONFIG_PATH

class Contr_DS_ConnectionDialog(QtWidgets.QDialog):
    ### get configuration details
    def __init__(self, parent=None, message=''):
        super(Contr_DS_ConnectionDialog, self).__init__(parent)
        self.config_parser = configparser.ConfigParser()
        self.config_parser.read(CONFIG_PATH)

        ContChannelBoxtext = str(self.config_parser['IPs']['controller'])
        ContPortBoxtext = str(self.config_parser['ports']['controller'])
        
        serverChannelBoxtext = str(self.config_parser['IPs']['data_server'])
        serverPortBoxtext = str(self.config_parser['ports']['data_server'])

        self.layout = QtWidgets.QGridLayout(self)
        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel,
            QtCore.Qt.Horizontal)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        self.layout.addWidget(buttons, 500, 1, 1, 2)

        self.layout.addWidget(QtWidgets.QLabel(message), 0, 0, 1, 1)

        self.layout.addWidget(QtWidgets.QLabel('controller IP'), 1, 1, 1, 1)
        self.ContChannelBox = QtWidgets.QLineEdit(self, text=ContChannelBoxtext)
        self.layout.addWidget(self.ContChannelBox, 2, 1, 1, 1)
        self.layout.addWidget(QtWidgets.QLabel('controller port'), 1, 2, 1, 1)
        self.ContPortBox = QtWidgets.QLineEdit(self, text=ContPortBoxtext)
        self.layout.addWidget(self.ContPortBox, 2, 2, 1, 1)

        self.layout.addWidget(QtWidgets.QLabel('Data server IP'), 3, 1, 1, 1)
        self.serverChannelBox = QtWidgets.QLineEdit(self, text=serverChannelBoxtext)
        self.layout.addWidget(self.serverChannelBox, 4, 1, 1, 1)
        self.layout.addWidget(QtWidgets.QLabel('Data server port'), 3, 2, 1, 1)
        self.ServerPortBox = QtWidgets.QLineEdit(self, text=serverPortBoxtext)
        self.layout.addWidget(self.ServerPortBox, 4, 2, 1, 1)

    def getData(self):
        return (self.ContChannelBox.text(), self.ContPortBox.text(),
                self.serverChannelBox.text(), self.ServerPortBox.text())

    @staticmethod
    def getInfo(parent=None, message=''):
        dialog = Contr_DS_ConnectionDialog(parent, message)
        result = dialog.exec_()
        data = dialog.getData()
        return (data, result == QtWidgets.QDialog.Accepted)


class ConnectionDialog(QtWidgets.QDialog):

    def __init__(self, parent=None):
        super(ConnectionDialog, self).__init__(parent)
        self.layout = QtWidgets.QGridLayout(self)
        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel,
            QtCore.Qt.Horizontal)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        self.layout.addWidget(buttons, 500, 1, 1, 2)

        self.layout.addWidget(QtWidgets.QLabel('Channel'), 1, 0, 1, 1)
        self.channelBox = QtWidgets.QLineEdit(self, text='127.0.0.1')
        self.layout.addWidget(self.channelBox, 2, 0, 1, 1)

        self.layout.addWidget(QtWidgets.QLabel('Port'), 1, 1, 1, 1)
        self.portBox = QtWidgets.QLineEdit(self, text='5005')
        self.layout.addWidget(self.portBox, 2, 1, 1, 1)

    def getData(self):
        return (self.channelBox.text(),
                self.portBox.text())

    @staticmethod
    def getInfo(parent=None):
        dialog = ConnectionDialog(parent)
        result = dialog.exec_()
        data = dialog.getData()
        return (data, result == QtWidgets.QDialog.Accepted)


class FieldAdditionDialog(QtWidgets.QDialog):

    def __init__(self, parent=None):
        super(FieldAdditionDialog, self).__init__(parent)
        self.layout = QtWidgets.QGridLayout(self)
        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel,
            QtCore.Qt.Horizontal)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        self.layout.addWidget(buttons, 500, 1, 1, 2)

        self.layout.addWidget(QtWidgets.QLabel('Field name'), 1, 0, 1, 1)
        self.fieldBox = QtWidgets.QLineEdit(self, text='')
        self.layout.addWidget(self.fieldBox, 2, 0, 1, 1)

    def getData(self):
        return self.fieldBox.text()

    @staticmethod
    def getInfo(parent=None):
        dialog = FieldAdditionDialog(parent)
        result = dialog.exec_()
        data = dialog.getData()
        return (data, result == QtWidgets.QDialog.Accepted)
