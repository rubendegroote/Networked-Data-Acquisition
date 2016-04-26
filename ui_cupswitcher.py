from PyQt4.uic import loadUiType
from PyQt4.QtCore import SIGNAL
from PyQt4.QtCore import QTimer

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
import visa

# portName="COM6"

Ui_Form, QWidget = loadUiType('cupswitcher.ui')


class CupSwitcher(QWidget,Ui_Form):

	def __init__(self):
		super(CupSwitcher,self).__init__()
		self.setupUi(self) #and setupUi method
		self.config={}
		self.load_config()

		self.pushCup.clicked.connect(self.switch_cup)
		self.connect(self.chooseCup,SIGNAL("currentIndexChanged(int)"),self.view_cup)

		self.checkPico.setStyleSheet("QLabel { background-color: red; }")
		self.checkRelay.setStyleSheet("QLabel { background-color: red; }")

		rm = visa.ResourceManager()
		self.switch = rm.open_resource('GPIB0::15::INSTR')
		#self.switch.write('*RST')

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

	def switch_cup(self):
		print("switching cup")
		#print(str(self.chooseCup.currentIndex()))
		cup=int(self.chooseCup.currentIndex())


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

			#switch relays# - make sure config is in physical seqential order..
			relay_on={}
			for cups in range(0,cup+1):#turns on relays up to the chosen cup
					relay=self.config[cups,2]
					try: relay_on[relay]
					except:
						self.relay_write(relay,"on")
						relay_on[relay]=True

			for cups in range(cup+1,int(len(self.config)/3)): #turns off remaining relays/cups
					relay=self.config[cups,2]
					try:
						if relay_on[relay]:
							break
					except:
						self.relay_write(relay,"off")
						relay_on[relay]=False

			#switch picoammeter channel
			for card in range(1,3):#close other channels
				for chan in range(1,11):
					self.switch.write(":open (@ "+str(card)+"!"+str(chan)+")") # close 'all' might work too
					#self.switch.write(":close (@ "+str(card)+"!"+str(chan)+")") # close 'all' might work too

			ch_switch=self.config[cup,1]
			#self.switch.write(":open (@ "+ch_switch+")")
			self.switch.write(":close (@ "+ch_switch+")")

	def view_cup(self):
		print("checking cup")
		cup=int(self.chooseCup.currentIndex())
		relay=self.config[cup,2]
		ch_switch=self.config[cup,1]

		# if bool(self.switch.query(":open? (@ "+ch_switch+")")):
		# 	print(self.switch.query(":open? (@ "+ch_switch+")"))
		if not bool(self.switch.query(":open? (@ "+ch_switch+")")):
			print(self.switch.query(":open? (@ "+ch_switch+")"))
			#self.checkPico.setStyleSheet("QLabel { background-color: green; }")
		else:
			self.checkPico.setStyleSheet("QLabel { background-color: red; }")


		# if self.relay_read(relay):
		# 	self.checkRelay.setStyleSheet("QLabel { background-color: green; }")
		# else:
		# 	self.checkRelay.setStyleSheet("QLabel { background-color: red; }")


	def load_config(self):
		sc=open('switcher_config','r')

		linenum=0
		for line in sc:
			self.config[linenum,0],self.config[linenum,1],self.config[linenum,2]=[x.strip() for x in line.split(',')]
			linenum=linenum+1

		for i in range(0,int(len(self.config)/3)):
			self.chooseCup.addItem(str(self.config[i,0]))

	def relay_write(self,relayNum,relayCmd):
		#print("relay:",relayNum,relayCmd)
		pass
		# serPort = serial.Serial(portName, 19200, timeout=1)

		# if (int(relayNum) < 10):
		# 	relayIndex = str(relayNum)
		# else:
		# 	relayIndex = chr(55 + int(relayNum))

		# serPort.write("relay "+ str(relayCmd) +" "+ relayIndex + "\n\r")

		# serPort.close()
		# return True

	def relay_read(self,relayNum):
		pass
		return True

		# serPort = serial.Serial(portName, 19200, timeout=1)

		# if (int(relayNum) < 10):
		# 	relayIndex = str(relayNum)
		# else:
		# 	relayIndex = chr(55 + int(relayNum))

		# serPort.write("relay read "+ relayIndex + "\n\r")

		# response = serPort.read(25)
		# serPort.close()

		# if(response.find("on") > 0):
		# 	#print ("Relay " + str(relayNum) +" is ON")
		# 	return True

		# elif(response.find("off") > 0):
		# 	#print ("Relay " + str(relayNum) +" is OFF")
		# 	return False

	# def switch_write(self,chan):
	# 	pass

	# def switch_read(self,chan):
	# 	pass


if __name__ == '__main__':
	import sys
	from PyQt4 import QtGui

	app = QtGui.QApplication(sys.argv)
	form=CupSwitcher()
	form.show()
	form.resize(0, 0)
	sys.exit(app.exec_())


    # def read_from_device(self):
    #     ret_list=[]
    #     for card in range(1,2):
    #       for chan in range(1,10):
    #         print("In loop",card,chan)
    #         self.switch.write(":open (@ "+str(card)+"!"+str(chan)+")")
    #         read_i=float(self.pA_meter.query("READ?").split(',')[0].strip('A'))
    #         ret_list.append(read_i)
    #         self.switch.write(":close (@ "+str(card)+"!"+str(chan)+")")
    #         data[chan-1]=read_i

    #         norm = mpl.colors.Normalize(vmin=min(data), vmax=max(data))
    #         cb1 = mpl.colorbar.ColorbarBase(axl, cmap=cmap, norm=norm, orientation='vertical')
    #         cb1.set_label('Amperes')
    #         bullseye_plot(ax, data, cmap=cmap, norm=norm)
    #         plt.draw()
    #         plt.pause(0.001)

    #     return ret_list