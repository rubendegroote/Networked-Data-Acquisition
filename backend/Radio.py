from backend.connectors import Connector
import pandas as pd
import pickle


class RadioConnector(Connector):

    def __init__(self, chan, callback, onCloseCallback):
        super(RadioConnector, self).__init__(chan, callback, t='R_to_DS')

        self.format = tuple()
        self.xy = ['time', 'Rubeny']
        self.giveScan = True
        self.currentScan = True
        self.format = ()
        self.data = pd.DataFrame()
        self.data_stream = pd.DataFrame()
        self.data_current_scan = pd.DataFrame()
        self.data_previous_scan = pd.DataFrame()

        self.send_next()

    def found_terminator(self):
        data = pickle.loads(self.buff)
        self.buff = b''

        try:
            if self.format is ():
                self.format = data['format']
            if not len(data) == 0:
                self.data = data['data']
                print(self.data.head())
        except TypeError:
            pass

        self.send_next()

    def changeMemory(self, value):
        self.push(pickle.dumps(['Set Memory Size', value]))
        self.push('END_MESSAGE'.encode('UTF-8'))

    def clearMemory(self):
        self.push(pickle.dumps(['Clear Memory']))
        self.push('END_MESSAGE'.encode('UTF-8'))

    def send_next(self):
        cols = [xy for xy in self.xy if not xy == 'time']
        try:
            latest = self.data.index.values[-1]
        except:
            latest = None
        self.push(pickle.dumps(['data', ([self.giveScan, self.currentScan], cols)]))
        self.push('END_MESSAGE'.encode('UTF-8'))
