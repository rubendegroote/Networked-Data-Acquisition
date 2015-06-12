from backend.connectors import Connector
import pandas as pd
import pickle
import threading as th
import time


class RadioConnector(Connector):

    def __init__(self, chan, callback, onCloseCallback):
        super(RadioConnector, self).__init__(chan, callback, t='R_to_DS')

        self.format = tuple()
        self.xy = ['time', 'Rubeny']
        self._giveScan = False
        self._currentScan = True
        self.format = ()
        self._clear_memory = False
        self.data_lock = th.Lock()
        self.data = pd.DataFrame()
        self.data_stream = pd.DataFrame()
        self.data_current_scan = pd.DataFrame()
        self.data_previous_scan = pd.DataFrame()

        self.send_next()

    @property
    def giveScan(self):
        return self._giveScan

    @giveScan.setter
    def giveScan(self, value):
        self._giveScan = value
        if self._giveScan:
            if self._currentScan:
                self.data = self.data_current_scan
            else:
                self.data = self.data_previous_scan
        else:
            self.data = self.data_stream

    @property
    def currentScan(self):
        return self._currentScan

    @currentScan.setter
    def currentScan(self, value):
        self._currentScan = value
        if self._giveScan:
            if self._currentScan:
                self.data = self.data_current_scan
            else:
                self.data = self.data_previous_scan
        else:
            self.data = self.data_stream


    def found_terminator(self):
        data = pickle.loads(self.buff)
        self.buff = b''

        try:
            if self.format is ():
                self.format = data['format']
            if not len(data) == 0 and not data['data'].empty:
                new_data = data['data']
                # if not data['data'].empty:
                #     self.data_lock.acquire()
                #     try:
                #         self.data_stream = self.data_stream.append(data['data'])
                #         if self.giveScan:
                #             if self.currentScan:
                #                 try:
                #                     if not data['data']['scan'][-1] == self.data_current_scan['scan'][-1]:
                #                         self.data_previous_scan = self.data_current_scan
                #                         self.data_current_scan = pd.DataFrame()
                #                 except:
                #                     pass
                #                 self.data_current_scan = self.data_current_scan.append(data['data'])
                #                 self.data = self.data_current_scan
                #             else:
                #                 try:
                #                     if not data['data']['scan'][-1] == self.data_previous_scan['scan'][-1]:
                #                         self.data_previous_scan = pd.DataFrame()
                #                 except:
                #                     pass
                #                 self.data_previous_scan = self.data_previous_scan.append(data['data'])
                #                 self.data = self.data_previous_scan
                #         else:
                #             self.data = self.data_stream
                #         if self._clear_memory:
                #             self.data_stream = self.data_stream[-10:]
                #             self._clear_memory = False
                #     finally:
                #         self.data_lock.release()
                self.data_lock.acquire()
                m = new_data['scan'].max()
                self.data_stream = self.data_stream.append(new_data)
                self.data_stream.drop_duplicates(inplace=True)
                if m > -1:
                    if self.data_current_scan.empty:
                        self.data_current_scan = new_data[new_data['scan'] == m]
                    else:
                        if m > self.data_current_scan['scan'][-1]:
                            self.data_previous_scan, self.data_current_scan = self.data_current_scan, new_data[new_data['scan'] == m]
                        else:
                            if m == self.data_current_scan['scan'][-1]:
                                self.data_current_scan = self.data_current_scan.append(new_data[new_data['scan'] == m])
                                self.data_current_scan.drop_duplicates(inplace=True)
                            else:
                                self.data_previous_scan = self.data_previous_scan.append(new_data[new_data['scan'] == m])
                                self.data_previous_scan.drop_duplicates(inplace=True)

                if not self._clear_memory:
                    pass
                else:
                    self.data_stream = self.data_stream[-10:]
                    self._clear_memory = False
                if self.giveScan:
                    if self.currentScan:
                        self.data = self.data_current_scan
                    else:
                        self.data = self.data_previous_scan
                else:
                    self.data = self.data_stream
                self.data_lock.release()
        except TypeError:
            pass

        self.send_next()

    def changeMemory(self, value):
        self.push(pickle.dumps(['Set Memory Size', value]))
        self.push('END_MESSAGE'.encode('UTF-8'))

    def clearMemory(self):
        self._clear_memory = True
        self.push(pickle.dumps(['Clear Memory']))
        self.push('END_MESSAGE'.encode('UTF-8'))

    def send_next(self):
        cols = [xy for xy in self.xy if not xy == 'time']
        self.data_lock.acquire()
        try:
            if self.giveScan:
                if self.currentScan:
                    latest = self.data_current_scan.index.values[-1]
                else:
                    latest = self.data_previous_scan.index.values[-1]
            else:
                latest = self.data_stream.index.values[-1]
        except:
            latest = None
        self.data_lock.release()
        self.push(pickle.dumps(['data', ([self.giveScan, self.currentScan], latest, cols)]))
        self.push('END_MESSAGE'.encode('UTF-8'))
