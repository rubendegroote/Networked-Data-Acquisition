from PyQt4 import QtCore, QtGui

class Spin(QtGui.QLineEdit):
    sigValueChanging = QtCore.pyqtSignal()
    def __init__(self,value=0,min=0,max=10**4,sig_figs=4):
        try:
            super(Spin,self).__init__(text=str(value))
            self.min = min
            self.max = max
            self.sig_figs = sig_figs
            self._value = value
        except:
            pass

        self.returnPressed.connect(self.sigValueChanging.emit)


    @property
    def value(self):
        return self._value

    @value.setter
    def value(self,val):
        val = float(val)
        val = max(self.min,val)
        val = min(self.max,val)
        self._value = round(val,self.sig_figs)

        l = len(self.text())
        pos = self.cursorPosition()

        self.setText(str(self.value))
        if l < len(self.text()):
            pos = pos + 1
        elif l < len(self.text()): 
            pos = pos - 1

        self.setCursorPosition(pos)

    def setText(self,text):
        self._value = float(text)
        super(Spin,self).setText(str(text))

    def keyPressEvent(self,e):
        text = self.text()
        if e.key() == QtCore.Qt.Key_Up or e.key() == QtCore.Qt.Key_Down:
            pos = self.cursorPosition()
            order = len(str(int(float(text))))
            if not pos == order + 1:
                if pos > order:
                    pos = pos - 1
                change = 10**(order - pos)
                if e.key() == QtCore.Qt.Key_Down:
                    change = - change

                self.value = self.value + change
        
        else:
            super(Spin,self).keyPressEvent(e)
            self._value = float(self.text())
            return

        if not text == self.text():
            self.sigValueChanging.emit()
