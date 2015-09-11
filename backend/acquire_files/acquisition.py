import json
import numpy
import time

from .M2 import M2 as M2

hardware_map = {}
hardware_map['M2'] = M2()

### Main acquire loop
def acquire(name,data_pipe,iQ,mQ,stopFlag,IStoppedFlag,ns):
    ### what hardware?
    hardware = hardware_map[name]

    hardware.ns = ns

    ### define format
    ns.format = hardware.format

    ### set-up connections and initialize
    return_message = hardware.setup()
    mQ.put(return_message)

    got_instr = False
    ### start acquisition loop
    while not stopFlag.is_set():  # Continue the acquisition loop while the stop flag is False
        try:
            ### Receiving instructions
            instr = receive_instruction(iQ)

            if instr is not None:
                return_message = hardware.interpret(instr)
                mQ.put(return_message)

            ### Output logic
            return_message = hardware.output()
            if return_message is not None:
                mQ.put(return_message)

            ### Input logic
            data = hardware.input()
            data_pipe.send(data)

        except Exception as e:
            mQ.put(([1],str(e)))

        time.sleep(0.001)

    IStoppedFlag.set()

def receive_instruction(queue):
    try:
        instr = queue.get_nowait()
    except:
        instr = None

    return instr