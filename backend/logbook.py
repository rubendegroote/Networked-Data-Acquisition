from datetime import datetime
import pickle
from copy import deepcopy
import glob
from collections import OrderedDict
# import time
# import os


def prettyPrint(snap):
    return "\n".join([snap['Time'].strftime("%d-%m-%Y %H:%M:%S")] + [str(key) + ': ' + str(val) for key, val in snap.items() if not key == 'time']) + "\n"


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


def addEntry(logbook, **kwargs):
    snap = OrderedDict()
    snap['Time'] = datetime.now()
    snap['Author'] = ''
    snap['Text'] = ''
    for key, val in kwargs.items():
        if not key == 'Time':
            snap[key] = val
    logbook.append([snap])


def editEntry(logbook, key, **kwargs):
    entry = logbook[key]
    fields = deepcopy(entry[-1])
    for key, val in kwargs.items():
        fields[key] = val
    fields['Time'] = datetime.now()
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

# class Entry(object):

#     def __init__(self, **kwargs):
#         super(Entry, self).__init__()
#         snap = OrderedDict()
#         snap['Time'] = datetime.now()
#         snap['Author'] = ''
#         snap['Text'] = ''
#         for key, val in kwargs.items():
#             if not key == 'time':
#                 snap[key] = val
#         self.snapShots = []
#         self.snapShots.append(snap)

#     def edit(self, **kwargs):
#         fields = deepcopy(self.snapShots[-1])
#         for key, val in kwargs.items():
#             fields[key] = val
#         self.snapShots.append(fields)
#         self.snapShots[-1]['time'] = datetime.now()

#     def save(self, fileName):
#         with open(fileName + '.txt','w') as f:
#             for snap in self.snapShots:
#                 f.write(prettyPrint(snap))
#                 f.write('\n')
#         with open(fileName + '_raw', 'wb') as f:
#             pickle.dump(self, f)

#     def __str__(self):
#         return prettyPrint(self.snapShots[-1])


# class Logbook(OrderedDict):

#     def __init__(self):
#         super(Logbook, self).__init__()

#     def addEntry(self, **kwargs):
#         key = kwargs.pop('key', None)
#         entry = Entry(**kwargs)
#         if key is None:
#             keys = list(self.keys())
#             try:
#                 key = keys[-1]
#             except IndexError:
#                 key = 0
#             try:
#                 key = int(key) + 1
#             except TypeError:
#                 key = key + '1'
#         self[key] = entry

#     def editEntry(self, key, **kwargs):
#         self[key].edit(**kwargs)

#     def save(self, fileName, nrs=None):
#         if nrs == 'all':
#             for i, entry in self.items():
#                 entry.save(fileName + 'entry_' + str(i))
#         elif nrs is not None:
#             for nr in nrs:
#                 self[int(nr)].save(fileName + 'entry_' + str(nr))

#     def load(self, filePath, nrs=None):
#         if nrs == 'all':
#             path = filePath
#             fileNames = glob.glob(filePath + '*')
#             fileNames = [f for f in fileNames if '_raw' in f]
#             for fileName in fileNames:
#                 nr = fileName.split('entry_')[-1].split('_raw')[0]
#                 with open(fileName, 'rb') as f:
#                     self[nr] = pickle.load(f)
#         else:
#             for nr in nrs:
#                 fileName = filePath + 'entry_' + str(nr) + '_raw'
#                 with open(fileName,'rb') as f:
#                     self[nr] = pickle.load(f)

#     def __str__(self):
# return "\n".join(["Entry {}:\n".format(i) + str(e) for i, e in
# self.items()])

def main():
    log = []
    addEntry(log, Author='Me')
    print(str(prettyPrint(log[0][-1])))
    editEntry(log, 0, Author='Not me')
    print(str(prettyPrint(log[0][-1])))
    log = loadLogbook("C:/Data/ManagerLogbook")
    print(log)

if __name__ == '__main__':
    main()
