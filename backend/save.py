import h5py
import numpy as np
import time

try:
    from Helpers import emptyPipe,group_per_scan
except:
    from backend.Helpers import emptyPipe,group_per_scan

def flatten(array):
    return [l for sub in array for l in sub]

def update_scan_info(file_path,scan,group):
    scan = int(scan)
    if not scan in group.attrs['scans']:
        scans = group.attrs['scans']
        group.attrs['scans'] = np.append(scans,scan)
        with open(file_path+'_scans.txt','a') as scanfile:
            scanfile.write(str(scan)+'\n')

def save(to_save,format,file_path,group_name):
    # saves data, per group (for each Artist) and per scan
    to_save_grouped = group_per_scan(to_save,
                    axis=format.index(b'scan_number'))
    with h5py.File(file_path+'_data.h5','a') as store:
        try:
            group = store[group_name]
        except KeyError:
            group = store.create_group(group_name)
            group.attrs['scans'] = []

        for scan, data in to_save_grouped.items():
            scan = str(int(scan))
            update_scan_info(file_path,scan,group)
            try:
                newshape = (group[scan].shape[0] + data.shape[0],
                                    data.shape[1])
                group[scan].resize(newshape)
                group[scan][-data.shape[0]:] = data
            except KeyError:
                group.create_dataset(scan,
                        data=data,
                        shape=(data.shape[0],data.shape[1]),
                        maxshape=(None,data.shape[1]),chunks=True)
                group[scan].attrs['format'] = format

def save_continuously(save_output,saveDir,name,format):
    format = [f.encode('utf-8') for f in format]
    file_path = saveDir + name
    group_name = name

    while True:
        to_save = emptyPipe(save_output)
        if not to_save == []:
            to_save = np.row_stack(flatten(to_save))
            save(to_save,format,file_path,group_name)
        else:
            time.sleep(0.001)

def save_continuously_dataserver(save_output,saveDir):
    file_path = saveDir + 'server'
    
    while True:
        to_save=emptyPipe(save_output)
        if not to_save == []:
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

            for origin,to_save in to_save_dict.items():
                save(np.row_stack(to_save),
                     formats[origin],
                     file_path,origin)
        else:
            time.sleep(0.001)
            