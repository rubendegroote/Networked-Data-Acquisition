from PyQt4 import QtCore,QtGui

class ScannerWidget(QtGui.QWidget):
    def __init__(self):
        super(ScannerWidget,self).__init__()
        self.layout = QtGui.QGridLayout(self)
        self.layout.addWidget(QtGui.QLabel('test'),0,0,0,0)
