import asynchat
import asyncore
from backend.connectors import Connector
import pandas as pd
import pickle

class RadioConnector(Connector):
    def __init__(self,chan,callback,onCloseCallback):
        super(RadioConnector, self).__init__(chan,callback,t='R_to_DS')

        self.format = tuple()
        self.xy = ['time','Rubeny']
        self.perScan = True
        self.data = pd.DataFrame()
        
        self.send_next()

    def found_terminator(self):
        data = pickle.loads(self.buff)
        self.buff = b''
        
        self.format = data['format']
        if not len(data) == 0:
            self.data = data['data']

        self.send_next()

    def send_next(self):
        cols = [xy for xy in self.xy if not xy=='time']
        self.push(pickle.dumps(['data',(self.perScan,cols)]))
        self.push('END_MESSAGE'.encode('UTF-8'))