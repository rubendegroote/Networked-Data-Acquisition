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
        self.scanProgress = 0
        self.scanning = False
        self._instructors = {}
        for address in artists:
            self.addInstructor(address)

    def addInstructor(self, address=None):
        if address is None:
            print('provide IP address and PORT')
            return
        print('Adding Instructor')
        try:
            intr = ArtistInstructor(IP=address[0], PORT=int(address[1]), manager = self)
            self._instructors[intr.artistName] = intr
            print('Connected to ' + intr.artistName)
        except Exception as e:
            print('Connection failed')

    def scan(self,scanInfo):
        name = 'Ruben'
        instruction = ("Scan",)+scanInfo
        self.send_instruction(name,instruction)

    def send_instruction(self, name, instruction):
        print(name, instruction)
        self._instructors[name].send_instruction(instruction)

class ArtistInstructor(asynchat.async_chat):

    """docstring for ArtistInstructor"""

    def __init__(self, IP='KSF402', PORT=5005, manager = None):
        super(ArtistInstructor, self).__init__()
        self.manager = manager

        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self.connect((IP, PORT))
        self.set_terminator('STOP_DATA'.encode('UTF-8'))
        time.sleep(0.1)
        self.send('Manager'.encode('UTF-8'))

        self.artistName = self.wait_for_connection()
        self.message = b""

        self.push(pickle.dumps('CONT'))
        self.push('END_MESSAGE'.encode('UTF-8'))

    def wait_for_connection(self):
        # Wait for connection to be made with timeout
        success = False
        now = time.time()
        while time.time() - now < 5:
            try:
                name = self.recv(1024).decode('UTF-8')
                success = True
                break
            except:
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
            self.manager.scanning = message[0]
            self.manager.scanProgress = message[1]

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
        """
        self.push(pickle.dumps(instruction))
        self.push('END_MESSAGE'.encode('UTF-8'))
        print('Instruction sent')
