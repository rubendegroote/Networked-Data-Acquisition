import json
import numpy
import time
import traceback

format_map = {}
write_params_map = {}
hardware_map = {}

try:
    from . import M2
    format_map['M2'] = M2.this_format
    write_params_map['M2'] = M2.write_params
    hardware_map['M2'] = M2.M2
except ImportError:
    print('Could not import M2')
    
try:
    from . import Matisse
    format_map['Matisse'] = Matisse.this_format
    write_params_map['Matisse'] = Matisse.write_params
    hardware_map['Matisse'] = Matisse.Matisse
except ImportError:
    print('Could not import Matisse')

try:
    from . import wavemeter
    format_map['wavemeter'] = wavemeter.this_format
    write_params_map['wavemeter'] = wavemeter.write_params
    hardware_map['wavemeter'] = wavemeter.Wavemeter
except ImportError:
    print('Could not import wavemeter')

try:
    from . import wavemeter_pdl
    format_map['wavemeter_pdl'] = wavemeter_pdl.this_format
    write_params_map['wavemeter_pdl'] = wavemeter_pdl.write_params
    hardware_map['wavemeter_pdl'] = wavemeter_pdl.Wavemeter_pdl
except ImportError:
    print('Could not import wavemeter_pdl')

try:
    from . import CRIS
    format_map['CRIS'] = CRIS.this_format
    write_params_map['CRIS'] = CRIS.write_params
    hardware_map['CRIS'] = CRIS.CRIS
except ImportError:
    print('Could not import CRIS')

try:
    from . import diodes
    format_map['diodes'] = diodes.this_format
    write_params_map['diodes'] = diodes.write_params
    hardware_map['diodes'] = diodes.diodes
except ImportError:
    print('Could not import diodes')

try:
    from . import Beamline
    format_map['beamline'] = Beamline.this_format
    write_params_map['beamline'] = Beamline.write_params
    hardware_map['beamline'] = Beamline.Beamline
except ImportError as e:
    print(e)
    print('Could not import beamline')

### Main acquire loop
def acquire(name,data_pipe,iQ,mQ,stopFlag,IStoppedFlag,ns):
    ### what hardware?
    hardware = hardware_map[name]()

    hardware.ns = ns
    
    ### define format
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
        return_message = hardware.input()
        if return_message[0][0] == 0: # input was succesful
            data = return_message[1]
            data_pipe.send(data)
        else: #error to report
            mQ.put(return_message)
        time.sleep(0.001*hardware.refresh_time)

    IStoppedFlag.set()

def receive_instruction(queue):
    try:
        instr = queue.get_nowait()
    except:
        instr = None

    return instr