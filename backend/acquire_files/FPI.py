import socket
import time
import numpy as np
from PyDAQmx import *
from PyDAQmx.DAQmxConstants import *
from PyDAQmx.DAQmxFunctions import *

from .hardware import format,Hardware

this_format = format + ('AIChannel1','AIChannel2')
write_params = []

class FPI(Hardware):
    def __init__(self):
        super(FPI,self).__init__(name = 'FPI',
                                  format=this_format,
                                  write_params = write_params,
                                  refresh_time = 0)
        self.settings = dict(aiChannel="/Dev1/ai1,/Dev1/ai2",
                             noOfAi=2,
                             triggerChannel="/Dev1/PFI1",
                             sample_rate = 10**6,
                             samples = 600)

    def connect_to_device(self):
        self.timeout = 10.0
        maxRate = 10000.0  # Copied from old code

        # Create the task handles (just defines different task)
        self.aiTaskHandle = TaskHandle(0)

        # Creates the tasks
        DAQmxCreateTask("", byref(self.aiTaskHandle))

        DAQmxCreateAIVoltageChan(self.aiTaskHandle,
                    self.settings['aiChannel'], "",
                    DAQmx_Val_RSE, -10.0, 10.0,
                    DAQmx_Val_Volts, None)
        DAQmxCfgSampClkTiming(self.aiTaskHandle,'',self.settings['sample_rate'],
                              DAQmx_Val_Rising,DAQmx_Val_FiniteSamps,
                              self.settings['samples'])
        DAQmxCfgDigEdgeRefTrig(self.aiTaskHandle,self.settings['triggerChannel'],
                               DAQmx_Val_Rising,2)

        self.no_of_ai = self.settings['noOfAi']
        self.aiData = np.zeros((self.no_of_ai*self.settings['samples'],), dtype=np.float64)
        
    def read_from_device(self):
        # read = int32()
        # DAQmxStartTask(self.aiTaskHandle)
        # DAQmxReadAnalogF64(self.aiTaskHandle,
        #                    self.settings['samples'], self.timeout,
        #                    DAQmx_Val_GroupByChannel, self.aiData,
        #                    self.no_of_ai*self.settings['samples'],
        #                    byref(read), None)
        # DAQmxStopTask(self.aiTaskHandle)
    
        d1 = self.aiData[:self.settings['samples']]
        d2 = self.aiData[self.settings['samples']:]

        d1,d2 = np.abs(smooth(d1)),np.abs(smooth(d2))
        d1,d2 = d1/np.max(d1),d2/np.max(d2)

        peakind1 = detect_peaks(d1,mph=0.2,mpd=20)
        peakind2 = detect_peaks(d2,mph=0.2,mpd=20)

        return [peakind1,peakind2]



def detect_peaks(x, mph=None, mpd=1, threshold=0, edge='rising',
                 kpsh=False, valley=False):

    """Detect peaks in data based on their amplitude and other features.

    Parameters
    ----------
    x : 1D array_like
        data.
    mph : {None, number}, optional (default = None)
        detect peaks that are greater than minimum peak height.
    mpd : positive integer, optional (default = 1)
        detect peaks that are at least separated by minimum peak distance (in
        number of data).
    threshold : positive number, optional (default = 0)
        detect peaks (valleys) that are greater (smaller) than `threshold`
        in relation to their immediate neighbors.
    edge : {None, 'rising', 'falling', 'both'}, optional (default = 'rising')
        for a flat peak, keep only the rising edge ('rising'), only the
        falling edge ('falling'), both edges ('both'), or don't detect a
        flat peak (None).
    kpsh : bool, optional (default = False)
        keep peaks with same height even if they are closer than `mpd`.
    valley : bool, optional (default = False)
        if True (1), detect valleys (local minima) instead of peaks.

    Returns
    -------
    ind : 1D array_like
        indeces of the peaks in `x`.

    Notes
    -----
    The detection of valleys instead of peaks is performed internally by simply
    negating the data: `ind_valleys = detect_peaks(-x)`
    
    The function can handle NaN's 

    See this IPython Notebook [1]_.

    References
    ----------
    .. [1] http://nbviewer.ipython.org/github/demotu/BMC/blob/master/notebooks/DetectPeaks.ipynb
    """

    x = np.atleast_1d(x).astype('float64')
    if x.size < 3:
        return np.array([], dtype=int)
    if valley:
        x = -x
    # find indices of all peaks
    dx = x[1:] - x[:-1]
    # handle NaN's
    indnan = np.where(np.isnan(x))[0]
    if indnan.size:
        x[indnan] = np.inf
        dx[np.where(np.isnan(dx))[0]] = np.inf
    ine, ire, ife = np.array([[], [], []], dtype=int)
    if not edge:
        ine = np.where((np.hstack((dx, 0)) < 0) & (np.hstack((0, dx)) > 0))[0]
    else:
        if edge.lower() in ['rising', 'both']:
            ire = np.where((np.hstack((dx, 0)) <= 0) & (np.hstack((0, dx)) > 0))[0]
        if edge.lower() in ['falling', 'both']:
            ife = np.where((np.hstack((dx, 0)) < 0) & (np.hstack((0, dx)) >= 0))[0]
    ind = np.unique(np.hstack((ine, ire, ife)))
    # handle NaN's
    if ind.size and indnan.size:
        # NaN's and values close to NaN's cannot be peaks
        ind = ind[np.in1d(ind, np.unique(np.hstack((indnan, indnan-1, indnan+1))), invert=True)]
    # first and last values of x cannot be peaks
    if ind.size and ind[0] == 0:
        ind = ind[1:]
    if ind.size and ind[-1] == x.size-1:
        ind = ind[:-1]
    # remove peaks < minimum peak height
    if ind.size and mph is not None:
        ind = ind[x[ind] >= mph]
    # remove peaks - neighbors < threshold
    if ind.size and threshold > 0:
        dx = np.min(np.vstack([x[ind]-x[ind-1], x[ind]-x[ind+1]]), axis=0)
        ind = np.delete(ind, np.where(dx < threshold)[0])
    # detect small peaks closer than minimum peak distance
    if ind.size and mpd > 1:
        ind = ind[np.argsort(x[ind])][::-1]  # sort ind by peak height
        idel = np.zeros(ind.size, dtype=bool)
        for i in range(ind.size):
            if not idel[i]:
                # keep peaks with the same height if kpsh is True
                idel = idel | (ind >= ind[i] - mpd) & (ind <= ind[i] + mpd) \
                    & (x[ind[i]] > x[ind] if kpsh else True)
                idel[i] = 0  # Keep current peak
        # remove the small peaks and sort back the indices by their occurrence
        ind = np.sort(ind[~idel])

    return ind
