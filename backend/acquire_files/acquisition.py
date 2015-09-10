import json
import numpy

from . import M2 as M2

hardware_map = {}
hardware_map['M2'] = M2

### Main acquire loop
def acquire(settings,name,dQ,iQ,mQ,contFlag,stopFlag,IStoppedFlag,ns):
    ### what hardware?
    hardware = hardware_map[name]

    ### define format
    ns.format = hardware.format

    ### set-up connections and initialize
    return_message = hardware.format(settings)
    mQ.put(return_message)

    contFlag.wait()  # Wait until the boolean for continuing is set to True

    ### start acquisition loop
    while not stopFlag.is_set():  # Continue the acquisition loop while the stop flag is False
        try:
            # if the contFlag is set: wait for it to be unset
            contFlag.wait()
       
            ### Receiving instructions
            instr = receive_instruction(iQ)

            if instr is not None:
                return_message = hardware.interpret(ns,instr)
                mQ.put(return_message)

            ### Output logic
            return_message = hardware.output(ns)
            mQ.put(return_message)

            ### Input logic
            return_message,data = hardware.input(ns)
            mQ.put(return_message)
            dQ.send(data)

        except Exception as e:
            mQ.put(([1],str(e)))
            # hold the process...
            contFlag.wait()
            # ... and wait for a decision to be made by the ARTIST/Manager
            contFlag.set()

def receive_instruction(queue):
    try:
        instr = iQ.get_nowait()
    except:
        instr = None
        pass

    return instr