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
binsize = 0.0005
minimal_value = 11991.70
maximal_value = 11991.90
bins = np.arange(minimal_value-binsize/2, maximal_value + binsize/2, binsize)
scans = [73]#, 74, 75]

with h5py.File('C:\\Data\\Gallium Run\\File_1\\server_data.h5','r') as store:
    for scan_number in scans:
        origin,par_name = x
        return_list = [[], [], [], []]
        data_set = store[origin][str(scan_number)]
        try:
            format = list(data_set.attrs['format'])
            format = [f.decode('utf-8') for f in format]
            col = format.index(par_name)
            chunks = np.linspace((0,len(data),10**4))
            print(chunks)
            input()
#            for chunk in chunks:
        
            return_list[0].extend(list(data_set[:,0]))
            return_list[1].extend(list(data_set[:,col]))
        except:
            pass

        origin,par_name = y
        data_set = store[origin][str(scan_number)]
        try:
            format = list(data_set.attrs['format'])
            format = [f.decode('utf-8') for f in format]
            col = format.index(par_name)
            return_list[2].extend(list(data_set[:,0]))
            return_list[3].extend(list(data_set[:,col]))
        except:
            pass
        data = return_list
    
        print(len(data[0]), len(data[1]), len(data[2]), len(data[3]))
        data_x = pd.DataFrame({'time':data[0],'x':data[1]})
        data_y = pd.DataFrame({'time':np.array(data[2])+10**(-6),'y':data[3]})

        data_frame = pd.concat([data_x,data_y])
        data_frame.set_index(['time'],inplace=True)
        data_frame.sort_index(inplace=True)
        data_frame['x'].fillna(method='ffill', inplace=True)
        data_frame.dropna(inplace=True)

        x_data = data_frame['x'].values
        y_data = data_frame['y'].values

        del data_frame
        del data_x
        del data_y
        del data
        del return_list
        print(x_data[0], x_data[-1])
        print(bins[0], bins[-1])
        response, _ = np.histogram(x_data, bins, weights=y_data)
        print(response)
        scale = np.histogram(x_data, bins)[0]
        try:
            bin_response += response / scale
        except:
            bin_response = response / scale
        print(sum(y_data))

plt.plot(bins[1:], bin_response, drawstyle='steps')
plt.show()
