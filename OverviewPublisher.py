from http.server import BaseHTTPRequestHandler,HTTPServer
import os,sys
from PyQt4 import QtCore, QtGui
import time    
import threading as th
import configparser
import numpy as np

CONFIG_PATH = os.getcwd() + "\\Config files\\config.ini"
class CRISWebHandler(BaseHTTPRequestHandler):
    config_parser = configparser.ConfigParser()
    config_parser.read(CONFIG_PATH)

    scan_parser = configparser.ConfigParser()
    # scan_path = config_parser['paths']['scan_path'] + 'scan_init.ini'
    scan_path = os.getcwd() + '\\temp\\scan_init.ini' 
    #Handler for the GET requests
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type','text/html')
        self.end_headers()

        self.scan_parser.read(self.scan_path)
        self.last_scan = int(self.scan_parser['last_scan']['last_scan'])
        self.scan_mass = dict(self.scan_parser['scan_mass'])


        for mass, scans in self.scan_mass.items():
            text_scans = ', '.join(eval(scans))
            text = "<p>{}{}</p> ".format(mass,text_scans)
            self.wfile.write(bytes(text,'utf-8'))


def main():
    server = HTTPServer(('', 50000), CRISWebHandler)
    server_thread = th.Thread(target = server.serve_forever)
    server_thread.setDaemon(True)
    server_thread.start()
    input()

if __name__ == '__main__':
    main()