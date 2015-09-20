import numpy as np
import ctypes
import datetime
import time
import pickle
import pandas as pd
import socket
import json

from . import SolsTiScommands as comm


FORMAT = ('timestamp','status', 'wavelength', 'temperature', 'temperature_status',
        'etalon_lock', 'etalon_voltage', 'ref_cavity_lock', 'resonator_voltage',
        'ecd_lock', 'ecd_voltage', 'output_monitor', 'etalon_pd_dc', 'dither')
def acquireM2(settings, dQ, iQ, mQ, contFlag, stopFlag, IStoppedFlag, ns):
    """ This is the function that will be the target function of a Process.

    VERY IMPORTANT: the type of the data that is put on the data queue MUST be
    consistent! E.g. do not start with sending an initial value of an integer 0,
    and then start sending floats! 

    Parameters:

    settings: a dictionary with settings that are used for the initial
        configuration
    dQ: data Queue
        This is the queue the acquire function will put the data on.
    iQ: instructions Queue
        This is the queue the function will get instructions from
    mQ: message Queue
        This is the queue the function will put the errors or warnings
        it encounters on (string format, or the error objects?).
    contFlag: an Event which indicates if the process can continue
        for some reason
    stopFlag: an Event which indicates if the process needs to exit
        for some reason (e.g. to allow for a reboot)
    IStoppedFlag: an Event WHICH RUBEN HAS TO CLARIFY
    ns: shared namespace with the Device running the acquire process
    """
    t0 = 0

    # Initialize whatever needs initializing using the settings
    # e.g.
    # set1 = settings['set1']
    # set_hardware_function(set1)

    # HOST = '192.168.1.216'
    # PORT = 39933
    # for res in socket.getaddrinfo(HOST, PORT, socket.AF_UNSPEC, socket.SOCK_STREAM):
    #     af, socktype, proto, canonname, sa = res
    #     try:
    #         s = socket.socket(af, socktype, proto)
    #     except OSError as msg:
    #         print(msg)
    #         s = None
    #         continue
    #     try:
    #         s.connect(sa)
    #     except OSError as msg:
    #         s.close()
    #         s = None
    #         print(msg)
    #         continue
    #     break
    # if not s is None:
    #     s.sendall(json.dumps(comm.start_link()))
    #     data = s.recv(1024)
    #     print(repr(data))
    # else:
    #     print('derp')

    # need to perform a count here that we then throw away
    # otherwise get mysterious low first count
    mQ.put(([0],"Communication with ICE-BLOC achieved."))

    p = float(0.)  # Initial value for the input
    got_instr = False

    contFlag.wait()  # Wait until the boolean for continuing is set to True

    while not stopFlag.is_set():  # Continue the acquisition loop while the stop flag is False
        try:
            # if the contFlag is set: wait for it to be unset
            contFlag.wait()

            ### Receiving instructions
            try:
                instr = iQ.get_nowait()
                got_instr = True
            except:
                got_instr = False
                # no instructions received
                pass
            ### Interpreting instructions
            if got_instr:
                if instr == 'scan':
                    if ns.scan_parameter == 'wavelength':
                        ns.current_position = 0
                        ns.scanning = True
                        mQ.put(([0],'Starting {} scan.'.format(ns.scan_parameter)))
                    else:
                        mQ.put(([1],'{} cannot be scanned.'.format(ns.scan_parameter)))

                elif instr == 'go_to_setpoint':
                    # s.sendall(json.dumps(comm.move_wave_t(841.0)))
                    # response = json.loads(s.recv(1024))
                    # if response['operator'] == 'move_wave_t_reply':
                    #     stat = response['parameters']['status']
                    #     if stat == 0:
                    #         mQ.put(([0],'Wavelength tuned to {} via table tuning'.format(841.0)))
                    #     elif stat == 1:
                    #         mQ.put(([1],'Command failed.'))
                    #     elif stat == 2:
                    #         mQ.put(([1],'Wavelength out of range.'))
                    # elif response['operator'] == 'parse_fail':
                    #     mQ.put(([1],'Parse fail: received message is "{}"'.format(str(response))))
                    if ns.parameter == 'wavelength':
                        # go to setpoint
                        mQ.put(([0],'Wavelength tuned to {} via table tuning'.format(ns.setpoint)))
                        ns.on_setpoint = True
                    else:
                        mQ.put(([1],'{} cannot be set.'.format(ns.parameter)))

                else:
                    try:
                        translation = mapping[instr[0]](instr[1])
                        mQ.put(([0],'Executed {} instruction.'.format(instr)))

                    except KeyError:
                        mQ.put(([1],'Unknown instruction {}.'.format(instr)))
                    
            ### Scanning logic
            if ns.scanning:
                if time.time() - ns.start_of_setpoint > ns.time_per_step:
                    ns.on_setpoint = False
                    if ns.current_position == len(ns.scan_array):
                        ns.scanning = False
                        ns.progress = 1.0
                        mQ.put(([0],'Stopped {} scan.'.format(ns.scan_parameter)))
                    else:
                        setpoint = ns.scan_array[ns.current_position]
                        # mapping["Set Wavelength"](setpoint)
                        wavelength = setpoint
                    
                        ns.progress = ns.current_position/len(ns.scan_array)
                        ns.current_position += 1
                        ns.start_of_setpoint = time.time()
                        ns.on_setpoint = True
                        mQ.put(([0],'{} scan: setpoint reached'.format(ns.scan_parameter)))
                else:
                    # carry on
                    pass

            ### Getting feedback
            # s.sendall(json.dumps(comm.get_status()))
            # response = s.recv(1024)
            # data = [response['parameters'][string] for string in data_channels]

            ### Sending data to Device
            now = time.time()
            # put data on the queue
            data = [now,1,wavelength]
            data.extend([np.random.rand()] * (len(ns.format)-3))
            dQ.send(data)


        except Exception as e:
            mQ.put(([1],str(e)))
            # hold the process...
            contFlag.wait()
            # ... and wait for a decision to be made by the ARTIST/Controller
            # (is this error a big deal? Can we recover?)
            contFlag.set()

        time.sleep(0.001)

    IStoppedFlag.set()
