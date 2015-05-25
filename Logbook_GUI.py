from PyQt4 import QtCore, QtGui
import pyqtgraph as pg
from LogbookApp import LogbookApp
from multiprocessing import freeze_support
import sys
from backend.logbook import *

if __name__ == "__main__":
    # add freeze support
    freeze_support()
    app = QtGui.QApplication(sys.argv)
    m = LogbookApp()
    sys.exit(app.exec_())
