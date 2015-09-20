from backend.Helpers import *
from backend.save import *
from backend.connectors import Connector, Acceptor
import backend.logbook as lb
from backend.dispatcher import Dispatcher

import sys
import multiprocessing as mp

SAVE_DIR = "C:\\Data\\Gallium Run\\"

class DataServer(Dispatcher):
    def __init__(self, PORT=5006, name='DataServer'):
        super(DataServer, self).__init__(PORT, name)
        self.data = {}
        self.scan_data = {}
        self.mode = 'stream'
        self.current_scan = -1

        self.formats = {}
        
        self.no_of_rows = {}
        self.no_of_rows_scan = {}

        self.buffer_size = 50000

        self.save_output,self.save_input = mp.Pipe(duplex=False)

        self.start_saving()

    def stop(self):
        self.saveProcess.terminate()
        super(DataServer,self).stop()

    def default_cb(self):
        return 'data', {}

    def start_saving(self):
        args = (self.save_output,SAVE_DIR)
        self.saveProcess = mp.Process(target = save_continuously_dataserver,
                                      args = args)
        self.saveProcess.start()

    def slice_new_data(self,name_info,no_of_rows,
                            DS_no_of_rows):
        # decide on the column and from what row onwards
        origin = name_info[0]
        par_name = name_info[1]

        try:
            if self.mode == 'stream':
                data_set = self.data[origin].T
            else:
                data_set = self.scan_data[origin].T
            col = self.formats[origin].index(par_name)
            row = DS_no_of_rows[origin]-no_of_rows[origin]
        except KeyError:
            # no scans yet
            return [[],[]]
            
            row = min(row,self.buffer_size)

        return_list = []
        if row > 0:
            return_list.append(list(data_set[0,-row:])) #timestamp as well
            return_list.append(list(data_set[col,-row:]))
        else:
            # row == 0 means the radio is up to date, nothing to send
            return_list.append([])
            return_list.append([])

        return return_list

    @try_call    
    def get_data(self,params):
        x,y = params['x'],params['y']

        no_of_rows = params['no_of_rows']
        if self.mode == 'stream':
            DS_no_of_rows = self.no_of_rows
        else:
            DS_no_of_rows = self.no_of_rows_scan

        if x == [] and y == []:
            # no specific columns sent; user does not know
            # the options yet
            return {'data':[],'format':self.formats,
                    'no_of_rows':DS_no_of_rows,
                    'current_scan':self.current_scan}

        return_list = []
        for name_info in [x,y]:
            ret_list = self.slice_new_data(name_info,
                    no_of_rows,DS_no_of_rows)
            return_list.extend(ret_list)
        return {'data': return_list,
                'no_of_rows':DS_no_of_rows,
                'current_scan':self.current_scan}

    @try_call
    def change_mode(self,params):
        self.mode = params['mode']
        return {'status': [0]}

    @try_call
    def clear_memory(self, *args):
        self._clear_memory = True
        return {'status': [0]}

    @try_call
    def set_memory_size(self, **kwargs):
        mem = np.abs(int(kwargs['memory_size'][0]))
        self.memory = mem
        return {'status': [0]}

    @try_call
    def status(self, *args):
        return {'connector_info': self.connInfo,'no_of_rows':self.no_of_rows}

    @try_call
    def data_format(self, *args):
        return {'data_format': self.formats,
                'current_scan':self.current_scan}

    def data_reply(self,track,params):
        data = params['data']
        format = params['format']
        origin, track_id = track[-1]

        if data == []:
            return

        #send the data as is to be saved
        self.save_input.send((origin,format,data))

        #add the data to the buffer (a dict of numpy arrays)
        try:
            if len(self.data[origin])<self.buffer_size:
                self.data[origin] = np.concatenate((self.data[origin],data))
            else:
                self.data[origin] = np.roll(self.data[origin],-len(data),axis=0)
                self.data[origin][-len(data):] = data

        except KeyError:
            # first time we see this artist
            self.data[origin] = data
            self.no_of_rows[origin] = 0
        finally:
            # some bookkeeping for radio communications
            self.no_of_rows[origin] += len(data)
            self.formats[origin] = format

        ## add the most recent scan to a separate buffer
        #turn the list of data lists into a nice array
        data = np.row_stack(data)
        #group it
        grouped_data = group_per_scan(data,
                    axis=format.index('scan_number'))
        scan_no = max(grouped_data.keys())
        if scan_no == -1:
            # no scan data this time
            return

        scan_data = grouped_data[scan_no]
        if not scan_no == self.current_scan:
            self.scan_data = {}
            self.current_scan = scan_no
        else:
            try:
                self.scan_data[origin] = \
                    np.concatenate((self.scan_data[origin],scan_data))
                self.no_of_rows_scan[origin] += len(scan_data)
            except KeyError:
                self.scan_data[origin] = scan_data
                self.no_of_rows_scan[origin] = 0
