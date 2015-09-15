import numpy as np
import h5py
import pylab as pl


with h5py.File('C:\\Data\\Gallium Run\\M2_data.h5','r') as store:
	for g in store.keys():
		group = store[g]
		for k in group.keys():
			data = group[k]
			print(data)
			if not k == '-1':
				x = data[:,0]
				y = data[:,4]

				pl.plot(x,y,'o',label = k)
	pl.legend()
	pl.show()