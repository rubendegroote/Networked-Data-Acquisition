import numpy as np
import ctypes
import datetime
import time
import pickle
import pandas as pd
try:
    from PyDAQmx import *
    from PyDAQmx.DAQmxConstants import *
    from PyDAQmx.DAQmxFunctions import *
except Exception as e:
    print(e)
    
FORMAT = tuple() # change this to actual format!
def acquireDiodes(settings, dQ, iQ, mQ, contFlag, stopFlag, IStoppedFlag, ns):
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

    # Start the acquisition loop
    # mQ.put(['time', 'scan', 'x', 'y', 'z'])
    timeout = 10.0
    maxRate = 10000.0  # Again, copied from old code

    # Create the task handles (just defines different task)
    aiTaskHandle = TaskHandle(0)

    # Creates the tasks
    DAQmxCreateTask("", byref(aiTaskHandle))

    # Connect the tasks to PyDAQmx stuff...
    try:
        DAQmxCreateAIVoltageChan(aiTaskHandle,
                                 settings['aiChannel'], "",
                                 DAQmx_Val_RSE, -10.0, 10.0,
                                 DAQmx_Val_Volts, None)
    except DAQError as err:
        mQ.put("NI Communication failed: \n" + str(err))
        return

    # Start the tasks
    DAQmxStartTask(aiTaskHandle)

    # Check how many channels have to be created
    AIChannels = settings['noOfAi']
    # Initialize an array to store the data from all the channels
    aiData = np.zeros((AIChannels,), dtype=np.float64)

    # need to perform a count here that we then throw away
    # otherwise get mysterious low first count
    mQ.put("NI Communication established.")

    # Create the format
    ns.format = ('time', 'scan') 
    # Add an entry for each channel
    ns.format = ns.format + tuple(['AIChannel' + str(i + 1) for i in range(AIChannels)])
    print(ns.format)

    p = float(0.)  # Initial value for the input
    got_instr = False

    contFlag.wait()  # Wait until the boolean for continuing is set to True
    while not stopFlag.is_set():  # Continue the acquisition loop while the stop flag is False
        try:
            # if the contFlag is set: wait for it to be unset
            contFlag.wait()
                    
            DAQmxReadAnalogF64(aiTaskHandle,
                               -1, timeout,
                               DAQmx_Val_GroupByChannel, aiData,
                               AIChannels,
                               byref(ctypes.c_long()), None)

            # Modify the gathered data, to see how many counts since the last readout
            # have registered.
            now = time.time()

            # put data on the queue
            # Does each value have to be an array in and of itself?
            # For now, it is. The data from aiData is converted to
            # arrays with a single value, and added to the tuple created
            # from the other data (timestamp, scanNo, counts and scanningvoltage)
            dQ.send((
                    np.array([datetime.datetime.now()]),
                    np.array([ns.scanNo])) +
                    tuple([np.array([val]) for val in aiData])
                    )

            if ns.on_setpoint and time.time() - ns.t0 >= tPerStep:
                ns.on_setpoint = False
                   

        except Exception as e:
            mQ.put(e)
            # hold the process...
            contFlag.wait()
            # ... and wait for a decision to be made by the ARTIST/Controller
            # (is this error a big deal? Can we recover?)
            contFlag.set()

        time.sleep(0.01)

    IStoppedFlag.set()

