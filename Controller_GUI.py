from PyQt4 import QtCore,QtGui
import pyqtgraph as pg
from ControllerApp import ControllerApp
from multiprocessing import freeze_support
import sys

if __name__ == "__main__":
    # add freeze support
    freeze_support()
    app = QtGui.QApplication(sys.argv)
    m = ControllerApp()
    sys.exit(app.exec_())
