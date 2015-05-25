import http.server
import socketserver
import os
import asynchat
import asyncore
import socket
import threading as th
import multiprocessing as mp
import pickle
import time
from Convert import *


FILE_SERVER_PORT = 5009
HTTP_SERVER_PORT = 5010


class FileServer(asyncore.dispatcher):

    def __init__(self):
        super(FileServer, self).__init__()
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self.bind(('', FILE_SERVER_PORT))
        self.listen(5)
        print('Listening on port {}'.format(FILE_SERVER_PORT))

    def writable(self):
        return False

    def readable(self):
        return True

    def handle_accept(self):
        pair = self.accept()
        if pair is not None:
            sock, addr = pair
            handler = FileHandler(sock)
            print('Accepted {}'.format(addr))


class FileHandler(asynchat.async_chat):

    """docstring for FileHandler"""

    def __init__(self, sock):
        super(FileHandler, self).__init__(sock)
        self.set_terminator('END_REQUEST'.encode('UTF-8'))
        self.request = b""
        self.end_data = 'END_RESPONSE'.encode('UTF-8')
        self.mQ = mp.Queue()

        self.feedbackTimer = th.Timer(0.5, self.send_feedback).start()

    def found_terminator(self):
        request = self.decode_request()
        files = next(os.walk(os.getcwd()))[2]
        files = [f for f in files if '.h5' in f or '.csv' in f]
        req = request[0]
        if req == "GET_FILE_LIST":
            files_with_size = [
                f + ': {} bytes'.format(os.path.getsize(f)) for f in files]
            self.mQ.put("Found {} files:".format(str(len(files_with_size))))
            self.mQ.put(files_with_size)
        elif "SEND" in req:
            if req == "SEND_ALL_H5_FILES_CONVERTED":
                fileNames = [f for f in files if 'stream.h5' in f]
                req = "SEND_FILE_H5_AS_CSV_PLUS_SCANS"
            else:
                fileNames = [request[1]]
            for f in fileNames:
                if f not in files:
                    self.mQ.put("File not found")
                else:
                    if req == "SEND_FILE":
                        self.mQ.put(["File found", [f]])
                    elif "SEND_FILE_H5_AS_CSV" in req:
                        if req == "SEND_FILE_H5_AS_CSV_PLUS_SCANS":
                            newF = convert(f, self.mQ, full=True, groups=True)
                        elif req == "SEND_FILE_H5_AS_CSV_ONLY_SCANS":
                            newF = convert(f, self.mQ, full=False, groups=True)
                        else:
                            newF = convert(f, self.mQ, full=True, groups=False)
                        self.mQ.put(["File converted", newF])
        self.mQ.put('DONE')

    def send_feedback(self):
        feedback = self.mQ.get()
        self.push(pickle.dumps(feedback))
        self.push(self.end_data)

        self.feedbackTimer = th.Timer(0.5, self.send_feedback).start()

    def decode_request(self):
        req = pickle.loads(self.request)
        self.request = b""
        return req

    def collect_incoming_data(self, request):
        self.request += request


def start():
    while True:
        asyncore.loop(count=1)
        time.sleep(0.1)


def run():
    server_address = ('', HTTP_SERVER_PORT)
    httpd = socketserver.TCPServer(server_address,
                                   http.server.SimpleHTTPRequestHandler)
    httpd.serve_forever()


def main():
    f = FileServer()
    t = th.Thread(target=start).start()
    t = mp.Process(target=run).start()


if __name__ == '__main__':
    main()
