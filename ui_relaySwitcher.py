# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'relaySwitcher.ui'
#
# Created: Sat Jul  2 12:12:08 2016
#      by: PyQt4 UI code generator 4.11.3
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

import sys
import serial
import threading
portName="COM10"

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    def _fromUtf8(s):
        return s

try:
    _encoding = QtWidgets.QApplication.UnicodeUTF8
    def _translate(context, text, disambig):
        return QtWidgets.QApplication.translate(context, text, disambig, _encoding)
except AttributeError:
    def _translate(context, text, disambig):
        return QtWidgets.QApplication.translate(context, text, disambig)

class Ui_RelaySwitcher(object):

    def __init__(self):
        self.sc=open(u'\\\\cern.ch\\dfs\\Users\\c\\CRIS\\Documents\\Networked-Data-Acquisition\\Config files\\24V_config.ini','r')
        self.config={}
        self.labels={}
        self.checkRelays={}
        self.relay_mem={} #array to remember status of viewed relays
        

    def setupUi(self, RelaySwitcher):
        RelaySwitcher.setObjectName(_fromUtf8("RelaySwitcher"))
        RelaySwitcher.resize(142, 158)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(RelaySwitcher.sizePolicy().hasHeightForWidth())
        RelaySwitcher.setSizePolicy(sizePolicy)
        self.gridLayout_2 = QtWidgets.QGridLayout(RelaySwitcher)
        self.gridLayout_2.setObjectName(_fromUtf8("gridLayout_2"))
        self.gridLayout = QtWidgets.QGridLayout()
        self.gridLayout.setSizeConstraint(QtWidgets.QLayout.SetFixedSize)
        self.gridLayout.setObjectName(_fromUtf8("gridLayout"))

    ##create labels from config

        linenum=0
        for line in self.sc:
            self.config[linenum,0],self.config[linenum,1] = [x.strip() for x in line.split(',')]
            linenum=linenum+1

        for i in range(0,int(len(self.config)/2)):
            print(str(self.config[i,0]),i)
            self.labels[i]=QtWidgets.QLabel(RelaySwitcher)
            self.labels[i].setObjectName(_fromUtf8("rlabel"+str(i)))
            self.gridLayout.addWidget(self.labels[i], i, 0, 1, 1)

            self.checkRelays[i] = QtWidgets.QCheckBox(RelaySwitcher)
            self.checkRelays[i].setEnabled(True)
            self.checkRelays[i].setFocusPolicy(QtCore.Qt.NoFocus)
            self.checkRelays[i].setCheckable(True)
            self.checkRelays[i].setTristate(False)
            self.checkRelays[i].setObjectName(_fromUtf8("checkRelay"+str(i)))
            self.gridLayout.addWidget(self.checkRelays[i], i, 1, 1, 1)

            self.labels[i].setFrameShape(QtWidgets.QFrame.Box)
            self.labels[i].setFrameShadow(QtWidgets.QFrame.Plain)


        self.applyRelays = QtWidgets.QPushButton(RelaySwitcher)
        self.applyRelays.setObjectName(_fromUtf8("applyRelays"))
        rows=len(range(0,int(len(self.config)/2)))
        self.gridLayout.addWidget(self.applyRelays, rows, 0, 1, 2)

        self.gridLayout_2.addLayout(self.gridLayout, 0, 0, 1, 1)

        self.retranslateUi(RelaySwitcher)
        QtCore.QMetaObject.connectSlotsByName(RelaySwitcher)

        self.applyRelays.clicked.connect(self.switch_cups)
        self.view_cups()

    def mcp_popup(self):
        msg = QtWidgets.QMessageBox()
        msg.setIcon(QtWidgets.QMessageBox.Warning)
        msg.setText("Do you REALLY want to move the MCP?")
        msg.setInformativeText("Make sure that the MCP is not biased!!!")
        msg.setWindowTitle("MCP protector")
        msg.setStandardButtons(QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)

        retval = msg.exec_()

        return retval


    def retranslateUi(self, RelaySwitcher):
        RelaySwitcher.setWindowTitle(_translate("RelaySwitcher", "Form", None))

        linenum=0
        for line in self.sc:
            self.config[linenum,0],self.config[linenum,1] = [x.strip() for x in line.split(',')]
            linenum=linenum+1

        for i in range(0,int(len(self.config)/2)):
            self.labels[i].setText(_translate("RelaySwitcher", str(self.config[i,0]), None))
            self.checkRelays[i].setText(_translate("RelaySwitcher", "ON", None))


        self.applyRelays.setText(_translate("RelaySwitcher", "Apply", None))


    def switch_cups(self):

        for i in range(0, int(len(self.config)/2)):
            relay=self.config[i,1]
            cupname=self.config[i,0]

            # if "MCP" in cupname:
            # yesno=self.mcp_popup()
            if ("MCP" in cupname) and (self.relay_mem[cupname]!= int(self.checkRelays[i].isChecked())):
                yesno=self.mcp_popup()
                if yesno == 16384: #YES
                    print("yes")
                if yesno == 65536: #no
                    print("no")
                    continue
            elif self.relay_mem[cupname]==int(self.checkRelays[i].isChecked()):
                    continue
            else:
                print("MCP will not change position")

            if self.checkRelays[i].isChecked():
                self.relay_write(relay,"on")    
            else:
                self.relay_write(relay,"off")

        threading.Thread(target=self.view_cups()).start()
        # self.view_cups()
        
        # cup=int(self.chooseCup.currentIndex())
        # relay=self.config[cup,1]

        # if self.checkRelay.isChecked():
        #     self.relay_write(relay,"on")
        #     self.view_cup()
        # else:
        #     self.relay_write(relay,"off")
        #     self.view_cup()
        
    def view_cups(self):

        # serPort = serial.Serial(portName, 19200, timeout=1)
        # serPort.write("relay readall \n\r")
        # print(serPort.read(300))
        # serPort.close()
        # sys.exit()
        
        for i in range(0,int(len(self.config)/2)):

            relay=self.config[i,1]
            cupname=self.config[i,0]

            if self.relay_read(relay):
                self.checkRelays[i].setCheckState(2)
                self.labels[i].setStyleSheet("QLabel { background-color: green; }")
                self.relay_mem[cupname]=1
            else:
                self.checkRelays[i].setCheckState(0)
                self.labels[i].setStyleSheet("QLabel { background-color: red; }")
                self.relay_mem[cupname]=0


    def relay_write(self,relayNum,relayCmd):
        print("writing relay",relayNum,relayCmd)

        serPort = serial.Serial(portName, 19200, timeout=1)

        if (int(relayNum) < 10):
            relayIndex = str(relayNum)
        else:
            relayIndex =  chr(55 + int(relayNum))

        serPort.write("relay "+ str(relayCmd) +" "+ relayIndex + "\n\r")

        serPort.close()
        return True

    def relay_read(self,relayNum):
        print("reading relay",relayNum)
        # return False

        serPort = serial.Serial(portName, 19200, timeout=1)

        if (int(relayNum) < 10):
            relayIndex = str(relayNum)
        else:
            relayIndex = chr(55 + int(relayNum))

        serPort.write("relay read "+ relayIndex + "\n\r")

        response = serPort.read(25)
        serPort.close()

        if(response.find("on") > 0):
            # print ("Relay " + str(relayNum) +" is ON")
            return True

        elif(response.find("off") > 0):
            # print ("Relay " + str(relayNum) +" is OFF")
            return False
        else:
            print("failed to read relay, response:", response)
        


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    RelaySwitcher = QtWidgets.QWidget()
    ui = Ui_RelaySwitcher()
    ui.setupUi(RelaySwitcher)
    RelaySwitcher.show()
    sys.exit(app.exec_())

