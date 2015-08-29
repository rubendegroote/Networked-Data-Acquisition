import h5py
import numpy as np
import time

try:
    from Helpers import emptyPipe
except:
    from backend.Helpers import emptyPipe

def flatten(array):
    return [l for sub in array for l in sub]

def save(to_save,format,file_name,set_name):
    with h5py.File(file_name,'a') as store:
        try:
            newshape = (store[set_name].shape[0] + to_save.shape[0],
                                to_save.shape[1])
            store[set_name].resize(newshape)
            store[set_name][-to_save.shape[0]:] = to_save
        except KeyError:
            store.create_dataset(set_name,
                    data=to_save,
                    shape=(to_save.shape[0],to_save.shape[1]),
                    maxshape=(None,to_save.shape[1]),chunks=True)
            store[set_name].attrs['format'] = format

def save_continuously(save_output,saveDir,name,format):
    save_interval = 2

    format = [f.encode('utf-8') for f in format]
    file_name = saveDir + 'artist_data.h5'
    set_name = name

    while True:
        now = time.time()

        to_save = np.row_stack(flatten(emptyPipe(save_output)))
        save(to_save,format,file_name,set_name)

        # slightly more stable if the save runs every 0.5 seconds,
        # regardless of how long the previous saving took
        wait = abs(min(0, time.time() - now - save_interval))
        time.sleep(wait)

def save_continuously_dataserver(save_output,saveDir):
    save_interval = 2
    
    while True:
        now = time.time()
        to_save = emptyPipe(save_output)

        to_save_dict = {}
        formats = {}
        for info in to_save:
            origin,format,data = info
            format = [f.encode('utf-8') for f in format]
            try:
                to_save_dict[origin].extend(data)
            except:
                to_save_dict[origin] = data
            formats[origin] = format

        for key,val in to_save_dict.items():
            to_save_dict[key] = np.row_stack(val)

        for origin in formats.keys():
            to_save = to_save_dict[origin]
            format = formats[origin]
            file_name = saveDir + 'server_data.h5'
            set_name = origin
            print(to_save,format,file_name,set_name)
            save(to_save,format,file_name,set_name)

        # slightly more stable if the save runs every 0.5 seconds,
        # regardless of how long the previous saving took
        wait = abs(min(0, time.time() - now - save_interval))
        time.sleep(wait)
