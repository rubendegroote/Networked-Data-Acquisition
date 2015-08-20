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
try:
    from OpenOPC.OpenOPC import *
except:
    from backend.OpenOPC.OpenOPC import *



def acquire(settings, dQ, iQ, mQ, contFlag, stopFlag, IStoppedFlag, ns):
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

    # Create the task handles (just defines different task)
    countTaskHandle = TaskHandle(0)
    aoTaskHandle = TaskHandle(0)
    aiTaskHandle = TaskHandle(0)

    # Creates the tasks
    DAQmxCreateTask("", byref(countTaskHandle))
    DAQmxCreateTask("", byref(aoTaskHandle))
    DAQmxCreateTask("", byref(aiTaskHandle))

    # Connect the tasks to PyDAQmx stuff...
    try:
        DAQmxCreateCICountEdgesChan(countTaskHandle,
                                    settings['counterChannel'], "",
                                    DAQmx_Val_Falling, 0, DAQmx_Val_CountUp)

        DAQmxCfgSampClkTiming(countTaskHandle,
                              settings['clockChannel'],
                              maxRate, DAQmx_Val_Falling,
                              DAQmx_Val_ContSamps, 1)

        DAQmxCreateAOVoltageChan(aoTaskHandle,
                                 settings['aoChannel'],
                                 "", -10,
                                 10,
                                 DAQmx_Val_Volts, None)

        DAQmxCreateAIVoltageChan(aiTaskHandle,
                                 settings['aiChannel'], "",
                                 DAQmx_Val_RSE, -10.0, 10.0,
                                 DAQmx_Val_Volts, None)
    except DAQError as err:
        mQ.put("NI Communication failed: \n" + str(err))
        return

    # Start the tasks
    DAQmxStartTask(countTaskHandle)
    DAQmxStartTask(aoTaskHandle)
    DAQmxStartTask(aiTaskHandle)

    # Initialize the counters
    lastCount = uInt32(0)
    countData = uInt32(0) # the counter

    # Check how many channels have to be created
    AIChannels = settings['noOfAi']
    # Initialize an array to store the data from all the channels
    aiData = np.zeros((AIChannels,), dtype=np.float64)

    # need to perform a count here that we then throw away
    # otherwise get mysterious low first count
    try:
        DAQmxReadCounterScalarU32(countTaskHandle,
                                  timeout,
                                  byref(countData), None)
    except DAQError as err:
        mQ.put("NI Communication failed: \n" + str(err))
        return
    mQ.put("NI Communication established.")

    # Create the format
    ns.format = ('time', 'scan', 'Counts', 'AOV')
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
                    # instr[1] holds the parameter name to change. With the current architecture,
                    # and the current acquire loop, this is not feasible. In this case,
                    # the parameter to be scanned will always be the one input parameter.
                    p = instr[2]
                    tPerStep = instr[3]
                    DAQmxWriteAnalogScalarF64(aoTaskHandle,
                                      True, timeout,
                                      p, None)
                    # I assume the next line was a dummy line to simulate the writing
                    # of the scanning voltage. I couldn't find it in the original code.
                    # Nevertheless, it has been preserved.
                    # time.sleep(0.5)

                    ns.on_setpoint = True
                    # initial guess of when scanNo will be set to the current scan value. This
                    # is not a perfect guess because there is some time required for the 
                    # change in ns.on_setpoint to propagate to the manager and back.
                    # This initial guess will later be modified by the Artist to the actual time
                    # it received the 'Measuring' instruction.
                    ns.t0 = time.time()
                elif instr[0] == 'Setpoint Change':
                    p = instr[2]
                    mQ.put('Changing voltage to {}'.format(p))
                    DAQmxWriteAnalogScalarF64(aoTaskHandle,
                                              True, timeout,
                                              p, None)
                else:
                    mQ.put('Unknown instruction {}.'.format(instr[0]))
                    
            # get data fom the hardware
            DAQmxReadCounterScalarU32(countTaskHandle,
                                      timeout,
                                      byref(countData), None)
            DAQmxReadAnalogF64(aiTaskHandle,
                               -1, timeout,
                               DAQmx_Val_GroupByChannel, aiData,
                               AIChannels,
                               byref(ctypes.c_long()), None)

            # Modify the gathered data, to see how many counts since the last readout
            # have registered.
            counts = countData.value - lastCount.value
            lastCount.value = countData.value
            now = time.time()

            # put data on the queue
            # Does each value have to be an array in and of itself?
            # For now, it is. The data from aiData is converted to
            # arrays with a single value, and added to the tuple created
            # from the other data (timestamp, scanNo, counts and scanningvoltage)
            dQ.send((
                    np.array([datetime.datetime.now()]),
                    np.array([ns.scanNo]),
                    np.array([counts]),
                    np.array([p])) +
                    tuple([np.array([val]) for val in aiData])
                    )

            if ns.on_setpoint and time.time() - ns.t0 >= tPerStep:
                ns.on_setpoint = False
                   

        except Exception as e:
            mQ.put(e)
            # hold the process...
            contFlag.wait()
            # ... and wait for a decision to be made by the ARTIST/Manager
            # (is this error a big deal? Can we recover?)
            contFlag.set()

    IStoppedFlag.set()

