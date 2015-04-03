from datetime import datetime
import time
from collections import OrderedDict
from copy import deepcopy

class Properties(OrderedDict):
    def __str__(self):
        return "Properties: \n\t" + "\n\t".join([str(k) +": "+ str(v) for k,v in self.items()])

class Logbook(list):
    def __init__(self):
        super(Logbook,self).__init__()   

    def __str__(self):
        return "\n".join(["Entry {}:\n".format(i) + str(e) for i,e in enumerate(self)])

class Entry(object):
    def __init__(self,**kwargs):
        super(Entry,self).__init__()
        self.snapShots = []
        self.snapShots.append(SnapShot(**kwargs))

    def edit(self,**kwargs):
        fields = deepcopy(self.snapShots[-1].__dict__)
        for key,val in kwargs.items():
            fields[key] = val
        newSnap = SnapShot()
        newSnap.fromDict(fields)
        self.snapShots.append(newSnap)

    def __str__(self):
        return str(self.snapShots[-1])

class SnapShot(object):
    def __init__(self,text = '',author = '',props = {}):
        super(SnapShot,self).__init__()
        self.time = datetime.now()
        self.text = text
        self.author = author
        self.props = Properties(props.items())

    def fromDict(self,fields):
        for key, val in fields.items():
            if key == 'time':
                pass
            elif key =='props':
                for k,v in val.items():
                    self.props[k] = v
            else:
                setattr(self, key, val)

    def __str__(self):
        return "\n".join([self.time.strftime("%Y-%m-%d %H:%M:%S"),self.author,self.text,str(self.props)]) + "\n"

logbook = Logbook()
for i in range(10):
    entry = Entry(text = "Text for {}".format(str(i)),author = 'Me', props = {'isotope':79,'ISCOOL':0})
    logbook.append(entry)

time.sleep(1.5)
logbook[0].edit(text = 'We are at mass 80, durr', author = 'Ruben',props = {'isotope':80})
for s in logbook[0].snapShots:
    print(s)

print(logbook)