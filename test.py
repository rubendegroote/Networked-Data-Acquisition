import h5py
import numpy as np
import pylab as pl
store = h5py.File("C:\\Data\\artist_data.h5",'r')

for k in store.keys():
    print(k)
    print(store[k])
    pl.plot(store[k].value.T[0],'ko')
    pl.show()

store.close()