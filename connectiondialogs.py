from PyQt4 import QtCore,QtGui

class Man_DS_ConnectionDialog(QtGui.QDialog):
    def __init__(self, parent=None,message = ''):
        super(Man_DS_ConnectionDialog,self).__init__(parent)
        self.layout = QtGui.QGridLayout(self)
        buttons = QtGui.QDialogButtonBox(
            QtGui.QDialogButtonBox.Ok | QtGui.QDialogButtonBox.Cancel,
            QtCore.Qt.Horizontal)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        self.layout.addWidget(buttons,500,1,1,2)

        self.layout.addWidget(QtGui.QLabel(message),0,0,1,1)

        self.layout.addWidget(QtGui.QLabel('Channel'),1,1,1,1)
        self.ManChannelBox = QtGui.QLineEdit(self,text='KSF402')
        self.layout.addWidget(self.ManChannelBox,2,1,1,1)
        self.layout.addWidget(QtGui.QLabel('Port'),1,2,1,1)
        self.ManPortBox = QtGui.QLineEdit(self,text='5007')
        self.layout.addWidget(self.ManPortBox,2,2,1,1)

        self.layout.addWidget(QtGui.QLabel('Channel'),3,1,1,1)
        self.DSChannelBox = QtGui.QLineEdit(self,text='KSF402')
        self.layout.addWidget(self.DSChannelBox,4,1,1,1)
        self.layout.addWidget(QtGui.QLabel('Port'),3,2,1,1)
        self.DSPortBox = QtGui.QLineEdit(self,text='5006')
        self.layout.addWidget(self.DSPortBox,4,2,1,1)

    def getData(self):
        return (self.ManChannelBox.text(),self.ManPortBox.text(),
                self.DSChannelBox.text(),self.DSPortBox.text())
                
    @staticmethod
    def getInfo(parent = None,message=''):
        dialog = Man_DS_ConnectionDialog(parent,message)
        result = dialog.exec_()
        data = dialog.getData()
        return (data, result == QtGui.QDialog.Accepted)

class ConnectionDialog(QtGui.QDialog):
    def __init__(self, parent=None):
        super(ConnectionDialog,self).__init__(parent)
        self.layout = QtGui.QGridLayout(self)
        buttons = QtGui.QDialogButtonBox(
            QtGui.QDialogButtonBox.Ok | QtGui.QDialogButtonBox.Cancel,
            QtCore.Qt.Horizontal)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        self.layout.addWidget(buttons,500,1,1,2)

        self.layout.addWidget(QtGui.QLabel('Channel'),1,0,1,1)  
        self.channelBox = QtGui.QLineEdit(self,text='KSF402')
        self.layout.addWidget(self.channelBox,2,0,1,1)
        
        self.layout.addWidget(QtGui.QLabel('Port'),1,1,1,1)
        self.portBox = QtGui.QLineEdit(self,text='5005')
        self.layout.addWidget(self.portBox,2,1,1,1)


    def getData(self):
        return (self.channelBox.text(),
                self.portBox.text())
                
    @staticmethod
    def getInfo(parent = None):
        dialog = ConnectionDialog(parent)
        result = dialog.exec_()
        data = dialog.getData()
        return (data, result == QtGui.QDialog.Accepted)