import http.server
import socketserver
import os
import asynchat
import asyncore
import socket
import threading as th
import pickle
import time
import urllib.request

request_info = \
"""Type a number:
1 = Show the files in the data directory
2 = Transfer one file
3 = Convert a .h5 scan file to .csv and transfer it
4 = Convert a .h5 stream file to .csv, unpack all of the scans in the stream, and transfer them all
5 = Unpack all of the scans in a .h5 stream file, convert them, and transfer the scan files
6 = Unpack all of the scans in all of the .h5 stream files, convert them, and transfer the scan files
Number: """

FILE_SERVER_PORT = 5009
HTTP_SERVER_PORT = 5010

class FileReader(asynchat.async_chat):
    def __init__(self,IP='KSF402', PORT=5009):
        super(FileReader, self).__init__()
        self.IP,self.PORT = IP,PORT
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self.connect((IP, PORT))
        self.response = b""

        self.mode = ''
        self.ready = True

        self.set_terminator('END_RESPONSE'.encode('UTF-8'))

    def collect_incoming_data(self,data):
        self.response += data

    def found_terminator(self):
        resp = pickle.loads(self.response)
        self.response = b""
        if resp == "DONE":
            self.ready = True
        elif type(resp) == str:
            print(resp)
        elif self.mode == "1":
            for r in resp:
                print(r)
        else:
            for r in resp[1]:
                url = 'http://{}:{}/'.format(self.IP,HTTP_SERVER_PORT)+r
                print("Fetching file \"{}\"...".format(url))
                urllib.request.urlretrieve(url,"copy_of_"+r)
                print("File saved as \"copy_of_{}\".".format(r))

    def send_request(self,request):
        self.push(pickle.dumps(request))
        self.push('END_REQUEST'.encode('UTF-8'))
        self.ready = False

def start():
    while True:
        asyncore.loop(count = 1)
        time.sleep(0.1)

def main():
    reader = FileReader(IP = 'KSF402')
    t = th.Thread(target = start).start()
    while True:
        if reader.ready:
            resp = input("\nWhat is your request (type H for help)?")
            if resp == 'H':
                resp = input(request_info)
            reader.mode = resp
            if resp == "1":
                reader.send_request(["GET_FILE_LIST"])
            elif resp == "6":
                reader.send_request(["SEND_ALL_H5_FILES_CONVERTED"])
            else:
                f = input("Which file?")
                
                if '.h5' in f or '.csv' in f:
                    if resp == "2":
                        reader.send_request(
                                ["SEND_FILE",f])
                    elif resp == "3":
                        if 'scan' in f:
                            reader.send_request(
                                    ["SEND_FILE_H5_AS_CSV",f])
                        else:
                            print('File is not a scan file!')
                    elif resp == "4":
                        if 'stream' in f:
                            reader.send_request(
                                ["SEND_FILE_H5_AS_CSV_PLUS_SCANS",f])
                        else:
                            print('File is not a stream file!')
                    elif resp == "5":
                        if 'stream' in f:
                            reader.send_request(
                                ["SEND_FILE_H5_AS_CSV_ONLY_SCANS",f])
                        else:
                            print('File is not a stream file!')
                else:
                    print('File is not .csv or .h5!')
        else:
            time.sleep(0.1)

if __name__ == '__main__':
    main()