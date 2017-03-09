import matplotlib.pyplot as plt
import h5py
import numpy as np

file = 0


path = 'C:\\Data\\Radium_08_2016\\server_data.h5'
path_2 = 'C:\\Data\\Radium_08_2016\\converted_{}_{}.csv'

chunk = 10**3
with h5py.File(path.format(file),'r') as store:    
    for key in store.keys():
        print(key)
        for scan in store[key].keys():
            if not str(scan)=="-1":
                print(scan)
                data_set_x = store[key][scan]
                if len(data_set_x) > chunk:
                    stops = np.linspace(0,len(data_set_x),
                                           len(data_set_x)/(chunk),dtype=int)
                    start=0
                    new_path = path_2.format(scan,key)
                    with open(new_path,'wb') as file:
                        for i,stop in enumerate(stops[1:]):
                            X = data_set_x[start:stop]
                            np.savetxt(file,X,delimiter = ';')
                            start=stop
                else:
                    new_path = path_2.format(scan,key)
                    with open(new_path,'wb') as file:
                        X = data_set_x[:]
                        np.savetxt(file,X,delimiter = ';')
