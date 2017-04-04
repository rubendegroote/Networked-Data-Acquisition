from PyQt5.uic import loadUiType
from PyQt5.QtCore import QTimer

from PyQt5 import QtCore, QtGui, QtWidgets


from seg_plot import bullseye_plot

import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt

from matplotlib.figure import Figure
from matplotlib.backends.backend_qt4agg import (
    FigureCanvasQTAgg as FigureCanvas,
    NavigationToolbar2QT as NavigationToolbar)

import threading

import visa

Ui_Form, QWidget = loadUiType('7001switcher.ui')

class CupSwitcher(QWidget,Ui_Form):
	switch_sig = QtCore.pyqtSignal(str) 
	def __init__(self):
		super(CupSwitcher,self).__init__()
		self.setupUi(self)
		self.config={}
		self.load_config()
		self.cup_names = []

		rm = visa.ResourceManager()
		self.switch = rm.open_resource('GPIB0::15::INSTR')

		self.pushCup.clicked.connect(self.switch_cup) 
		self.chooseCup.currentIndexChanged.connect(self.view_cup)
		self.view_cup()
		self.none=1

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

		# self.segloop=False 
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
		cup=int(self.chooseCup.currentIndex())
		self.switch.write(":open all")

		###
		self.switch_sig.emit(str(cup))

		if 'segplot' in str(self.chooseCup.currentText()):
			try: #deletes old plot if exists
				self.segloop=True
				print("print segment plot")
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
		####

		ch_switch=self.config[cup,1]

		if int(ch_switch[0]) == 0:
			self.none=0
			self.view_cup()
		else:
			self.none=1
			if int(ch_switch[0]) == 2: self.switch.write(":close (@ 1!10)")
			self.switch.write(":close (@ "+ch_switch+")")
			self.view_cup()

	def view_cup(self):

		cup=int(self.chooseCup.currentIndex())
		ch_switch=self.config[cup,1]

		if int(ch_switch[0]) == 0:
			reply = self.none
		else:
			reply = self.switch.query(":open? (@ "+ch_switch+")")
			reply = reply.strip('\n').strip('\r')

		if int(reply) == 0:
			self.chActive.setStyleSheet("QLabel { background-color: green; }")
		elif int(reply) == 1:
			self.chActive.setStyleSheet("QLabel { background-color: red; }")

	def load_config(self):
		sc=open('7001_config.ini','r')

		linenum=0
		for line in sc:
			self.config[linenum,0],self.config[linenum,1] = [x.strip() for x in line.split(',')]
			linenum=linenum+1

		for i in range(0,int(len(self.config)/2)):
			self.chooseCup.addItem(str(self.config[i,0]))

if __name__ == '__main__':
	import sys

	app = QtWidgets.QApplication(sys.argv)
	form=CupSwitcher()
	form.show()
	form.resize(0, 0)
	sys.exit(app.exec_())