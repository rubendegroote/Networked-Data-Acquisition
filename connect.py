from PyQt4 import QtCore,QtGui

class ConnectionsWidget(QtGui.QWidget):
    newConn = QtCore.Signal(tuple)
    def __init__(self):
        super(ConnectionsWidget,self).__init__()
        self.layout = QtGui.QGridLayout(self)

        self.addConButton = QtGui.QPushButton('Add Connection')
        self.addConButton.clicked.connect(self.addConn)

        self.layout.addWidget(self.addConButton)

    def addConn(self):
        respons = ConnectionDialog.getInfo(self)
        if respons[1]:
            self.newConn.emit(respons[0])

class ConnectionDialog(QtGui.QDialog):
    def __init__(self, parent=None):
        super(ConnectionDialog,self).__init__(parent)
        self.channel = 'localhost'
        self.port = 5005

        layout = QtGui.QGridLayout(self)

        layout.addWidget(QtGui.QLabel('Channel'),1,0,1,1)        
        self.channelBox = QtGui.QLineEdit(self,text="KSF402")
        layout.addWidget(self.channelBox,2,0,1,1)
        layout.addWidget(QtGui.QLabel('Port'),1,1,1,1)
        self.portBox = QtGui.QLineEdit(self,text="5004")
        layout.addWidget(self.portBox,2,1,1,1)

        buttons = QtGui.QDialogButtonBox(
            QtGui.QDialogButtonBox.Ok | QtGui.QDialogButtonBox.Cancel,
            QtCore.Qt.Horizontal)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons,3,1,1,2)


    def getData(self):
        return (self.channelBox.text(),
                self.portBox.text(),)

    @staticmethod
    def getInfo(parent = None):
        dialog = ConnectionDialog(parent)
        result = dialog.exec_()
        data = dialog.getData()
        return (data, result == QtGui.QDialog.Accepted)