import asynchat
import asyncore
from connectors import Connector


class RadioConnector(Connector):
    def __init__(self,chan,callback):
        super(RadioConnector, self).__init__(chan,callback,t='RGui_to_DS')

        self.format = tuple()
        self.xy = ['time','Rubeny']
        self.perScan = True
        self.data = pd.DataFrame()
        
        self.send_next()

    def found_terminator(self):
        format,data = pickle.loads(self.buff)
        self.buff = b''
        
        self.format = format
        if not len(data) == 0:
            self.data = data

        self.send_next()

    def send_next(self):
        self.push(pickle.dumps((self.perScan,self.xy)))
        self.push('END_MESSAGE'.encode('UTF-8'))