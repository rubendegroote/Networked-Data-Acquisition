# import satlas as sat
import numpy as np
import matplotlib.pyplot as plt
import h5py
import pandas as pd
import os

chunksize = 10**4
fname = 'C:\\Users\\MyStuff\\Dropbox\\PhD\\Data\\Copper2016\\server_data.h5'       
save_path = 'C:\\Users\\MyStuff\\Dropbox\\PhD\\Data Analysis\\Copper2016\\csv_data\\'
with h5py.File(fname, 'r') as server_data:
    for name in server_data.keys():
        store = server_data[name]
        for scan in sorted(store.keys()):
            if not str(scan) == "-1":
                print(scan)
                dataset = store[scan]
                format = list(dataset.attrs['format'])
                format = [str(f)[1:].strip('\'') for f in format]

                ranges = np.arange(0, (np.ceil(dataset.shape[0]/chunksize)+1)*chunksize, chunksize)
                left = ranges[:-1]            
                right = ranges[1:]-1
                for l, r in zip(left, right):
                    l, r = int(l), int(r)
                    data = dataset[l:r]
                    data_frame = pd.DataFrame(data, columns=format)
                    fname = save_path + name + '_' + str(scan) + '.csv'
                    if os.path.isfile(fname):
                        new = False
                    else:
                        new = False
                    with open(fname, 'a') as f:
                        if new:
                            data_frame.to_csv(f,sep=';',header=True)
                        else:
                            data_frame.to_csv(f,sep=';',header=True)