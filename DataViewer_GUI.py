from PyQt4 import QtCore,QtGui
import pyqtgraph as pg
from DataViewerApp import DataViewerApp
from multiprocessing import freeze_support
import sys

pg.setConfigOption('background', 'w')
pg.setConfigOption('foreground', 'k')


if __name__ == "__main__":
    # add freeze support
    freeze_support()
    app = QtGui.QApplication(sys.argv)
    m = DataViewerApp()
    sys.exit(app.exec_())
