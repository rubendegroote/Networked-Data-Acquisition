import numpy as np
import datetime
import time
import pickle
import pandas as pd
# developing a general acquisition function, to get a feel for the data
# standard we would like

def acquire(settings,dQ,iQ,mQ,contFlag,stopFlag,IStoppedFlag,ns):
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
    """
    t0 = 0

    # Initialize whatever needs initializing using the settings
    # e.g.
    # set1 = settings['set1']
    # set_hardware_function(set1)

    # Start the acquisition loop
    # data = np.linspace(0,99,1)
    # times = np.array(1*[datetime.datetime.now()])
    # scans = np.append(np.append(np.ones(1400)*1,np.ones(1400)*2),np.ones(200)*-1.0)

    # mQ.put(['time', 'scan', 'x', 'y', 'z'])
    ns.format = ('time', 'scan', 'x', 'y', 'z')
    contFlag.wait()
    i = 0
    p = float(0.)
    got_instr = False


    while not stopFlag.is_set():
        try:
            # if the contFlag is set: wait for it to be unset
            contFlag.wait()

            # get data fom the hardware
            # data = get_hardware_function()
            now = time.time()

            # put data on the queue
            dQ.send((
                    np.array([datetime.datetime.now()]),
                    np.array([ns.scanNo]),
                    np.array([p]),
                    np.random.rand(1),
                    np.random.rand(1)
                   ))
            i += 1

            while time.time() - now < 0.5:
                time.sleep(0.001)

            # get instructions from the instructions queue
            try:
                instr = iQ.get_nowait()
                got_instr = True
            except:
                got_instr = False
                # no instructions received
                pass

            if got_instr:
                if instr[0] == 'Scan Change':
                    par = instr[1]
                    tPerStep = instr[3]
                    ## setting parameter in hardware somewhere
                    p = instr[2]

                    ns.measuring = True
                    # initial guess of when scanNo will be set to the current scan value. This
                    # is not a perfect guess because there is some time required for the
                    # change in ns.measuring to propagate to the manager and back.
                    # This initial guess will later be modified by the Artist to the actual time
                    # it received the 'Measuring' instruction.
                    ns.t0 = time.time()

            if ns.measuring and time.time() - ns.t0 >= tPerStep:
                ns.measuring = False


        except Exception as e:
            mQ.put(e)
            # hold the process...
            contFlag.wait()
            # ... and wait for a decision to be made by the ARTIST/Manager
            # (is this error a big deal? Can we recover?)
            contFlag.set()

    IStoppedFlag.set()