from datetime import datetime
import pickle
from copy import deepcopy
import glob
from collections import OrderedDict
# import time
# import os

START = 'Started scanning Artist {} from {:.8f} to {:.8f} cm-1, in {:.0f} steps with {:.8f} seconds per step.'
SET   = 'Set Artist {} parameter {} to {:.8f} cm-1.'

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
    for key, val in kwargs.items():
        if not key == 'Time':
            snap[key] = val
    logbook.append([snap])

def editEntry(logbook, index, updated_entry):
    entry = logbook[index]
    fields = deepcopy(entry[-1])
    for key, val in updated_entry.items():
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
    for fileName in fileNames:
        with open(fileName, 'rb') as f:
            logbook.append(pickle.load(f))
    logbook = sorted(logbook, key=lambda entry: entry[0]['Time'])
    return logbook

def main():
    print(SET.format(1,2,3))

if __name__ == '__main__':
    main()
