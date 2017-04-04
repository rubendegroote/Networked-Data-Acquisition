from PyQt5.uic import loadUiType
from PyQt5 import QtCore, QtGui, QtWidgets
import numpy as np
import threading
import sys
import time
from multiprocessing import freeze_support
from backend.connectors import Connector
import configparser
import asyncore
import threading as th
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib as mpl
import matplotlib.pyplot as plt
mpl.rcParams['toolbar'] = 'None'

CONFIG_PATH = "\\\\cern.ch\\dfs\\Users\\c\\CRIS\\Documents\\Networked-Data-Acquisition\\Config files\\config.ini"


def make_plot(radii, seg = None):
    fig = plt.figure(figsize=(7, 5))
    ax=plt.subplot(projection='polar')
    fig.canvas.set_window_title('test GUI')
    ax.grid(False)

    radius=12.5
    linewidth = 5 # convert segment spacing to pixels here
    theta = np.linspace(0, 2*np.pi, 768)

    # Create the bound for the segment 9
    for i in range(3):
        ax.plot(theta, np.repeat(radii[i], theta.shape), '-k', lw=linewidth)

    # Create the bounds for the segments 8-5
    for i in range(4):
        theta_i = i*90*np.pi/180
        ax.plot([theta_i, theta_i], [radii[0], radii[1]], '-k', lw=linewidth)

    # Create the bounds for the segments  1-4
    for i in range(4):
        theta_i = i*90*np.pi/180
        ax.plot([theta_i, theta_i], [radii[1], radius], '-k', lw=linewidth)

    if not seg is None:
        seg = int(seg)
        if seg == 0:
            theta = np.arange(0, 2, 1./180)*np.pi
            plt.fill_between(theta, 0, radii[0], alpha=0.5, color = 'g')
        elif seg == 1:
            theta = np.arange(0, 0.5, 1./180)*np.pi
            plt.fill_between(theta, radii[0], radii[1], alpha=0.5, color = 'g')
        elif seg == 2:
            theta = np.arange(1.5, 2, 1./180)*np.pi
            plt.fill_between(theta, radii[0], radii[1], alpha=0.5, color = 'g')
        elif seg == 3:
            theta = np.arange(1, 1.5, 1./180)*np.pi
            plt.fill_between(theta, radii[0], radii[1], alpha=0.5, color = 'g')
        elif seg == 4:
            theta = np.arange(0.5, 1, 1./180)*np.pi
            plt.fill_between(theta, radii[0], radii[1], alpha=0.5, color = 'g')
        elif seg == 5:
            theta = np.arange(0, 0.5, 1./180)*np.pi
            plt.fill_between(theta, radii[1], radii[2], alpha=0.5, color = 'g')
        elif seg == 6:
            theta = np.arange(1.5, 2, 1./180)*np.pi
            plt.fill_between(theta, radii[1], radii[2], alpha=0.5, color = 'g')
        elif seg == 7:
            theta = np.arange(1, 1.5, 1./180)*np.pi
            plt.fill_between(theta, radii[1], radii[2], alpha=0.5, color = 'g')
        elif seg == 8:
            theta = np.arange(0.5, 1, 1./180)*np.pi
            plt.fill_between(theta, radii[1], radii[2], alpha=0.5, color = 'g')

    ax.set_ylim([0, radius])
    ax.set_yticklabels([])
    ax.set_xticklabels([])

    return fig

class Cup_Valve_Controller(QtWidgets.QWidget):

    config_parser = configparser.ConfigParser()
    config_parser.read(CONFIG_PATH)

    lost_connection = QtCore.pyqtSignal(object)
    update_sig = QtCore.pyqtSignal(dict)
    def __init__(self):
        super(Cup_Valve_Controller,self).__init__()

        self.setWindowTitle('Cups and valves control')
        self.outStyle = "QPushButton { background-color: rgba(255, 0, 0, 50); }"
        self.inStyle = "QPushButton { background-color: rgba(0, 255, 0, 50); }"

        self.layout = QtWidgets.QGridLayout(self)


        ### Keithley switcher
        self.cupLayout = QtWidgets.QGridLayout()
        self.layout.addLayout(self.cupLayout,0,0)
        self.segCupLayout = QtWidgets.QGridLayout()
        self.layout.addLayout(self.segCupLayout,0,1,4,4)


        self.connect_buttons = {}
        self.cup_status = {}

        self.lost_connection.connect(self.update_ui_connection_lost)
        self.update_sig.connect(self.set_status)

        ### Actuator switcher
        self.actuator_layout = QtWidgets.QGridLayout()
        self.layout.addLayout(self.actuator_layout,2,0,1,1)
        self.in_buttons = {}
        self.actuator_status = {}

        self.make_seg_plot()

        ### communicate with controller server
        chan = (str(self.config_parser['IPs']['controller']),
                   int(self.config_parser['ports']['controller']))       

        self.server_connector = Connector(name = 'CC_to_C', chan=chan,
                                 callback=self.reply_cb,
                                 default_callback=self.default_cb,
                                 onCloseCallback = self.lostConn)

        self.looping = True
        t = th.Thread(target=self.startIOLoop).start()

        self.show()


    ## connector methods
    def startIOLoop(self):
        while self.looping:
            asyncore.loop(count=1)
            time.sleep(0.05)

    def stopIOLoop(self):
        self.looping = False

    def update_ui_connection_lost(self,connector):
        self.disable()

    def default_cb(self):
        return 'status',{}

    def status_reply(self,track,params):
        origin, track_id = track[-1]
        self.update_sig.emit(params['status_data'])

    def reply_cb(self,message):
        track = message['track']
        if message['reply']['parameters']['status'][0] == 0:
            function = message['reply']['op']
            args = message['reply']['parameters']
            status_updates = message['status_updates']
            params = getattr(self, function)(track,args)

        else:
            exception = message['reply']['parameters']['exception']
            print(exception)

    def lostConn(self, connector):
        self.lost_connection.emit(connector)

    def forward_instruction_reply(self,track,params):
        origin,track_id = track[-1]

    ## UI methods
    def set_status(self,params):
        if '7001_switcher' in params.keys():
            info = params['7001_switcher']
            self.set_cup_names(info)
            if not any([v for n,v in info.items() if 'FC3S:' in n]) and \
                  any([v for n,v in self.cup_status.items() if 'FC3S:' in n]):
                self.make_seg_plot()

            for n,v in info.items():
                if v:
                    self.connect_buttons[n].setStyleSheet(self.inStyle)
                    try:
                        old_status = self.cup_status[n]
                    except:
                        old_status = None
                    self.cup_status[n] = v
                    if 'FC3S:' in n and not old_status:
                        self.make_seg_plot(n)
                else:
                    self.connect_buttons[n].setStyleSheet(self.outStyle)
                    self.cup_status[n] = v

        if 'relay_switcher' in params.keys():
            info = params['relay_switcher']
            self.set_act_names(info)
            for n,v in info.items():
                if v:
                    self.in_buttons[n].setStyleSheet(self.inStyle)
                    self.actuator_status[n] = v
                else:
                    self.in_buttons[n].setStyleSheet(self.outStyle)
                    self.actuator_status[n] = v

    def set_cup_names(self,info):
        if list(self.connect_buttons.keys()) == list(info.keys()):
            return

        for i in reversed(range(self.cupLayout.count())): 
            self.cupLayout.itemAt(i).widget().setParent(None)

        self.connect_buttons = {}
        # index_seg = 0
        for i,opt in enumerate(info.keys()):

            self.connect_buttons[opt] = QtWidgets.QPushButton(opt)
            self.connect_buttons[opt].setCheckable(True)
            self.connect_buttons[opt].clicked.connect(self.change_cups)

            self.connect_buttons[opt].setChecked(info[opt])
            if info[opt]:
                self.connect_buttons[opt].setStyleSheet(self.inStyle)
            else:
                self.connect_buttons[opt].setStyleSheet(self.outStyle)

            if 'seg' in opt:
                continue ## remove later once this seg thing is implemented!!!

            if not 'S:' in opt:
                self.cupLayout.addWidget(self.connect_buttons[opt],i//4,i%4)
            # else:
            #     pos = seg_cup_pos[opt]
            #     self.segCupLayout.addWidget(self.connect_buttons[opt],pos[0],pos[1])
            #     index_seg += 1


    def set_act_names(self,info):
        if list(self.in_buttons.keys()) == list(info.keys()):
            return

        for i in reversed(range(self.actuator_layout.count())): 
            self.actuator_layout.itemAt(i).widget().setParent(None)

        self.in_buttons = {}
        for i,opt in enumerate(info.keys()):

            self.actuator_status[opt] = info[opt]

            self.in_buttons[opt] = QtWidgets.QPushButton(opt)
            self.in_buttons[opt].setCheckable(True)
            self.in_buttons[opt].clicked.connect(self.change_acts)
            self.actuator_layout.addWidget(self.in_buttons[opt],i//4,i%4)

            self.in_buttons[opt].setChecked(info[opt])
            if info[opt]:
                self.in_buttons[opt].setStyleSheet(self.inStyle)
            else:
                self.in_buttons[opt].setStyleSheet(self.outStyle)


    def mcp_popup(self):
        msg = QtWidgets.QMessageBox()
        msg.setIcon(QtWidgets.QMessageBox.Warning)
        msg.setText("Do you REALLY want to move the MCP?")
        msg.setInformativeText("Make sure that the MCP is not biased!!!")
        msg.setWindowTitle("MCP protector")
        msg.setStandardButtons(QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)

        retval = msg.exec_()

        return retval == QtWidgets.QMessageBox.Yes

    def make_seg_plot(self, info = None):
        self.radii=np.array([1.5,5.5,12.5])
        for i in reversed(range(self.segCupLayout.count())): 
            self.segCupLayout.itemAt(i).widget().setParent(None)

        if info is None:  
            fig = make_plot(self.radii, None)
        else:
            fig = make_plot(self.radii, info.split('FC3S:')[-1])
        
        self.canvas = FigureCanvas(fig)
        cid = fig.canvas.mpl_connect('button_press_event', self.seg_clicked)
        self.canvas.setMinimumWidth(250)
        self.canvas.setMaximumWidth(250)
        self.canvas.setMinimumHeight(250)
        self.canvas.setMaximumHeight(250)
        self.segCupLayout.addWidget(self.canvas,0,0)


    def seg_clicked(self,event):
        ### Behold the worst hack man has ever made:
        angle, radius = event.xdata, event.ydata
        if radius < self.radii[0]:
            button = self.connect_buttons['FC3S:{}'.format(0)]
        elif radius < self.radii[1]:
            if angle > 0 and angle <= np.pi/2:
                button = self.connect_buttons['FC3S:{}'.format(1)]
            elif np.pi/2 > 0 and angle <= np.pi:
                button = self.connect_buttons['FC3S:{}'.format(4)]
            elif np.pi > 0 and angle <= 3*np.pi/2:
                button = self.connect_buttons['FC3S:{}'.format(3)]
            else:
                button = self.connect_buttons['FC3S:{}'.format(2)]

        elif radius < self.radii[2]:
            if angle > 0 and angle <= np.pi/2:
                button = self.connect_buttons['FC3S:{}'.format(5)]
            elif np.pi/2 > 0 and angle <= np.pi:
                button = self.connect_buttons['FC3S:{}'.format(8)]
            elif np.pi > 0 and angle <= 3*np.pi/2:
                button = self.connect_buttons['FC3S:{}'.format(7)]
            else:
                button = self.connect_buttons['FC3S:{}'.format(6)]

        button.setChecked(not button.isChecked())
        button.clicked.emit()
             
    def change_cups(self):
        for n,c in self.connect_buttons.items():
            if not c == self.sender():
                c.setChecked(False)
            else:
                name = n

        self.server_connector.add_request(('forward_instruction',
                                                  {'instruction':'switch_cup',
                                                   'device':'7001_switcher',
                                                   'arguments':
                                                       {'cup_info':(name,self.sender().isChecked())}
                                                   }))

    def change_acts(self):
        info = {n:c.isChecked() for n,c in self.in_buttons.items()}
        for key in self.in_buttons.keys():
            if 'MCP' in key:
                if not info[key] == self.actuator_status[key]:
                    if not self.mcp_popup():
                        info[key] = False
                        self.in_buttons[key].setChecked(self.actuator_status[key])
                        return

        self.server_connector.add_request(('forward_instruction',
                                                  {'instruction':'switch_actuator',
                                                   'device':'relay_switcher',
                                                   'arguments':
                                                      {'actuator_info':info}
                                                  }))

    def closeEvent(self, event):
        self.stopIOLoop()
        event.accept()

def main():
    # add freeze support
    freeze_support()
    app = QtWidgets.QApplication(sys.argv)
    m = Cup_Valve_Controller()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()