from PyQt4 import QtCore, QtGui


class ConversionWidget(QtGui.QWidget):
    def __init__(self):
        super(ConversionWidget,self).__init__()

        layout = QtGui.QGridLayout(self)

        layout.addWidget(QtGui.QLabel('Wavenumber difference'),0,0)
        self.wn_box = QtGui.QLineEdit('0.001')
        self.wn_box.textChanged.connect(self.update_wn)
        layout.addWidget(self.wn_box,0,1)

        layout.addWidget(QtGui.QLabel('Frequency difference'),0,2)
        self.freq_box = QtGui.QLineEdit()
        self.freq_box.textChanged.connect(self.update_freq)
        layout.addWidget(self.freq_box,0,3)

        self.update_wn()

    def update_wn(self):
        self.wn_box.textChanged.disconnect(self.update_wn)
        self.freq_box.textChanged.disconnect(self.update_freq)

        wn = float(self.wn_box.text()) 
        freq = wn * 30000
        self.freq_box.setText(str(freq))

        self.wn_box.textChanged.connect(self.update_wn)
        self.freq_box.textChanged.connect(self.update_freq)


    def update_freq(self):
        self.wn_box.textChanged.disconnect(self.update_wn)
        self.freq_box.textChanged.disconnect(self.update_freq)

        freq = float(self.freq_box.text())
        wn = freq / 30000
        self.wn_box.setText(str(wn))

        self.wn_box.textChanged.connect(self.update_wn)
        self.freq_box.textChanged.connect(self.update_freq)


