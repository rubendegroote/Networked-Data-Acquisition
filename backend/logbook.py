from datetime import datetime
import pickle
from collections import OrderedDict
from copy import deepcopy
import time
import os

class Properties(OrderedDict):
    def __str__(self):
        return "Properties: \n\t" + "\n\t".join([str(k) +": "+ str(v) for k,v in self.items()])

class SnapShot(object):
    def __init__(self,text='',author='',scan=None,props={}):
        super(SnapShot,self).__init__()
        self.time = datetime.now()
        self.text = text
        self.author = author
        self.scan = scan
        self.props = Properties(props.items())

    def fromDict(self,fields):
        for key, val in fields.items():
            if key == 'time' or key == 'scan':
                pass
            else:
                setattr(self, key, val)

    def __str__(self):
        return "\n".join([self.time.strftime("%Y-%m-%d %H:%M:%S"),self.author,self.text,str(self.props)]) + "\n"

class Entry(object):
    def __init__(self,**kwargs):
        super(Entry,self).__init__()
        self.snapShots = []
        self.snapShots.append(SnapShot(**kwargs))

    def edit(self,**kwargs):
        fields = deepcopy(self.snapShots[-1].__dict__)
        for key,val in kwargs.items():
            if key=='props':
                for k,v in val.items():
                    fields[key][k] = v
            else:
                fields[key] = val
        newSnap = SnapShot()
        newSnap.fromDict(fields)
        self.snapShots.append(newSnap)

    def save(self,fileName):
        with open(fileName+'.txt','w') as f:
            for snap in self.snapShots:
                f.write(str(snap))
                f.write('\n')
        with open(fileName+'_raw','wb') as f:
            pickle.dump(self,f)

    def __str__(self):
        return str(self.snapShots[-1])

class Logbook(OrderedDict):
    def __init__(self):
        super(Logbook,self).__init__()

    def save(self,fileName,nrs=None):
        if nrs == 'all':
            for i,entry in self.items():
                entry.save(fileName+'entry_'+str(i))
        elif nrs is not None:
            for nr in nrs:
                self[int(nr)].save(fileName+'entry_'+str(nr))

    def load(self,filePath,nrs=None):
        if nrs=='all':
            path = filePath
            fileNames = next(os.walk(path))[2]
            fileNames = ['\\'+f for f in fileNames if '_raw' in f]
            for fileName in fileNames:
                nr = fileName.split('entry_')[-1].split('_raw')[0]
                with open(filePath+fileName,'rb') as f:
                    print(f)
                    self[nr] = pickle.load(f)
        else:
            for nr in nrs:
                fileName = '\\entry_'+str("%06d" % nr)+'_raw'
                with open(filePath+fileName,'rb') as f:
                    self[nr] = pickle.load(f)

    def __str__(self):
        return "\n".join(["Entry {}:\n".format(i) + str(e) for i,e in self.items()])

# logbook = Logbook()
# for i in range(651):
#     entry = Entry(text = "Text for {}".format(str(i)),author = 'Me', props = {'isotope':79,'ISCOOL':0})
#     logbook["%06d" % i] = entry

# logbook["%06d" % 0].edit(text = 'We are at mass 80, durr', author = 'Ruben',props = {'isotope':80})
# for s in logbook["%06d" % 0].snapShots:
#     print(s)
# print(logbook)

# logbook.save('.\\logbook\\',nrs='all')

# logbook = Logbook()
# logbook.load('\\logbook\\',nrs='all')#[0,1,55])
# print(str(logbook))