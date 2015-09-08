import h5py
import numpy as np
import pylab as pl
store = h5py.File("C:\\Data\\server_data.h5",'r')
store2 = h5py.File("C:\\Data\\m2_data.h5",'r')
store3 = h5py.File("C:\\Data\\laser_data.h5",'r')

for k in store2.keys():
    print(store[k][-1,0])
    print(store2[k][-1,0])
    # pl.plot(store[k].value.T[0],'ko')
    # pl.plot(store2[k].value.T[0],'bo')
    pl.show()

for k in store3.keys():
    print(store[k][-1,0])
    print(store3[k][-1,0])
    # pl.plot(store[k].value.T[0],'ko')
    # pl.plot(store2[k].value.T[0],'bo')
    pl.show()

store.close()
store2.close()