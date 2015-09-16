import os
import sys
import multiprocessing as mp

from backend.Helpers import *
from backend.connectors import Connector, Acceptor
import backend.logbook as lb
from backend.dispatcher import Dispatcher


FILE_SERVER_PORT = 5009
HTTP_SERVER_PORT = 5010
DATA_PATH = 'C:\\Data\\Gallium Run\\'

class FileServer(Dispatcher):
    def __init__(self, PORT=5007, name='FileServer'):
        super(FileServer, self).__init__(PORT, name)
        
    @try_call
    def request_data(self,params):
        file_name = params['file_name']
        x,y = params['x'],params['y']

    @try_call
    def file_status(self,params):
        available_scans = []
        with open('C:\\Data\\Gallium Run\\server_scans.txt','r') as f:
            for line in f.readlines():
            	lines = line.strip('\n')
            	if not line == -1:
	            	available_scans.append(str(line))

        return {'available_scans':available_scans}

def makeFileServer(PORT=5006):
    return FileServer(PORT=PORT)

def start_fileserver():
    try:
        m = makeFileServer(5006)
        style = "QLabel { background-color: green }"
        e=''
    except Exception as error:
        e = str(error)
        style = "QLabel { background-color: red }"

    from PyQt4 import QtCore,QtGui
    # Small visual indicator that this is running
    app = QtGui.QApplication(sys.argv)
    w = QtGui.QWidget()

    w.setWindowTitle('FileServer')
    layout = QtGui.QGridLayout(w)
    label = QtGui.QLabel(e)
    label.setStyleSheet(style)
    layout.addWidget(label)
    w.show()
    
    sys.exit(app.exec_())


if __name__ == '__main__':
    start_fileserver()
