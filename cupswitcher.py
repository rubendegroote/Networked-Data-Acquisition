from PyQt4.uic import loadUiType
from PyQt4 import QtCore, QtGui


from seg_plot import bullseye_plot

import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt

from matplotlib.figure import Figure
from matplotlib.backends.backend_qt4agg import (
    FigureCanvasQTAgg as FigureCanvas,
    NavigationToolbar2QT as NavigationToolbar)

import threading

# import sys
# import serial
# import visa

# portName="COM6"

Ui_Form, QWidget = loadUiType('cupswitcher.ui')

class CupSwitcher(QWidget,Ui_Form):
	switch_sig = QtCore.pyqtSignal(str) 
	def __init__(self):
		super(CupSwitcher,self).__init__()
		self.setupUi(self) #and setupUi method
		self.cup_names = []

		self.pushCup.clicked.connect(self.switch_cup)
		# self.chooseCup.currentIndexChanged.connect(self.view_cup)

		self.checkPico.setStyleSheet("QLabel { background-color: red; }")
		self.checkRelay.setStyleSheet("QLabel { background-color: red; }")

		self.bullplot=bullseye_plot()
		#self.thread1 = threading.Thread(target=self.bull_update)

	def bull_update(self):
		#plt.ion()
		data=np.array([1.1E-13,1.2E-13,3E-13,4.3E-13,2.3E-13,1.2E-13,0.3E-13,0.7E-13,0.9E-13])
		# Make a figure and axes with dimensions as desired.
		self.fig = plt.figure(figsize=(6.5, 5))
		ax=plt.subplot(projection='polar')
		self.fig.canvas.set_window_title('Segmented Faraday Cup Plot')

		# Create the axis for the colorbars
		axl=self.fig.add_axes([0.85, 0.2, 0.05, 0.5])

		# Set the colormap and norm to correspond to the data for which the colorbar will be used.
		cmap = mpl.cm.jet

		norm = mpl.colors.Normalize(vmin=min(data), vmax=max(data))

		cb1 = mpl.colorbar.ColorbarBase(axl, cmap=cmap, norm=norm, orientation='vertical')
		cb1.set_label('Amperes')

		# Create the 9 segment model
		self.bullplot.plot(ax, data, cmap=cmap, norm=norm)
		#ax.set_title('Segmented Faraday cup')

		self.canvas = FigureCanvas(self.fig)
		#self.canvas=self.fig.canvas

		plt.ion()
		#self.setStyleSheet("background-color:transparent;")

		self.segloop=False 
		while self.segloop: #####should spawn seperate thread

			norm = mpl.colors.Normalize(vmin=min(data), vmax=max(data))
			cb1 = mpl.colorbar.ColorbarBase(axl, cmap=cmap, norm=norm, orientation='vertical')
			cb1.set_label('Amperes')
			for x in range(0,9):
				data[x] = np.random.random()

			self.bullplot.plot(ax, data, cmap=cmap, norm=norm)
			#self.canvas=fig.canvas
			#self.gridLayout.addWidget(self.canvas, 2, 0, 1, 5)
			#self.canvas.close()
			#self.canvas.draw()

			plt.pause(0.300)#need this for the self.canvas widget!

			#if plt.
			print(data)

	def setOptions(self,options):

		if self.cup_names == options:
			return

		self.chooseCup.clear()
		for opt in options:
			self.chooseCup.addItem(opt)
		self.cup_names = options

	def switch_cup(self):
		print("switching cup")
		#print(str(self.chooseCup.currentIndex()))
		cup=str(self.chooseCup.currentText())
	
		self.switch_sig.emit(cup)

		if 'segplot' in str(self.chooseCup.currentText()):
			try: #deletes old plot if exists
				plt.close()
				self.canvas.close()
				self.gridLayout.removeWidget(self.canvas)
			except:
				pass

			self.bull_update()

		else:
			self.segloop=False
			try: #deletes old plot if exists
				plt.close()
				self.canvas.close()
				self.gridLayout.removeWidget(self.canvas)
			except:
				pass


if __name__ == '__main__':
	import sys
	from PyQt4 import QtGui

	app = QtGui.QApplication(sys.argv)
	form=CupSwitcher()
	form.show()
	form.resize(0, 0)
	sys.exit(app.exec_())
