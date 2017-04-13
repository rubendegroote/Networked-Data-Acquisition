import h5py
import numpy as np
import os,sys,time
from backend.helpers import emptyPipe,group_per_scan

MAXLEN = 5*10**4

current_scan = -1

def flatten(array):
    return [l for sub in array for l in sub]

def update_scan_info(saveDir,scan):
    try:
        with open(saveDir+'scanning.txt','r') as file:
            line = file.readline()
            scanning = int(line) == 1
    except:
        scanning = False

    if scan == -1:
        if scanning:
            with open(saveDir+'scanning.txt','w') as file:
                file.write('0')
    else:
        if not scanning:
            with open(saveDir+'scanning.txt','w') as file:
                file.write('1 \n')
                file.write(str(scan))

def save(to_save,frmt,saveDir,name,save_stream=True):
    global current_scan # don't like globals, but this works

    # saves data, per group (for each Device) and per scan
    to_save_grouped = group_per_scan(to_save,
                    axis=frmt.index('scan_number'))
    frmt = list(frmt)
    mass_index = frmt.index('mass')
    scan_index = frmt.index('scan_number')
    
    for scan, data in to_save_grouped.items():
        scanno = int(scan)
        if not scanno == current_scan:
            update_scan_info(saveDir,scanno)
            current_scan = scanno
        mass = int(data[:,mass_index][0])
        data = np.delete(data,mass_index,1) # no need to save scan
        data = np.delete(data,scan_index,1) # no need to save mass

        if str(scanno) == '-1':
            if not save_stream:
                continue
            else:
                direct = saveDir + 'stream\\'
        else:
            str_scan = 'scan_{0:04d}'.format(scanno)
            direct = saveDir + '{}\\{}\\'.format(mass,str_scan)

        file_path = direct + '{}.csv'.format(name)
        if not os.path.isdir(direct):
            try:
                os.makedirs(direct)
            except FileExistsError:
                # this exception gets raised if the directory has been created by another
                # device in the meantime. This happens if multiple devices run on the same pc
                # This is probably an indication that I'm making things too complicated...
                pass
        if not os.path.isfile(file_path):
            # if this is the first time we are saving data for this scan:
            # save the metadata
            with open(direct + 'metadata_{}.txt'.format(name), 'w') as meta:
                meta.write('mass {}'.format(mass) + '\n')
                meta.write('scan {}'.format(scanno) + '\n')
                frmt.remove('mass')
                frmt.remove('scan_number')
                meta.write(str(frmt) + '\n')
        
        with open(file_path, 'ab') as fname:
            np.savetxt(fname,X = data,delimiter = ';')


def save_continuously(save_output,saveDir,name,frmt,saveFlag,saveStreamFlag):
    try:
        os.stat(saveDir)
    except:
        os.mkdirs(saveDir)

    while True:
        if saveFlag.is_set():
            save_stream = saveStreamFlag.is_set()
            to_save = emptyPipe(save_output)
            if not to_save == []:
                to_save = np.row_stack(flatten(to_save))
                save(to_save,frmt,saveDir,name,save_stream)
            else:
                time.sleep(0.001)
        else:
            time.sleep(0.100)


def save_continuously_dataserver(save_output,saveDir):
    try:
        os.stat(saveDir)
    except:
        os.mkdir(saveDir)

    while True:
        to_save = emptyPipe(save_output)
        if not to_save == []:
            to_save_dict = {}
            formats = {}
            for info in to_save:
                origin,frmt,data,save_stream = info
                try:
                    to_save_dict[origin].extend(data)
                except:
                    to_save_dict[origin] = data
                formats[origin] = frmt

            for origin,to_save in to_save_dict.items():
                save(np.row_stack(to_save),
                     formats[origin],
                     saveDir,origin+'_ds',
                     save_stream)
        else:
            time.sleep(0.001)









def save_hdf(to_save,frmt,saveDir,name,save_stream=True):
    # saves data, per group (for each Device) and per scan
    to_save_grouped = group_per_scan(to_save,
                    axis=frmt.index(b'scan_number'))
    mass_index = frmt.index(b'mass')

    with h5py.File(saveDir+'_data.h5','a') as store:
        if name in store.keys():
            group = store[name]
        else:
            group = store.create_group(name)

        for scan, data in to_save_grouped.items():
            scan = str(int(scan))
            mass = data[:,mass_index][0]
            update_scan_info(saveDir,scan,mass)

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
                    col_name = frmt[i]

                    if col_name in subgroup.keys():
                        dataset = subgroup[col_name]
                    else:
                        dataset = subgroup.create_dataset(col_name,
                                data=column,
                                shape=(len(column),),
                                maxshape=(None,),chunks=True)
                        
                    newlen = len(dataset) + len(column)
                    dataset.resize((newlen,))
                    dataset[-len(column):] = column

                if newlen > MAXLEN:
                    subgroup = group.create_group(scan+'_{}'.format(highest_index+1))
