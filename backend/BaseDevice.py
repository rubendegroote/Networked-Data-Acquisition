import backend.Helpers as hp
from backend.dispatcher import Dispatcher

import os,sys
import multiprocessing as mp
import threading as th
import configparser

def acquire(name,iQ,mQ,stopFlag,ns):
    hardware = __import__(name).Hardware()
    ns.format = hardware.format
    ns.write_params = hardware.write_params
    
    ### set-up connections and initialize
    return_message = hardware.setup()
    if not return_message is None:
        mQ.put(return_message)

    got_instr = False
    ### start acquisition loop
    while not stopFlag.is_set():  # Continue the acquisition loop while the stop flag is False
        ### Receiving instructions
        instr = receive_instruction(iQ)

        ### Act on the instruction
        ## This can also write to the device if needed
        if not instr is None:
            return_message = hardware.interpret(instr)
            # never returns None
            mQ.put(return_message)
        
        ### Input logic
        return_message = hardware.input()
        if return_message[0][0] == 0: # input was succesful
            data = return_message[1]
            data_pipe.send(data)
        else: #error to report
            mQ.put(return_message)
        time.sleep(0.001*hardware.ns.refresh_time)


CONFIG_PATH = os.getcwd() + "\\Config files\\config.ini"
class BaseDevice(Dispatcher):
    ### get configuration details
    config_parser = configparser.ConfigParser()
    config_parser.read(CONFIG_PATH)
    def __init__(self, name = ''):
        PORT = int(self.config_parser['ports'][name])
        super(Device, self).__init__(PORT, name)

        #### BaseDevice Acquisition loop
        self.acquire = acquire

        # instructions queue:
        # Controller -> InstructionReceiver -> acquire
        self.iQ = mp.Queue()
        # message queue
        self.mQ = mp.Queue()

        # stop flag for the acquisition
        self.stopFlag = mp.Event()
        self.stopFlag.set()

        # Shared memory values: manager
        self.mgr = mp.Manager()
        # Shared scan number
        self.ns = self.mgr.Namespace()
        self.ns.status_data = {}

        self.start_daq()

    def stop(self):
        self.stopFlag.set()
        self.communicateThread.join()
        if not self.name == 'DSS':
            self.saveProcess.terminate()
        self.DAQProcess.terminate()
        super(Device,self).stop()

    def start_daq(self):
        self.stopFlag.clear()

        args = (self.name,self.data_input,
                self.iQ, self.mQ,self.stopFlag, self.ns)
        self.DAQProcess = mp.Process(name = 'daq' + self.name,
                  target=self.acquire,
                  args=args)
        self.DAQProcess.start()

        self.communicateThread = th.Timer(0, self.communicate)
        self.communicateThread.start()

    def communicate(self):
        while not self.stopFlag.is_set():
            self.handle_messages()
            # self.read_data()

    def handle_messages(self):
        message = hp.GetFromQueue(self.mQ)
        if not message == None:
            self.notify_connectors(message)
            
    @hp.try_call
    def status(self, params):
        self.ns.mass = params['mass'][0]
        self.ns.scan_number = params['scan_number'][0]
        self.ns.proton_info = params['proton_info']

        return {'scanning': self.ns.scanning,
                'on_setpoint': self.ns.on_setpoint,
                'progress': self.ns.progress,
                'status_data':self.ns.status_data}

    @hp.try_call
    def initial_information(self,params):
        return {'type':'BaseDevice'}

    @hp.try_call
    def execute_instruction(self,params):
        instruction = params['instruction']
        self.iQ.put([instruction,params['arguments']])
        return {}
