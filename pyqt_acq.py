from PyQt4 import QtCore,QtGui
import pyqtgraph as pg
from app import Application
from multiprocessing import freeze_support
import sys

pg.setConfigOption('background', 'w')
pg.setConfigOption('foreground', 'k')


if __name__ == "__main__":
    # add freeze support
    freeze_support()
    app = QtGui.QApplication(sys.argv)
    m = Application()
    sys.exit(app.exec_())
