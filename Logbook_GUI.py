import sys
from PyQt4 import QtCore, QtGui
from multiprocessing import freeze_support

from backend.logbook import *
from LogbookApp import LogbookApp

if __name__ == "__main__":
    # add freeze support
    freeze_support()
    app = QtGui.QApplication(sys.argv)
    m = LogbookApp()
    sys.exit(app.exec_())
