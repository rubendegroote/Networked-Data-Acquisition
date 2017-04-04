from datetime import datetime
import pickle
from copy import deepcopy
import glob
from collections import OrderedDict
# import time
# import os

START = 'Scanning {} from {:.8f} to {:.8f} cm-1, in {:.0f} steps with {:.8f} units of {} per step.'
SET   = 'Set Device {} parameter {} to {:.8f} cm-1.'

def stringify_scan_summary(device,summary):
    txt = ''
    for point in summary:
        txt += START.format(device,point[0],point[1],point[2],point[3],point[4]) + '\n'

    return txt

def prettyPrint(snap):
    return "\n".join([str(key) + ': ' + str(val) for key, val in snap.items()]) + "\n"

def saveEntry(filename, logbook, entry):
    filename = filename + 'entry_'
    filename = filename + \
        str(entry) if entry > -1 else filename + str(entry + len(logbook))
    entry = logbook[entry]
    with open(filename + '.txt', 'w') as f:
        for snapshot in entry:
            f.write(prettyPrint(snapshot))
            f.write('\n')
    with open(filename + '_raw', 'wb') as f:
        pickle.dump(entry, f)

def addEntryFromCopy(logbook,new_info):
    try:
        newEntry = {key: '' for key in logbook[-1][-1].keys()}
        if 'Tags' in logbook[-1][-1].keys():
            newEntry['Tags'] = OrderedDict()
            for t in logbook[-1][-1]['Tags'].keys():
                newEntry['Tags'][t] = False
    except:
        newEntry = {}

    for key,val in new_info.items():
        newEntry[key] = val

    addEntry(logbook, **newEntry)

def addEntry(logbook, **kwargs):
    snap = OrderedDict()
    snap['Time'] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    snap['Author'] = ''
    snap['Text'] = ''
    snap["Mass"] = ''
    for key, val in kwargs.items():
        if not key == 'Time':
            snap[key] = val
    logbook.append([snap])

def editEntry(logbook, index, new_info):
    entry = logbook[index]
    fields = deepcopy(entry[-1])
    for key, val in new_info.items():
        if key == 'Tags':
            if not key in fields.keys():
                fields[key] = dict()
            for tag_name,tagged in val.items():
                fields[key][tag_name] = tagged

        else:   
            fields[key] = val

    fields['Time'] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    entry.append(fields)

def saveLogbook(filename, logbook):
    for i, entry in enumerate(logbook):
        saveEntry(filename, logbook, i)

def loadLogbook(filePath):
    logbook = []
    fileNames = glob.glob(filePath + '*')
    fileNames = [f for f in fileNames if '_raw' in f]
    sorting_key = lambda f: int(f.split('_raw')[0].split('_')[-1])
    for fileName in sorted(fileNames,key = sorting_key):
        with open(fileName, 'rb') as f:
            logbook.append(pickle.load(f))
    return logbook


def main():
    print(SET.format(1,2,3))

if __name__ == '__main__':
    main()
