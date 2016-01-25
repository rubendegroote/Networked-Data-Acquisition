import h5py
import numpy as np
import time

try:
    from Helpers import emptyPipe,group_per_scan
except:
    from backend.Helpers import emptyPipe,group_per_scan

def flatten(array):
    return [l for sub in array for l in sub]

def update_scan_info(file_path,scan,mass,group):
    scan = int(scan)
    mass = int(mass)
    if not scan in group.attrs['scans']:
        scans = group.attrs['scans']
        group.attrs['scans'] = np.append(scans,scan)
        with open(file_path+'_scans.txt','a') as scanfile:
            scanfile.write(str(scan)+';'+str(mass)+'\n')

def save(to_save,format,file_path,group_name):
    # saves data, per group (for each Device) and per scan
    to_save_grouped = group_per_scan(to_save,
                    axis=format.index(b'scan_number'))
    mass_index = format.index(b'mass')
    with h5py.File(file_path+'_data.h5','a') as store:
        try:
            group = store[group_name]
        except KeyError:
            group = store.create_group(group_name)
            group.attrs['scans'] = []

        for scan, data in to_save_grouped.items():
            scan = str(int(scan))
            mass = data[:,mass_index][0]
            update_scan_info(file_path,scan,mass,group)
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

def createbackup(source, backupname):
    with h5py.File(backupname, 'a') as backupstore:
        with h5py.File(source, 'r') as store:
            for group in store.keys():
                if group not in backupstore:
                    backupstore.create_group(group)
                    backupstore[group].attrs['scans'] = []
                for dataset in store[group].keys():
                    if dataset not in backupstore[group]:
                        data = store[group][dataset].value
                        backupstore[group].create_dataset(dataset,
                                                          data=data,
                                                          shape=(data.shape[0], data.shape[1]),
                                                          maxshape=(None, data.shape[1]),
                                                          chunks=True)
                        backupstore[group][scan].attrs['format'] = store[group][scan].attrs['format']
                    else:
                        data = store[group][dataset].shape
                        backup_data = backupstore[group][dataset].shape

                        if not np.array_equal(data, backup_data):
                            backupstore[group][dataset].resize(data)
                            backupstore[group][dataset][-(data[0]-backup_data[0]):] = store[group][dataset][-(data[0]-backup_data[0]):]

def save_continuously(save_output,saveDir,name,format):
    format = [f.encode('utf-8') for f in format]
    print(saveDir,name)
    file_path = saveDir + name
    group_name = name

    while True:
        to_save = emptyPipe(save_output)
        if not to_save == []:
            to_save = np.row_stack(flatten(to_save))
            save(to_save,format,file_path,group_name)
        else:
            time.sleep(0.001)

def save_continuously_dataserver(save_output,saveDir, backupFlag):
    file_path = saveDir + 'server'
    backuptime = 900
    start = time.time()
    while True:
        #if time.time() - start > backuptime:
        #    backupFlag.set()
        #    start = time.time()
        #if backupFlag.is_set():
        #    createbackup(file_path + '_data.h5', file_path + '_backup.h5')
        #    backupFlag.clear()
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
