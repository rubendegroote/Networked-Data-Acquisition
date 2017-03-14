from PyQt5 import QtCore, QtGui, QtWidgets


class ConnectionsWidget(QtWidgets.QWidget):
    newConn = QtCore.pyqtSignal(tuple)
    newDevice = QtCore.pyqtSignal(tuple)

    def __init__(self):
        super(ConnectionsWidget, self).__init__()
        self.layout = QtWidgets.QGridLayout(self)

        self.addConButton = QtWidgets.QPushButton('Add Connection')
        self.addConButton.clicked.connect(self.addConn)
        self.layout.addWidget(self.addConButton)

        self.devicesLabel = QtWidgets.QLabel()
        self.deviceText = ""
        self.layout.addWidget(self.devicesLabel)

    def addConn(self):
        respons = ConnectionDialog.getInfo(self)
        if respons[1]:
            self.newConn.emit(respons[0])

class ConnectionDialog(QtWidgets.QDialog):

    def __init__(self, parent=None):
        super(ConnectionDialog, self).__init__(parent)
        self.channel = '127.0.0.1'
        self.port = 5005

        layout = QtWidgets.QGridLayout(self)

        layout.addWidget(QtWidgets.QLabel('Channel'), 1, 0, 1, 1)
        self.channelBox = QtWidgets.QLineEdit(self, text=self.channel)
        layout.addWidget(self.channelBox, 2, 0, 1, 1)
        layout.addWidget(QtWidgets.QLabel('Port'), 1, 1, 1, 1)
        self.portBox = QtWidgets.QLineEdit(self, text=str(self.port))
        layout.addWidget(self.portBox, 2, 1, 1, 1)

        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel,
            QtCore.Qt.Horizontal)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons, 3, 1, 1, 2)

    def getData(self):
        return (self.channelBox.text(),
                self.portBox.text(),)

    @staticmethod
    def getInfo(parent=None):
        dialog = ConnectionDialog(parent)
        result = dialog.exec_()
        data = dialog.getData()
        return (data, result == QtWidgets.QDialog.Accepted)
