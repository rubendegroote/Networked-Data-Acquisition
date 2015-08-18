from backend.Manager import makeManager
import asyncore
import sys
from PyQt4 import QtCore,QtGui

def main():
    try:
        m = makeManager(5004)
        style = "QLabel { background-color: green }"
        e = ''
    except Exception as error:
        e = str(error)
        style = "QLabel { background-color: red }"

    # Small visual indicator that this is running
    app = QtGui.QApplication(sys.argv)
    w = QtGui.QWidget()
    w.setGeometry(300, 300, 250, 150)

    w.setWindowTitle('Manager')
    layout = QtGui.QGridLayout(w)
    label = QtGui.QLabel(e)
    label.setStyleSheet(style)
    layout.addWidget(label)
    w.show()
    
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
