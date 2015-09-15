import json
import numpy
import time

from . import M2

format_map = {}
format_map['M2'] = M2.this_format

hardware_map = {}
hardware_map['M2'] = M2.M2

### Main acquire loop
def acquire(name,data_pipe,iQ,mQ,stopFlag,IStoppedFlag,ns):
    ### what hardware?
    hardware = hardware_map[name]()

    hardware.ns = ns

    ### define format
    ns.format = hardware.format

    ### set-up connections and initialize
    return_message = hardware.setup()
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
            print(ns.on_setpoint)

        ### Scanning logic
        ## iterates through the scan array
        if ns.scanning:
            return_message = hardware.scan()
            if not return_message is None:
                mQ.put(return_message)

        ### Stabilizing on setpoint logic
        if not ns.on_setpoint or \
                hardware.needs_stabilization:
            return_message = hardware.stabilize()
            if not return_message is None:
                mQ.put(return_message)

        ### Input logic
        return_message = hardware.input()
        if return_message[0][0] == 0: # input was succesful
            data = return_message[1]
            data_pipe.send(data)
        else: #error to report
            mQ.put(return_message)

        time.sleep(0.001)

    IStoppedFlag.set()

def receive_instruction(queue):
    try:
        instr = queue.get_nowait()
    except:
        instr = None

    return instr