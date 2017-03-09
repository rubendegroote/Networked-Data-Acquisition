from PyQt4 import QtCore, QtGui
from multiprocessing import freeze_support
import pyqtgraph as pg
import os,sys

class ScanVisualiser(QtGui.QWidget):
	def __init__(self):
		super(ScanVisualiser,self).__init__()

		self.init_ui()

		self.show()

	def init_ui(self):
		self.layout=QtGui.QGridLayout(self)
		self.plot = pg.PlotWidget()
		self.layout.addWidget(self.plot)

		# self.layout.addWidget(self.add)

	def add_scan(self):
		pass

	def 

def main():
    pg.setConfigOption('background', 'w')
    pg.setConfigOption('foreground', 'k')

    # add freeze support
    freeze_support()
    app = QtGui.QApplication(sys.argv)
    m = ScanVisualiser()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()