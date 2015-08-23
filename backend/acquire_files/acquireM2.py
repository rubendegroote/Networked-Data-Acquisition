import numpy as np
import ctypes
import datetime
import time
import pickle
import pandas as pd
import socket
import json

from . import SolsTiScommands as comm

mapping = {
    "Set Wavelength": comm.set_wave_m,
    "Poll Wavelength": comm.poll_wave_m,
    "Lock Wavelength": comm.lock_wave_m,
    "Stop Wavelength": comm.stop_wave_m,
    "Set Wavelength Tune": comm.move_wave_t,
    "Poll Wavelength Tune": comm.poll_move_wave_t,
    "Stop Wavelength Tune": comm.stop_move_wave_t,
    "Tune Etalon": comm.tune_etalon,
    "Tune Cavity": comm.tune_cavity,
    "Finetune Cavity": comm.fine_tune_cavity,
    "Tune Resonator": comm.tune_resonator,
    "Finetune Resonator": comm.fine_tune_resonator,
    "Lock Etalon": comm.etalon_lock,
    "Etalon Lock Status": comm.etalon_lock_status,
    "Lock Reference Cavity": comm.cavity_lock,
    "Reference Cavity Lock Status": comm.cavity_lock_status,
    "Lock ECD": comm.ecd_lock,
    "ECD Lock Status": comm.ecd_lock_status,
    "Monitor A": comm.monitor_a,
    "Monitor B": comm.monitor_b,
    "Select Etalon Profile": comm.select_profile,
    "Get Status": comm.get_status,
    "Get Alignment Status": comm.get_alignment_status,
    "Beam Alignment Mode": comm.beam_alignment,
    "Beam Alignment x": comm.beam_adjust_x,
    "Beam Alignment y": comm.beam_adjust_y,
    "Initialize Scan Stitch": comm.scan_stitch_initialise,
    "Scan Stitch": comm.scan_stitch_op,
    "Scan Stitch Status": comm.scan_stitch_status,
    "Scan Stitch Output": comm.scan_stitch_output,
    "Start Fast Scan": comm.fast_scan_start,
    "Poll Fast Scan": comm.fast_scan_poll,
    "Stop Fast Scan": comm.fast_scan_stop,
    "Stop Fast Scan Without Return": comm.fast_scan_stop_nr
}

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
    ns: shared namespace with the Artist running the acquire process
    """
    t0 = 0

    # Initialize whatever needs initializing using the settings
    # e.g.
    # set1 = settings['set1']
    # set_hardware_function(set1)

    # Start the acquisition loop
    # mQ.put(['time', 'scan', 'x', 'y', 'z'])
    timeout = 10.0
    maxRate = 10000.0  # Again, copied from old code

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
    mQ.put("Communication with ICE-BLOC achieved.")

    p = float(0.)  # Initial value for the input
    got_instr = False

    contFlag.wait()  # Wait until the boolean for continuing is set to True

    tPerStep = 0
    while not stopFlag.is_set():  # Continue the acquisition loop while the stop flag is False
        try:
            # if the contFlag is set: wait for it to be unset
            contFlag.wait()
            try:
                instr = iQ.get_nowait()
                got_instr = True
            except:
                got_instr = False
                # no instructions received
                pass

            if got_instr:

                translation = mapping[instr[0]](instr[1])

                if instr[0] == 'Setpoint Change':
                    p = instr[2]
                    # s.sendall(json.dumps(comm.move_wave_t(841.0)))
                    # response = json.loads(s.recv(1024))
                    # if response['operator'] == 'move_wave_t_reply':
                    #     stat = response['parameters']['status']
                    #     if stat == 0:
                    #         mQ.put('Wavelength tuned to {} via table tuning'.format(841.0))
                    #     elif stat == 1:
                    #         mQ.put('Command failed.')
                    #     elif stat == 2:
                    #         mQ.put('Wavelength out of range.')
                    # elif response['operator'] == 'parse_fail':
                    #     mQ.put('Parse fail: received message is "{}"'.format(str(response)))
                    mQ.put('Wavelength tuned to {} via table tuning'.format(841.0))


                    ns.on_setpoint = True
                    # initial guess of when scanNo will be set to the current scan value. This
                    # is not a perfect guess because there is some time required for the 
                    # change in ns.on_setpoint to propagate to the manager and back.
                    # This initial guess will later be modified by the Artist to the actual time
                    # it received the 'Measuring' instruction.
                    ns.t0 = time.time()
                else:
                    mQ.put('Unknown instruction {}.'.format(instr[0]))
                    
            # s.sendall(json.dumps(comm.get_status()))
            # response = s.recv(1024)
            # data = [response['parameters'][string] for string in data_channels]

            # Modify the gathered data, to see how many counts since the last readout
            # have registered.
            now = time.time()

            # put data on the queue
            data = [now]
            data.extend([1] * (len(ns.format)-1))
            dQ.send(data)

            if ns.on_setpoint and time.time() - ns.t0 >= tPerStep:
                ns.on_setpoint = False

        except Exception as e:
            mQ.put(e)
            # hold the process...
            contFlag.wait()
            # ... and wait for a decision to be made by the ARTIST/Manager
            # (is this error a big deal? Can we recover?)
            contFlag.set()

        time.sleep(0.01)

    IStoppedFlag.set()
