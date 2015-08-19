import pandas as pd
import pylab as pl
import numpy as np
import os,os
import itertools
import time
import satlas.spectrum as hfs
import satlas.utilities as utils
import seaborn as sns


def calcHist(x, y, binsize=None,bins=None,rate=True):

    if bins is not None and not bins == []:
        bins = bins

    if binsize is not None:
        binsize = binsize * 1.
        x, y = np.array(x, dtype=float), np.array(y, dtype=float)

        if x[0] < x[-1]:
            bins = np.arange(min(x)-binsize/2, max(x) + binsize/2, binsize)
        else:
            start = round(min(x)/binsize) * binsize
            bins = np.arange(start-binsize/2, max(x) + binsize/2, binsize)

    bin_means, edges = np.histogram(x, bins, weights=y)

    errors = np.sqrt(bin_means + 1)

    if rate:
        scale = np.histogram(x, bins)[0]
        bin_means = bin_means / scale
        errors = errors / scale

    return edges,bin_means,errors

def plot(chunks=[],queries=[],x_name='',y_name='',bins=[],label='',rate=True,convert_to_csv=False):
    frames = []
    for frameNo,chunk in chunks.items():
        d = chunk.copy()
        for q in queries:
            d = d.query(q)

        if len(d)>0:   
            x,y,err = calcHist(x=d[x_name],y=d[y_name],
                            bins=bins,rate=rate)
            frames.append((x,y))

    y=np.nan_to_num(frames[0][1])
    for f in frames[1:]:
        y = y + np.nan_to_num(f[1])
    pl.figure(1)
    x = 0.5*(frames[0][0][1:]+frames[0][0][:-1])
    if convert_to_csv:
        np.savetxt('Converted File.csv',[x,y])
    
    x = x * 29.9 * 2 * 1000 - x[0]
    pl.plot(x,y,drawstyle='steps',label=label)
    pl.legend()

    return(x,y)
    
def load_server(artists,columns,scans):

    os.chdir('C:\Data')

    files = [f for f in os.listdir() if 'stream' in f]
    times = [os.path.getmtime(f) for f in files]
    files = [f for t,f in sorted(zip(times,files))]
    data = {}
    for f in files:
        for a,c in zip(artists,columns):
            store = pd.read_hdf(f,key = a,columns=c)

##            store = s.copy()

            store.columns = [n.replace(': ','_') for n in store.columns]
            try:
                data[a] = pd.concat([data[a],store])
            except Exception as e:
                data[a] = store

    times = [d.index.values for d in data.values()]
    time = times[np.argmax(len(times))]

    l = len(time)
    cz = 10**5
    sc = int(1.*l/cz)+1

    chunks = {}
    for i in range(sc):
        slices = []
        for a,d in data.items():
            try:
                slices.append(d[time[i*cz]:time[(i+1)*cz]])
            except:
                slices.append(d[time[i*cz]:time[-1]])
        
        chunks[i] = pd.concat(slices)
        chunks[i].sort_index(inplace=True)
        chunks[i]['laser_wavenumber'].fillna(method='bfill', inplace=True)
        chunks[i].dropna(inplace=True)

    return chunks

   
def load_server_scan(artists,columns,scan):

    os.chdir('C:\Data')

    files = [f for f in os.listdir() if ('scan' in f and '_'+str(scan)+'.h5' in f)]
    times = [os.path.getmtime(f) for f in files]
    files = [f for t,f in sorted(zip(times,files))]
    data = {}
    for f in files:
        print(f)
        for a,c in zip(artists,columns):
            s = pd.read_hdf(f,key = a,columns=c)
            store = s.copy()
            store.columns = [n.replace(': ','_') for n in store.columns]
            try:
                data[a] = pd.concat([data[a],store])
            except Exception as e:
                data[a] = store

    times = [d.index.values for d in data.values()]
    time = times[np.argmin(len(times))]

    l = len(time)
    cz = 10**5
    sc = int(1.*l/cz)+1

    chunks = {}
    for i in range(sc):
        slices = []
        for a,d in data.items():
            try:
                slices.append(d[time[i*cz]:time[(i+1)*cz]])
            except:
                slices.append(d[time[i*cz]:time[-1]])
        
        chunks[i] = pd.concat(slices)
        chunks[i].sort_index(inplace=True)
        chunks[i]['laser_wavenumber'].fillna(method='bfill', inplace=True)
        chunks[i].dropna(inplace=True)

    return chunks

def convert(chunks):
    for c in chunks.values():
        c.to_csv('Converted File.csv')

def plot_one_scan(scan,start,end,binsize,convert_to_csv,rate):
    ## Load single scans
    chunks = load_server_scan(artists = ['laser','ABU'],scan=scan,
       columns=(['scan','laser: wavenumber'],['scan','ABU: Counts']))
    
    no_of_bins = (end-start)/binsize
    bins = np.linspace(start,end,no_of_bins)
    plot(chunks=chunks,bins=bins,
        x_name='laser_wavenumber',y_name='ABU_Counts',
         rate=rate,label = 'Scan {}'.format(scan),convert_to_csv=convert_to_csv)

def plot_all_data(queries,start,end,binsize,rate,convert_to_csv=False):
    
    ## Load all files on server and do magic
    chunks = load_server(artists = ['laser','ABU'],scans=range(-1,400),
       columns=(['scan','laser: wavenumber'],['scan','ABU: Counts']))


    no_of_bins = (end-start)/binsize
    bins = np.linspace(start,end,no_of_bins)
    data = plot(chunks=chunks,queries=queries,bins=bins,
        x_name='laser_wavenumber',y_name='ABU_Counts',rate=rate,
         label = 'Summed scans',convert_to_csv=convert_to_csv)
    return data

def main():

##    plot_one_scan(1,15391.72,15391.76,0.0002,rate=True,convert_to_csv = False)
##    plot_one_scan(2,15391.72,15391.76,0.0002,rate=True,convert_to_csv = False)
##    pl.show()

    queries = ['laser_wavenumber>15391.72',
           'laser_wavenumber<15392.0',
           'scan < 15', 'scan > -1']
    data = plot_all_data(queries,15391.72,15392,0.0002,rate=True,convert_to_csv=False)
    pl.show()


    x = data[0]
    x = utils.Energy(x, unit='cm-1')('MHz')
    x -= central
    x -= 4000.0
    y = data[1]
    yerr[np.isclose(yerr, 0)] = 1.

    # Ratio taken from "Nuclear Spins and Magnetic Moments of 71;73;75Cu: Inversion of 2p3=2 and 1f5=2 Levels in 75Cu"
    Au_Al = 0.03325558147284238587137620793069

    parameters = {
        ##       Spin,      Al,              Au, Bl,    Bu,     IS
        '63Cu': (3/2,   5867.1, Au_Al *   5867.1, 0, -28.0, 0.0),
        '69Cu': (3/2,   7492.3, Au_Al *   7492.3, 0, -20.0, 1097.0),
        '71Cu': (3/2,   6001.4, Au_Al *   6001.4, 0, -25.3, 1526.0),
        '72Cu': (2,   -2663.76, Au_Al * -2663.76, 0,   8.0, 1787.0),
        '73Cu': (3/2,  -4597.8, Au_Al *  -4597.8, 0, -26.5, 1984.0),
        '74Cu': (2  ,  -2113.0, Au_Al *  -2113.0, 0,  34.0, 2260.0),
        '75Cu': (5/2,   1591.5, Au_Al *   1591.5, 0, -36.0, 2484.0),
        ## Bu from here on out is unknown, so needs to be set!
        ## Different settings for different spins, uncomment whichever you need
        '76Cu (I=3)': (3,     1591.5, Au_Al *   1591.5, 0, -36.0, 2000.0),
        '76Cu (I=4)': (4,     1591.5, Au_Al *   1591.5, 0, -36.0, 2000.0),
        '77Cu': (5/2,   2550.0, Au_Al *   2550.0, 0, -36.0, 2700.0),
        ## Different settings for different spins, uncomment whichever you need
        '78Cu (I=4)': (4,      250.0, Au_Al *    250.0, 0, -36.0, 3030.0),
        '78Cu (I=5)': (5,      250.0, Au_Al *    250.0, 0, -36.0, 3030.0),
        '78Cu (I=6)': (6,      250.0, Au_Al *    250.0, 0, -36.0, 3030.0),
    }

    J = [1/2, 3/2]
    fwhm = [20.0, 20.0]

    
main()

