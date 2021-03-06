from backend.helpers import *
from backend.save import *
from backend.connectors import Connector, Acceptor
import backend.logbook as lb
from backend.dispatcher import Dispatcher

import os,sys
import multiprocessing as mp
import configparser

CHUNK_SIZE = 10**4

class DataServer(Dispatcher):
    def __init__(self, name='data_server'):
        super(DataServer, self).__init__(name)
        ### get configuration details
        self.save_path = self.config_parser['paths']['data_path']
        if not os.path.exists(self.save_path):
            try:
                os.makedirs(self.save_path)
            except:
                # in case the file server or something just made it
                pass
        self.time_offset = int(self.config_parser['other']['time_offset'])
        
        self.data = {}
        self.scan_data = {}
        self.mode = 'stream'
        self.current_scan = -1
        self.current_mass = -1

        self.format = {}

        self.no_of_rows = {}
        self.no_of_rows_scan = {}

        self.saving_devices = {}
        self.saving_stream_devices = {}

        self.buffer_size = 10**5

        self.backupFlag = mp.Event()
        self.backupFlag.clear()

        self.save_output, self.save_input = mp.Pipe(duplex=False)

        self.start_saving()

    def stop(self):
        self.saveProcess.terminate()
        super(DataServer,self).stop()

    def default_cb(self):
        rep = time.time()-self.time_offset
        return 'data', {'t0': rep}

    def start_saving(self):
        args = (self.save_output,self.save_path)
        self.saveProcess = mp.Process(target=save_continuously_dataserver,
                                      args=args)
        self.saveProcess.start()

    @try_call
    def create_backup(self, *args):
        self.backupFlag.set()
        return {'status': [0]}

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
            col = self.format[origin].index(par_name)
            row = DS_no_of_rows[origin]-no_of_rows[origin]
        except KeyError as e:
            # print(e,self.format.keys(),DS_no_of_rows.keys(),no_of_rows.keys(),self.data.keys())
            # no scans yet
            return [[],[]]

        return_list = []
        if row > 0:
            return_list.append(list(data_set[0,-row:])) #timestamp as well
            return_list.append(list(data_set[col,-row:]))
        else:
            # row == 0 means the DataViewer is up to date, nothing to send
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
            return {'data':[],'format':self.format,
                    'no_of_rows':DS_no_of_rows,
                    'current_scan':self.current_scan,
                    'mass':self.current_mass}

        return_list = []
        for name_info in [x,y]:
            ret_list = self.slice_new_data(name_info,
                    no_of_rows,DS_no_of_rows)
            return_list.extend(ret_list)

        return {'data': return_list,
                'no_of_rows':DS_no_of_rows,
                'current_scan':self.current_scan,
                'mass':self.current_mass}

    @try_call
    def change_mode(self,params):
        self.mode = params['mode']
        return {'status': [0]}

    # @try_call
    # def clear_memory(self, *args):
    #     self._clear_memory = True
    #     return {'status': [0]}

    # @try_call
    # def set_memory_size(self, **kwargs):
    #     mem = np.abs(int(kwargs['memory_size'][0]))
    #     self.memory = mem
    #     return {'status': [0]}

    @try_call
    def status(self, *args):
        return {'connector_info': self.connInfo,'no_of_rows':self.no_of_rows,
                'saving_devices':self.saving_devices,
                'saving_stream_devices':self.saving_stream_devices}

    @try_call
    def get_latest(self,*args):
        return {'data_format': self.format,
                'latest_data':{n:list(d[-1]) for n,d in self.data.items()}}

    @try_call
    def data_format(self, *args):
        return {'data_format': self.format,
                'current_scan':self.current_scan}

    def data_reply(self,track,params):
        data = params['data']
        self.current_mass = params['mass']
        origin, track_id = track[-1]

        if data == []:
            return

        self.saving_devices[origin] = params['save']
        self.saving_stream_devices[origin] = params['save_stream']

        if params['save']:
            self.save_input.send((origin,
                                  self.format[origin],
                                  data,
                                  self.saving_stream_devices[origin]))

        #add the data to the buffer (a dict of numpy arrays)
        try:
            if len(self.data[origin])<self.buffer_size:
                self.data[origin] = np.concatenate((self.data[origin],data))
            else:
                self.data[origin] = np.roll(self.data[origin],-len(data),axis=0)
                self.data[origin][-len(data):] = data

        except KeyError:
            # first time we see this device
            self.data[origin] = data
            self.no_of_rows[origin] = 0
        finally:
            # some bookkeeping for DataViewer communications
            self.no_of_rows[origin] += len(data)

        ## add the most recent scan to a separate buffer
        #turn the list of data lists into a nice array
        data = np.row_stack(data)
        #group it
        grouped_data = group_per_scan(data,
                    axis=self.format[origin].index('scan_number'))
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

    def initial_information_reply(self,track,params):
        origin, track_id = track[-1]
        self.format[origin] = params['format']