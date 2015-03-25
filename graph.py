import pyqtgraph as pg
from PyQt4 import QtCore,QtGui
import pyqtgraph.dockarea as da
import datetime

from picbutton import PicButton

class GraphDock(pg.dockarea.Dock):
    def __init__(self,name):
        super(GraphDock,self).__init__(name)
        self.graph = MyGraph(name)
        self.layout.addWidget(self.graph)

class MyGraph(QtGui.QWidget):
    def __init__(self,name):
        super(QtGui.QWidget,self).__init__()

        self.options = []
        self.name = name

        self.layout = QtGui.QGridLayout(self)

        self.labelStyle = {'font-size': '18pt'}

        gView = pg.GraphicsView()

        self.graph = pg.PlotWidget()
        self.graph.showGrid(x=True, y=True,alpha=0.7)

        layout = QtGui.QGridLayout(gView)
        layout.addWidget(self.graph,0,0,1,1)

        self.sublayout = QtGui.QGridLayout()
        layout.addLayout(self.sublayout,1,0)

        self.comboY = QtGui.QComboBox(parent = None)
        self.comboY.setToolTip('Choose the variable you want to put\
 on the Y-axis.')
        self.comboY.currentIndexChanged.connect(self.newXY)
        self.sublayout.addWidget(self.comboY,0,1)

        label = QtGui.QLabel('vs')
        label.setStyleSheet("border: 0px;");
        self.sublayout.addWidget(label,0,2)

        self.comboX = QtGui.QComboBox(parent = None)
        self.comboX.setToolTip('Choose the variable you want to put\
 on the X-axis.')
        self.comboX.currentIndexChanged.connect(self.newXY)
        self.sublayout.addWidget(self.comboX,0,3)

 #        self.mathCheckBox = QtGui.QCheckBox('Mathy math math')
 #        self.mathCheckBox.setToolTip('Check this box if you want to some\
 # math on the data before it is plotted.')
 #        self.mathCheckBox.stateChanged.connect(self.enableMathPanel)
 #        self.sublayout.addWidget(self.mathCheckBox,1,0)

        self.freqUnitSelector = QtGui.QComboBox(parent = None)
        self.freqUnitSelector.setToolTip('Choose the units you want to\
 display the frequency in.')
        self.freqUnitSelector.addItems(['Frequency','Wavelength','Wavenumber'])
        # self.freqUnitSelector.currentIndexChanged.connect(self.updatePlot)
        self.sublayout.addWidget(self.freqUnitSelector,0,5)

        self.meanStyles = ['Combined','Per Capture', 'Per Scan']
        self.meanBox = QtGui.QComboBox(self)
        self.meanBox.setToolTip('Choose how you want to combine data\
 from all of the scans in the captures this graph plots.')
        self.meanBox.addItems(self.meanStyles)
        self.meanBox.setCurrentIndex(1)
        self.meanBox.setMaximumWidth(110)
        # self.meanBox.currentIndexChanged.connect(self.updatePlot)
        self.sublayout.addWidget(self.meanBox,2,1)

        self.graphStyles = ['Step (histogram)', 'Line']#, 'Point']

        self.graphBox = QtGui.QComboBox(self)
        self.graphBox.setToolTip('Choose how you want to plot the data:\
 as a binned histogram, or the raw data. The latter strains the a lot pc though!')
        self.graphBox.addItems(self.graphStyles)
        self.graphBox.setCurrentIndex(0)
        self.graphBox.setMaximumWidth(110)
        # self.graphBox.currentIndexChanged.connect(self.updatePlot)
        self.sublayout.addWidget(self.graphBox,2,2)

        self.binLabel = QtGui.QLabel(self, text="Bin size: ")
        self.binSpinBox = pg.SpinBox(value = 1000,
            bounds = (0,None), dec = False)
        self.binSpinBox.setToolTip('Choose the bin size\
 used to bin the data.')
        self.binSpinBox.setMaximumWidth(110)
        # self.binSpinBox.sigValueChanged.connect(self.updatePlot)
        
        self.sublayout.addWidget(self.binLabel,2,3)
        self.sublayout.addWidget(self.binSpinBox,2,4)      
        

        self.saveButton = PicButton('save',checkable = False,size = 25)
        self.saveButton.setToolTip('Save the current graph to file.')
        # self.saveButton.clicked.connect(self.saveSpectrum)
        self.sublayout.addWidget(self.saveButton, 0,7,1,1)

        self.settingsButton = PicButton('settings',checkable = True,size = 25)
        self.settingsButton.setToolTip('Display the advanced plotting options.')
        # self.settingsButton.clicked.connect(self.showSettings)
        self.sublayout.addWidget(self.settingsButton, 0,8,1,1)

        self.sublayout.setColumnStretch(6,1)

        # self.settingsWidget = GraphSettingsWidget()
        # self.settingsWidget.updatePlot.connect(self.updatePlot)
        # self.meanBox.currentIndexChanged.connect(self.settingsWidget.onStyleChanged) 
            #line above is MEGAHACK to have updating results table in analysiswidget
        # self.settingsWidget.setVisible(False)

        self.layout.addWidget(gView,0,0)
        # self.layout.addWidget(self.settingsWidget,0,1)

    def plot(self,data):
        try:
            data = data.dropna()
            try:
                time = (data['time'].values-datetime.datetime(1970,1,1))
                data['time'] = [t.total_seconds() for t in time]
            except:
                pass

            columns = data.columns.values
            self.graph.plot(data[columns[0]].values,data[columns[1]].values, 
                pen = 'r', clear = True)
        except Exception as e:
            pass

    def setXYOptions(self,options):
        if not options == self.options:
            self.options = options
            curX = int(self.comboX.currentIndex())
            curY = int(self.comboY.currentIndex())
            self.comboX.clear()
            self.comboX.addItems(options)

            self.comboY.clear()
            self.comboY.addItems(options)

            self.comboX.setCurrentIndex(curX)
            self.comboY.setCurrentIndex(curY)

        else:
            pass

    def newXY(self):
        self.xkey = str(self.comboX.currentText())
        self.ykey = str(self.comboY.currentText())
