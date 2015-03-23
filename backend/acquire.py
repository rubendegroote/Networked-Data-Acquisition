import numpy as np
import datetime
import time
import pickle
import pandas as pd
# developing a general acquisition function, to get a feel for the data
# standard we would like

def acquire(settings,dQ,iQ,rQ,mQ,contFlag,stopFlag,IStoppedFlag,ns):
    """ This is the function that will be the target function of a Process.

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
    p = 0
    got_instr = False

    while not stopFlag.is_set():
        try:
            # if the contFlag is set: wait for it to be unset
            contFlag.wait()

            # get data fom the hardware
            # data = get_hardware_function()
            now = time.time()

            # put data on the queue
            dQ.send(np.array([
                np.array([datetime.datetime.now()]),
                np.array([ns.scanNo]),
                np.array([p]), np.random.rand(1), np.random.rand(1)
            ]).T)
            i += 1

            while time.time() - now < 0.05:
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
                if instr[0] == 'Change':
                    pass
                    # Change parameter
                    # mQ.put("Changed {} to {}".format(instr[1], instr[2]))
                elif instr[0] == 'Scan':
                    if not ns.scanning:
                        # Start the scanning process
                        ns.scanning = True
                        ns.scanNo += 1
                        curPos = 0
                        scanPar, scanRange, tPerStep = instr[1:]
                        totalSteps = len(scanRange)
                        mQ.put("Started scanning {} in range {} at 1 step per {}s"
                               .format(instr[1], instr[2], instr[3]))
                        rQ.put((True,0))
                    else:
                        mQ.put('''Already scanning! Abort current scan first
                            or wait for it to finish.''')

            if ns.scanning:
                if curPos == totalSteps:
                    ns.scanning = False
                    rQ.put((False,100))
                elif curPos == 0 or time.time() - t0 >= tPerStep:
                    # Set scanPar to scanRange[curPos]
                    p = scanRange[curPos]
                    curPos += 1
                    t0 = time.time()
                    
                    progress = int(curPos / len(scanRange) * 100)
                    rQ.put((True,progress))

        except Exception as e:
            mQ.put(e)
            # hold the process...
            contFlag.wait()
            # ... and wait for a decision to be made by the ARTIST/Manager
            # (is this error a big deal? Can we recover?)
            contFlag.set()

    IStoppedFlag.set()
