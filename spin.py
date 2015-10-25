from PyQt4 import QtCore, QtGui


class Spin(QtGui.QLineEdit):
    sigValueChanging = QtCore.pyqtSignal()
    def __init__(self,*args,**kwargs):
        super(Spin,self).__init__(*args,**kwargs)

        self._value = int(self.text())

        self.min = 0
        self.max = 10**4

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self,val):
        val = int(val)
        val = max(self.min,val)
        val = min(self.max,val)
        self._value = val

        l = len(self.text())
        pos = self.cursorPosition()
        self.setText(str(self.value))
        if l < len(self.text()):
            pos = pos + 1
        elif l < len(self.text()): 
            pos = pos - 1
        self.setCursorPosition(pos)

    def setText(self,text):
        self._value = int(text)
        super(Spin,self).setText(str(self._value))

    def keyPressEvent(self,e):
        text = self.text()
        if e.key() == QtCore.Qt.Key_Up or e.key() == QtCore.Qt.Key_Down:
            pos = self.cursorPosition()
            change = 10**(len(self.text())-pos)
            if e.key() == QtCore.Qt.Key_Down:
                change = - change

            self.value = self.value + change
        
        else:
            super(Spin,self).keyPressEvent(e)

        if not text == self.text():
            self.value = self.text()
            self.sigValueChanging.emit()