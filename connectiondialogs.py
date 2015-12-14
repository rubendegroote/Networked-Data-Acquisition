from PyQt4 import QtCore, QtGui
import os
import configparser

CONFIG_PATH = os.getcwd() + "\\config.ini"


class Man_DS_ConnectionDialog(QtGui.QDialog):
    ### get configuration details
    config_parser = configparser.ConfigParser()
    config_parser.read(CONFIG_PATH)
    def __init__(self, parent=None, message=''):
        super(Man_DS_ConnectionDialog, self).__init__(parent)
        ContChannelBoxtext = str(self.config_parser['IPs']['controller'])
        ContPortBoxtext = str(self.config_parser['ports']['controller'])
        serverChannelBoxtext = str(self.config_parser['IPs']['server'])
        serverPortBoxtext = str(self.config_parser['ports']['server'])

        self.layout = QtGui.QGridLayout(self)
        buttons = QtGui.QDialogButtonBox(
            QtGui.QDialogButtonBox.Ok | QtGui.QDialogButtonBox.Cancel,
            QtCore.Qt.Horizontal)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        self.layout.addWidget(buttons, 500, 1, 1, 2)

        self.layout.addWidget(QtGui.QLabel(message), 0, 0, 1, 1)

        self.layout.addWidget(QtGui.QLabel('Channel'), 1, 1, 1, 1)
        self.ContChannelBox = QtGui.QLineEdit(self, text=ContChannelBoxtext)
        self.layout.addWidget(self.ContChannelBox, 2, 1, 1, 1)
        self.layout.addWidget(QtGui.QLabel('Port'), 1, 2, 1, 1)
        self.ContPortBox = QtGui.QLineEdit(self, text=ContPortBoxtext)
        self.layout.addWidget(self.ContPortBox, 2, 2, 1, 1)

        self.layout.addWidget(QtGui.QLabel('Channel'), 3, 1, 1, 1)
        self.serverChannelBox = QtGui.QLineEdit(self, text=serverChannelBoxtext)
        self.layout.addWidget(self.serverChannelBox, 4, 1, 1, 1)
        self.layout.addWidget(QtGui.QLabel('Port'), 3, 2, 1, 1)
        self.ServerPortBox = QtGui.QLineEdit(self, text=ServerPortBoxtext)
        self.layout.addWidget(self.ServerPortBox, 4, 2, 1, 1)

    def getData(self):
        return (self.ContChannelBox.text(), self.ContPortBox.text(),
                self.serverChannelBox.text(), self.ServerPortBox.text())

    @staticmethod
    def getInfo(parent=None, message=''):
        dialog = Man_DS_ConnectionDialog(parent, message)
        result = dialog.exec_()
        data = dialog.getData()
        return (data, result == QtGui.QDialog.Accepted)


class ConnectionDialog(QtGui.QDialog):

    def __init__(self, parent=None):
        super(ConnectionDialog, self).__init__(parent)
        self.layout = QtGui.QGridLayout(self)
        buttons = QtGui.QDialogButtonBox(
            QtGui.QDialogButtonBox.Ok | QtGui.QDialogButtonBox.Cancel,
            QtCore.Qt.Horizontal)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        self.layout.addWidget(buttons, 500, 1, 1, 2)

        self.layout.addWidget(QtGui.QLabel('Channel'), 1, 0, 1, 1)
        self.channelBox = QtGui.QLineEdit(self, text='127.0.0.1')
        self.layout.addWidget(self.channelBox, 2, 0, 1, 1)

        self.layout.addWidget(QtGui.QLabel('Port'), 1, 1, 1, 1)
        self.portBox = QtGui.QLineEdit(self, text='5005')
        self.layout.addWidget(self.portBox, 2, 1, 1, 1)

    def getData(self):
        return (self.channelBox.text(),
                self.portBox.text())

    @staticmethod
    def getInfo(parent=None):
        dialog = ConnectionDialog(parent)
        result = dialog.exec_()
        data = dialog.getData()
        return (data, result == QtGui.QDialog.Accepted)


class FieldAdditionDialog(QtGui.QDialog):

    def __init__(self, parent=None):
        super(FieldAdditionDialog, self).__init__(parent)
        self.layout = QtGui.QGridLayout(self)
        buttons = QtGui.QDialogButtonBox(
            QtGui.QDialogButtonBox.Ok | QtGui.QDialogButtonBox.Cancel,
            QtCore.Qt.Horizontal)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        self.layout.addWidget(buttons, 500, 1, 1, 2)

        self.layout.addWidget(QtGui.QLabel('Field name'), 1, 0, 1, 1)
        self.fieldBox = QtGui.QLineEdit(self, text='')
        self.layout.addWidget(self.fieldBox, 2, 0, 1, 1)

    def getData(self):
        return self.fieldBox.text()

    @staticmethod
    def getInfo(parent=None):
        dialog = FieldAdditionDialog(parent)
        result = dialog.exec_()
        data = dialog.getData()
        return (data, result == QtGui.QDialog.Accepted)
