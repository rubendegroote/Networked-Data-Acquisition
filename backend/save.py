import h5py
import numpy as np
import os,sys,time

try:
    from Helpers import emptyPipe,group_per_scan
except:
    from backend.Helpers import emptyPipe,group_per_scan

def flatten(array):
    return [l for sub in array for l in sub]

def update_scan_info(file_path,scan,mass):
    scan = int(scan)
    mass = int(mass)
    scans = []
    try:
        read_scans = np.loadtxt(file_path+'_scans.txt',delimiter = ';').T[0]
        try:
            scans.extend(read_scans)
        except TypeError:
            scans.extend([read_scans])
    except FileNotFoundError:
        pass

    if not scan in scans:
        with open(file_path+'_scans.txt','a') as scanfile:
            scanfile.write(str(scan)+';'+str(mass)+'\n')

def save(to_save,format,file_path,group_name,save_stream=True):
    # saves data, per group (for each Device) and per scan
    to_save_grouped = group_per_scan(to_save,
                    axis=format.index(b'scan_number'))
    mass_index = format.index(b'mass')

    with h5py.File(file_path+'_data.h5','a') as store:
        try:
            group = store[group_name]
        except KeyError:
            group = store.create_group(group_name)

        for scan, data in to_save_grouped.items():
            scan = str(int(scan))
            mass = data[:,mass_index][0]
            update_scan_info(file_path,scan,mass)

            if scan == '-1' and not save_stream:
                pass
            else:
                scans = list(group.keys())
                if scan+'_0' in scans:
                    highest_index = max([int(s.split('_')[-1]) for s in scans if scan+'_' in s])
                    subgroup = group[scan+'_{}'.format(highest_index)]
                else:
                    highest_index = 0
                    subgroup = group.create_group(scan+'_0')

                for i,column in enumerate(data.T):
                    col_name = format[i]

                    try:
                        dataset = subgroup[col_name]
                    except:
                        dataset = subgroup.create_dataset(col_name,
                                data=column,
                                shape=(len(column),1),
                                maxshape=(None,1),chunks=True)
                        
                    newlen = len(dataset) + len(column)
                    dataset.resize((newlen,1))
                    dataset[-len(column):,0] = column

                if newlen > 5*10**4:
                    subgroup = group.create_group(scan+'_{}'.format(highest_index+1))

        store.flush()
        
def save_continuously(save_output,saveDir,name,format,saveFlag,saveStreamFlag):
    format = [f.encode('utf-8') for f in format]
    try:
        os.stat(saveDir)
    except:
        os.mkdir(saveDir)
    file_path = saveDir + name

    group_name = name
    while True:
        if saveFlag.is_set():
            save_stream = saveStreamFlag.is_set()
            to_save = emptyPipe(save_output)
            if not to_save == []:
                to_save = np.row_stack(flatten(to_save))
                save(to_save,format,file_path,group_name,save_stream)
            else:
                time.sleep(0.001)

def save_continuously_dataserver(save_output,saveDir):
    try:
        os.stat(saveDir)
    except:
        os.mkdir(saveDir)

    file_path = saveDir + 'server'
    while True:
        to_save = emptyPipe(save_output)
        if not to_save == []:
            to_save_dict = {}
            formats = {}
            for info in to_save:
                origin,format,data,save_stream = info
                format = [f.encode('utf-8') for f in format]
                try:
                    to_save_dict[origin].extend(data)
                except:
                    to_save_dict[origin] = data
                formats[origin] = format

            for origin,to_save in to_save_dict.items():
                save(np.row_stack(to_save),
                     formats[origin],
                     file_path,origin,
                     save_stream)
        else:
            time.sleep(0.001)
