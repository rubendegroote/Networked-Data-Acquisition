import numpy as np
import h5py
import pylab as pl


with h5py.File('C:\\Data\\Gallium Run\\server_data.h5','r') as store:
	for g in store.keys():
		print(g)
		group = store[g]
		for k in group.keys():
			data = group[k]
			print(data)
			if not k == '-1':
				x = data[:,0]
				y = data[:,3]

				pl.plot(x,y,'o',label = k)
	pl.legend()
	pl.show()