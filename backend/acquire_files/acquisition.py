import json
import numpy
import time
import traceback
import importlib

### Main acquire loop
def acquire(name,data_pipe,iQ,mQ,stopFlag,readDataFlag,ns):
    ### what hardware?
    hrdwr = importlib.import_module('backend.acquire_files.{}'.format(name))
    hardware = hrdwr.Hardware()
    ns.write_params = hardware.write_params
    ns.refresh_time = hardware.refresh_time
    hardware.ns = ns

    # add format and write params to the namespace so
    # they can be accesses by device
    ns.format = hardware.format

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

        ### Scanning logic
        ## iterates through the scan array
        if ns.scanning:
            return_message = hardware.scan()
            if not return_message is None:
                mQ.put(return_message)

        ### Stabilizing on setpoint logic
        if hardware.needs_stabilization:
            return_message = hardware.stabilize()
            if not return_message is None:
                mQ.put(return_message)

        elif not ns.on_setpoint:
            return_message = hardware.output()
            if not return_message is None:
                mQ.put(return_message)

        ### Input logic
        if readDataFlag.is_set():
            return_message = hardware.input()
            if return_message[0][0] == 0: # input was succesful
                data = return_message[1]
                data_pipe.send(data)
            else: #error to report
                mQ.put(return_message)
        time.sleep(0.001*hardware.ns.refresh_time)

def receive_instruction(queue):
    try:
        instr = queue.get_nowait()
    except:
        instr = None

    return instr