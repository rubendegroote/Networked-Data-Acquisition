import matplotlib.pyplot as plt
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

x = ('CRIS', 'counts')
y = ('wavemeter', 'wavenumber_1')
scans = [73, 74, 75]

x_data = [[], []]
y_data = [[], []]
with h5py.File('C:\\Data\\Gallium Run\\server_data.h5','r') as store:
    origin,par_name = x
    for scan_number in scans:
        data_set = store[origin][str(scan_number)]
        try:
            format = list(data_set.attrs['format'])
            format = [f.decode('utf-8') for f in format]
            col = format.index(par_name)
            x_data[0].extend(list(data_set[:,0]))
            x_data[1].extend(list(data_set[:,col]))

    origin,par_name = y
    for scan_number in scans:
        data_set = store[origin][str(scan_number)]
        try:
            format = list(data_set.attrs['format'])
            format = [f.decode('utf-8') for f in format]
            col = format.index(par_name)
            y_data[0].extend(list(data_set[:,0]))
            y_data[1].extend(list(data_set[:,col]))

data = x_data.extend(y_data)

data_x = pd.DataFrame({'time':data[0],'x':data[1]})
data_y = pd.DataFrame({'time':np.array(data[2])+10**(-6),'y':data[3]})

data = pd.concat([data_x,data_y])
data.set_index(['time'],inplace=True)

data = self.data.sort_index()
data['x'].fillna(method='ffill', inplace=True)
data.dropna(inplace=True)

x, y, errors = calcHist(x, y, binsize)

plt.plot(x, y)
plt.show()
