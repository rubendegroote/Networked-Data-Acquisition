import asyncore
import asynchat
import socket
import multiprocessing as mp
import threading as th
import pickle
import numpy as np
import pandas as pd
try:
    from Helpers import *
except:
    from backend.Helpers import *

class Manager():
    def __init__(self, artists=[]):
        self.scanNo = 0
        self.progress = 0
        self.scanning = False
        self.format = {}
        self.measuring = False
        self._instructors = {}
        for address in artists:
            self.addInstructor(address)

    def addInstructor(self, address=None):
        if address is None:
            print('provide IP address and PORT')
            return
        try:
            instr = ArtistInstructor(IP=address[0], PORT=int(address[1]), manager = self)
            self._instructors[instr.artistName] = instr
            print('Connected to ' + instr.artistName)
        except Exception as e:
            print('Connection failed')
        print('done')

    def scan(self,scanInfo):
        name,self.scanPar = scanInfo[0].split(':')
        self.scanner = self._instructors[name]
        self.scanner.scanning = True
        self.curPos = 0
        self.scanRange = scanInfo[1]
        self.tPerStep = scanInfo[2]
        self.scanning = True
        self.scanNo += 1
        self.sendNext()

    def notifyAll(self,instruction):
        for instr in self._instructors.values():
            instr.send_instruction(instruction)

    def sendNext(self):
        if self.curPos == len(self.scanRange):
            self.progress = 100
            self.scanning = False
            self.scanner.scanning = False
            return

        self.scanner.send_instruction(
            ["Change",self.scanPar,self.scanRange[self.curPos],self.tPerStep])
        self.curPos +=1
        self.progress =  int(self.curPos / len(self.scanRange) * 100)

class ArtistInstructor(asynchat.async_chat):

    """docstring for ArtistInstructor"""

    def __init__(self, IP='KSF402', PORT=5005, manager = None):
        super(ArtistInstructor, self).__init__()
        self.manager = manager
        self.scanning = False

        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self.connect((IP, PORT))
        self.set_terminator('STOP_DATA'.encode('UTF-8'))

        self.send('Manager'.encode('UTF-8'))
        self.artistName = self.wait_for_connection()
        self.message = b""

        self.send_continue()

    def wait_for_connection(self):
        # Wait for connection to be made with timeout
        success = False
        now = time.time()
        while time.time() - now < 5:
            try:
                name = self.recv(1024).decode('UTF-8')
                success = True
                break
            except Exception as e:
                pass
        if not success:
            raise
        return name

    def collect_incoming_data(self, data):
        self.message += data

    def found_terminator(self):
        message = pickle.loads(self.message)
        self.message = b""
        if message is not None:
            self.manager.format[self.artistName] = message['format']
            if self.scanning and message['measuring'] != self.manager.measuring:
                self.manager.measuring = message['measuring']
                if message['measuring']:
                    self.manager.notifyAll(['Measuring', self.manager.scanNo])
                else:
                    self.manager.notifyAll(['idling'])
                    self.manager.sendNext()
            
        self.send_continue()

    def send_continue(self):
        self.push(pickle.dumps('CONT'))
        self.push('END_MESSAGE'.encode('UTF-8'))

    def send_instruction(self, instruction):
        """
        Some additional info on the instructions options and syntax

        Changing a paramter:
            instruction = ["Change", parameter name, value]
        Scanning a paramter:
            instruction = ["Scan", parameter name, range, time per step]
        Stopping the DAQ loop:
            instruction = ["STOP"]
        Starting the DAQ loop:
            instruction = ["START"]
        Restarting the DAQ loop:
            instruction = ["RESTART"]
        Pauzing the DAQ loop:
            instruction = ["PAUZE"]
        Resuming the DAQ loop:
            instruction = ["RESUME"]
        Changing hardware settings:
            instruction = ["CHANGE SETTINGS",Dict with settings]
        Notifying the artist that a scan has started (this or another artist):
            instruction = ["SCAN STARTED"]
        Notifying the artist that the scan has finished:
            instruction = ["SCAN STOPPED"]
        """
        self.push(pickle.dumps(instruction))
        self.push('END_MESSAGE'.encode('UTF-8'))
        print('Instruction sent')
