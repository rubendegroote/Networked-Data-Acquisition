from PyQt5 import QtCore, QtGui, QtWidgets
from multiprocessing import freeze_support, Process
import sys
from subprocess import Popen
import ctypes
import xmlrpc.client
import os
import configparser
import time
from config.absolute_paths import CONFIG_PATH, BATCH_PATH

class CRISTAL(QtWidgets.QMainWindow):
    def __init__(self):
        super(CRISTAL, self).__init__()

        self.get_configs()

        time.sleep(5)
        self.get_configs()

        self.setMinimumWidth(250)

        os.chdir(u"C:\\Networked-data-acquisition")
        
        # fix the icon in taskbar
        myappid = u'CRISTAL' # arbitrary string
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        self.setWindowTitle('CRISTAL')

        # enable custom window hint
        self.setWindowFlags(self.windowFlags() | QtCore.Qt.CustomizeWindowHint)
        # disable (but not hide) close button
        self.setWindowFlags(self.windowFlags() & ~QtCore.Qt.WindowMaximizeButtonHint)

        self.init_UI()

    def init_UI(self):

        wid = QtWidgets.QWidget()
        self.setCentralWidget(wid)
        layout = QtWidgets.QGridLayout(wid)
        
        rec_path = 'C:\\Networked-data-acquisition\\resources\\'

        label = QtWidgets.QLabel()
        label.setMaximumHeight(75)
        label.setMaximumWidth(250)
        pixmap = QtGui.QPixmap(rec_path + 'cris-logo.png')
        pixmap = pixmap.scaled(label.size(), QtCore.Qt.KeepAspectRatio)
        label.setPixmap(pixmap)
        layout.addWidget(label,0,0)

        self.run_update_button = QtWidgets.QPushButton('Update install files')
        self.run_update_button.setMinimumHeight(50)
        self.run_update_button.setStyleSheet('QPushButton {background-color: #bdbdbd; color: black; font-size: 16pt}')
        self.run_update_button.clicked.connect(self.run_update)
        layout.addWidget(self.run_update_button,1,0)

        self.mod_config_button = QtWidgets.QPushButton('Modify config file...')
        self.mod_config_button.setMinimumHeight(50)
        self.mod_config_button.setStyleSheet('QPushButton {background-color: #bdbdbd; color: black; font-size: 16pt}')
        self.mod_config_button.clicked.connect(self.modify_config)
        layout.addWidget(self.mod_config_button,2,0)

        self.listen_button = QtWidgets.QPushButton('Launch listener')
        self.listen_button.setMinimumHeight(50)
        self.listen_button.setStyleSheet('QPushButton {background-color: #bdbdbd; color: black; font-size: 16pt}')
        self.listen_button.clicked.connect(self.launch_listener)
        layout.addWidget(self.listen_button,3,0)

        line = QtWidgets.QFrame();
        line.setFrameShape(QtWidgets.QFrame.HLine);
        line.setFrameShadow(QtWidgets.QFrame.Sunken);
        layout.addWidget(line,4,0)

        self.data_server_button = QtWidgets.QPushButton('Launch data server')
        self.data_server_button.setMinimumHeight(50)
        self.data_server_button.setStyleSheet('QPushButton {background-color: #bcbded; color: black; font-size: 16pt}')
        self.data_server_button.clicked.connect(self.launch_data_server)
        layout.addWidget(self.data_server_button,5,0)

        self.controller_button = QtWidgets.QPushButton('Launch control server')
        self.controller_button.setMinimumHeight(50)
        self.controller_button.setStyleSheet('QPushButton {background-color: #bcbded; color: black; font-size: 16pt}')
        self.controller_button.clicked.connect(self.launch_controller)
        layout.addWidget(self.controller_button,7,0)

        self.device_button = QtWidgets.QPushButton('Launch device...')
        self.device_button.setMinimumHeight(50)
        self.device_button.setStyleSheet('QPushButton {background-color: #bcbded; color: black; font-size: 16pt}')
        self.device_button.clicked.connect(self.device_picker)
        layout.addWidget(self.device_button,8,0)

        line = QtWidgets.QFrame();
        line.setFrameShape(QtWidgets.QFrame.HLine);
        line.setFrameShadow(QtWidgets.QFrame.Sunken);
        layout.addWidget(line,9,0)

        self.run_controller_button = QtWidgets.QPushButton('Run scanner')
        self.run_controller_button.setMinimumHeight(50)
        self.run_controller_button.setStyleSheet('QPushButton {background-color: #adbdbd; color: black; font-size: 16pt}')
        self.run_controller_button.clicked.connect(self.run_controller)
        layout.addWidget(self.run_controller_button,10,0)

        self.run_viewer_button = QtWidgets.QPushButton('Run data viewer')
        self.run_viewer_button.setMinimumHeight(50)
        self.run_viewer_button.setStyleSheet('QPushButton {background-color: #adbdbd; color: black; font-size: 16pt}')
        self.run_viewer_button.clicked.connect(self.run_viewer)
        layout.addWidget(self.run_viewer_button,11,0)

        self.run_tuning_button = QtWidgets.QPushButton('Run beam tuning')
        self.run_tuning_button.setMinimumHeight(50)
        self.run_tuning_button.setStyleSheet('QPushButton {background-color: #adbdbd; color: black; font-size: 16pt}')
        self.run_tuning_button.clicked.connect(self.run_tuning)
        layout.addWidget(self.run_tuning_button,12,0)

        self.valve_cup_button = QtWidgets.QPushButton('Run cups and valves')
        self.valve_cup_button.setMinimumHeight(50)
        self.valve_cup_button.setStyleSheet('QPushButton {background-color: #adbdbd; color: black; font-size: 16pt}')
        self.valve_cup_button.clicked.connect(self.valves_cups)
        layout.addWidget(self.valve_cup_button,13,0)

        line = QtWidgets.QFrame();
        line.setFrameShape(QtWidgets.QFrame.HLine);
        line.setFrameShadow(QtWidgets.QFrame.Sunken);
        layout.addWidget(line,14,0)

        self.kill_all_button = QtWidgets.QPushButton('Kill local programs')
        self.kill_all_button.setMinimumHeight(50)
        self.kill_all_button.setStyleSheet('QPushButton {background-color: #edbdbd; color: black; font-size: 16pt}')
        self.kill_all_button.clicked.connect(self.kill_all)
        layout.addWidget(self.kill_all_button,15,0)

        # self.nature_button = QtWidgets.QPushButton('Print New Nature Article')
        # layout.addWidget(self.nature_button,6,0)

        self.show()

    def launch_listener(self):
        p = Popen(r"C:\\Networked-data-acquisition\\batch scripts\\listener.bat")

    def get_configs(self):
        config_parser = configparser.ConfigParser()
        config_parser.read(CONFIG_PATH)
        ports = config_parser['ports']
        IPs1 = config_parser['IPs devices']
        IPs2 = config_parser['IPs']
        IPs = {**IPs1, **IPs2}
        self.addresses = {k:(IPs[k],ports[k]) for k in ports.keys()}

    def modify_config(self):
        self.get_configs()
        with open(CONFIG_PATH, 'r') as f:
            text = f.read()

        dialog = QtWidgets.QDialog()
        text_edit = QtWidgets.QPlainTextEdit(dialog)
        text_edit.setMinimumHeight(400)
        text_edit.setPlainText(text)
        dialog.setMinimumWidth(256)
        dialog.setMinimumHeight(400)
        dialog.exec_()
        self.run_update()

        with open(CONFIG_PATH, 'w') as f:
            f.write(str(text_edit.toPlainText()))

    def device_picker(self):
        self.get_configs()
        ok, devs = DevicePicker.get_devices(self.addresses)
        if ok:
            for d in devs:
                self.launch_device(d)

    def kill_all(self):
        reply = QtWidgets.QMessageBox.question(self, 'Proceed?', 
                     "This will also close this program, so you'll have to restart it.", 
                     QtWidgets.QMessageBox.Yes, QtWidgets.QMessageBox.No)
        if not reply == QtWidgets.QMessageBox.Yes:
            return

        p = Popen(r"C:\\Networked-data-acquisition\batch scripts\kill_all.bat")

    def launch_device(self,dev):
        IP = self.addresses[dev][0]
        try:
            with xmlrpc.client.ServerProxy("http://{}:5050/".format(IP)) as proxy:
                proxy.execute_launch_device(dev)    
        except TimeoutError:
            QtWidgets.QMessageBox.warning(self,'Timeout error',
                'Check if the listener program running on the target pc.',
                QtWidgets.QMessageBox.Default)
        except Exception as e:
            QtWidgets.QMessageBox.warning(self,'Received error from target',
                str(e),QtWidgets.QMessageBox.Default)

    def launch_data_server(self):
        self.get_configs()
        IP = self.addresses['data_server'][0]
        try:
            with xmlrpc.client.ServerProxy("http://{}:5050/".format(IP)) as proxy:
                proxy.execute_launch_data_server()
        except TimeoutError:
            QtWidgets.QMessageBox.warning(self,'Timeout error',
                'Check if the listener program running on the target pc.',
                QtWidgets.QMessageBox.Default)
        except Exception as e:
            QtWidgets.QMessageBox.warning(self,'Received error from target',
                str(e),QtWidgets.QMessageBox.Default)

        IP = self.addresses['file_server'][0]
        try:
            with xmlrpc.client.ServerProxy("http://{}:5050/".format(IP)) as proxy:
                proxy.execute_launch_file_server()
        except TimeoutError:
            QtWidgets.QMessageBox.warning(self,'Timeout error',
                'Check if the listener program running on the target pc.',
                QtWidgets.QMessageBox.Default)
        except Exception as e:
            QtWidgets.QMessageBox.warning(self,'Received error from target',
                str(e),QtWidgets.QMessageBox.Default)

    def launch_controller(self):
        self.get_configs()
        IP = self.addresses['controller'][0]
        try:
            with xmlrpc.client.ServerProxy("http://{}:5050/".format(IP)) as proxy:
                proxy.execute_launch_controller()
        except TimeoutError:
            QtWidgets.QMessageBox.warning(self,'Timeout error',
                'Check if the listener program running on the target pc.',
                QtWidgets.QMessageBox.Default)
        except Exception as e:
            QtWidgets.QMessageBox.warning(self,'Received error from target',
                str(e),QtWidgets.QMessageBox.Default)

    def run_controller(self):
        p = Popen(r"C:\Networked-data-acquisition\batch scripts\run_controller.bat")

    def run_viewer(self):
        p = Popen(r"C:\Networked-data-acquisition\batch scripts\run_viewer.bat")

    def run_tuning(self):
        p = Popen(r"C:\Networked-data-acquisition\batch scripts\run_beamtuning.bat")

    def valves_cups(self):
        p = Popen(r"C:\Networked-data-acquisition\batch scripts\run_valves_cups.bat")

    def run_update(self):
        p = Popen(BATCH_PATH + r"update_files.bat")

    def handle_close(self):
        self.rpc.kill()
        super(CRISTAL, self).handle_close()


class DevicePicker(QtWidgets.QDialog):
    def __init__(self, addresses):
        super(DevicePicker, self).__init__()

        layout = QtWidgets.QVBoxLayout(self)

        self.devs = {}
        for dev in addresses.keys():
            if not dev in ['file_server','data_server','controller']:
                self.devs[dev] = QtWidgets.QCheckBox(dev)
                layout.addWidget(self.devs[dev])

        # OK and Cancel buttons
        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel,
            QtCore.Qt.Horizontal, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    # get current date and time from the dialog
    def devices(self):
        return [dev for dev,check in self.devs.items() if check.isChecked()]

    # static method to create the dialog and return (date, time, accepted)
    @staticmethod
    def get_devices(addresses):
        dialog = DevicePicker(addresses)
        result = dialog.exec_()
        devices = dialog.devices()
        return (result == QtWidgets.QDialog.Accepted, devices)

if __name__ == "__main__":
   
    # add freeze support
    freeze_support()
    app = QtWidgets.QApplication(sys.argv)
    app.setWindowIcon(QtGui.QIcon('C:\\Networked-Data-Acquisition\\resources\\crystal-512.png'))

    m = CRISTAL()
    sys.exit(app.exec_())
