import http.server
import socketserver
import os
import sys
from Helpers import *
from connectors import Connector, Acceptor
import logbook as lb
from dispatcher import Dispatcher
import multiprocessing as mp

FILE_SERVER_PORT = 5009
HTTP_SERVER_PORT = 5010
DATA_PATH = 'C:/Data/'

class FileServer(Dispatcher):
    def __init__(self, PORT=5007, name='FileServer'):
        super(FileServer, self).__init__(PORT, name)
        self.http_process = mp.Process(target=run).start()
        
    @try_call
    def request_data(self,params):
        file_name = params['file_name']
        x,y = params['x'],params['y']

    @try_call
    def file_status(self,params):
        file_names = [f for f in next(os.walk(DATA_PATH))[2] if '.h5']
        return {'file_names':file_names}


# class FileHandler(asynchat.async_chat):

#     """docstring for FileHandler"""

#     def __init__(self, sock):
#         super(FileHandler, self).__init__(sock)
#         self.set_terminator('END_REQUEST'.encode('UTF-8'))
#         self.request = b""
#         self.end_data = 'END_RESPONSE'.encode('UTF-8')
#         self.mQ = mp.Queue()

#         self.feedbackTimer = th.Timer(0.5, self.send_feedback).start()

#     def found_terminator(self):
#         request = self.decode_request()
#         files = next(os.walk(os.getcwd()))[2]
#         files = [f for f in files if '.h5' in f or '.csv' in f]
#         print(request)
#         req = request[0]
#         if req == "GET_FILE_LIST":
#             files_with_size = [
#                 f + ': {} bytes'.format(os.path.getsize(f)) for f in files]
#             self.mQ.put("Found {} files:".format(str(len(files_with_size))))
#             self.mQ.put(files_with_size)
#         elif "SEND" in req:
#             if req == "SEND_ALL_H5_FILES_CONVERTED":
#                 fileNames = [f for f in files if 'stream.h5' in f]
#                 req = "SEND_FILE_H5_AS_CSV_PLUS_SCANS"
#             else:
#                 fileNames = [request[1]]
#             for f in fileNames:
#                 if f not in files:
#                     self.mQ.put("File not found")
#                 else:
#                     if req == "SEND_FILE":
#                         self.mQ.put(["File found", [f]])
# ##                    elif "SEND_FILE_H5_AS_CSV" in req:
# ##                        if req == "SEND_FILE_H5_AS_CSV_PLUS_SCANS":
# ##                            newF = convert(f, self.mQ, full=True, groups=True)
# ##                        elif req == "SEND_FILE_H5_AS_CSV_ONLY_SCANS":
# ##                            newF = convert(f, self.mQ, full=False, groups=True)
# ##                        else:
# ##                            newF = convert(f, self.mQ, full=True, groups=False)
# ##                        self.mQ.put(["File converted", newF])
#         self.mQ.put('DONE')

#     def send_feedback(self):
#         feedback = self.mQ.get()
#         self.push(pickle.dumps(feedback))
#         self.push(self.end_data)

#         self.feedbackTimer = th.Timer(0.5, self.send_feedback).start()

#     def decode_request(self):
#         req = pickle.loads(self.request)
#         self.request = b""
#         return req

#     def collect_incoming_data(self, request):
#         self.request += request

def run():
    server_address = ('', HTTP_SERVER_PORT)
    httpd = socketserver.TCPServer(server_address,
                                   http.server.SimpleHTTPRequestHandler)
    httpd.serve_forever()


def makeFileServer(PORT=5006):
    return FileServer(PORT=PORT)

def main():
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
    main()
