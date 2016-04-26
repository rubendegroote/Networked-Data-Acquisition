import matplotlib.pyplot as plt
import h5py
import numpy as np
import pandas as pd

def calcHist(x, y, binsize):

    binsize = binsize * 1.
    x, y = np.array(x, dtype=float), np.array(y, dtype=float)

    if x[0] < x[-1]:
        bins = np.arange(min(x)-binsize/2, max(x) + binsize/2, binsize)
    else:
        start = round(min(x)/binsize) * binsize
        bins = np.arange(start-binsize/2, max(x) + binsize/2, binsize)

    bin_means, edges = np.histogram(x, bins, weights=y)

    errors = np.sqrt(bin_means + 1)

    scale = np.histogram(x, bins)[0]

    bin_means = bin_means / scale
    errors = errors / scale

    return edges, bin_means, errors

y = ('CRIS', 'Counts')
x = ('wavemeter', 'wavenumber_1')
binsize = 0.0002
time_bin = 0.1

#### 10Hz
scans = [109,110,111,121,122]

x_data = dict()
y_data = dict()

with h5py.File('C:\\Data\\Gallium Run\\File_1\\server_data.h5','r') as store:
    for scan_number in scans:
        print('Reading in scan {} as fast as I can!'.format(scan_number))
        ### x data
        print('reading x data in chunks')
        
        origin,par_name = x
        
        data_set = store[origin][str(scan_number)]

        centers_x = np.array([])
        means_x = np.array([])
        errors_x = np.array([])

        format = list(data_set.attrs['format'])
        format = [f.decode('utf-8') for f in format]
        col = format.index(par_name)
        stops = np.linspace(0,len(data_set),
                               len(data_set)/(10**4),dtype=int)
        start=0
        for stop in stops[1:]:
            print(stop)
            time = data_set[start:stop,0]
            data = data_set[start:stop,col]

            e,m,err = calcHist(time-data_set[0,0],data,time_bin)
            e = 0.5*(e[1:]+e[:-1])

            centers_x=np.append(centers_x,e)
            means_x=np.append(means_x,m)
            errors_x=np.append(errors_x,err)

            start=stop

        ### y data
        print('reading y data in chunks')
        origin,par_name = y
        data_set = store[origin][str(scan_number)]

        centers_y = np.array([])
        means_y = np.array([])
        errors_y = np.array([])

        format = list(data_set.attrs['format'])
        format = [f.decode('utf-8') for f in format]
        col = format.index(par_name)
        stops = np.linspace(0,len(data_set),
                               len(data_set)/(10**4),dtype=int)
        start=0
        for stop in stops[1:]:
            time = data_set[start:stop,0]
            data = data_set[start:stop,col]

            e,m,err = calcHist(time-data_set[0,0],data,1)
            e = 0.5*(e[1:]+e[:-1])

            centers_y=np.append(centers_y,e)
            means_y=np.append(means_y,m)
            errors_y=np.append(errors_y,err)

            start=stop

        data_x = pd.DataFrame({'time':centers_x,'x':means_x})
        data_y = pd.DataFrame({'time':centers_y,'y':means_y})
    
        data_frame = pd.concat([data_x,data_y])
        data_frame.set_index(['time'],inplace=True)
        data_frame.sort_index(inplace=True)
        data_frame['x'].fillna(method='ffill', inplace=True)
        data_frame.dropna(inplace=True)

        x_data[scan_number] = data_frame['x'].values
        y_data[scan_number] = data_frame['y'].values

final_x = np.array([])
final_y = np.array([])

for scan in scans:
    final_x = np.append(final_x,x_data[scan])
    final_y = np.append(final_y,y_data[scan])

e,m,err = calcHist(final_x,final_y,binsize)

plt.plot(0.5*e[1:]+0.5*e[:-1], m, drawstyle = 'steps')
plt.show()

