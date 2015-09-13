import sys
from Helpers import *
from save import *
from connectors import Connector, Acceptor
import logbook as lb
from dispatcher import Dispatcher
import multiprocessing as mp

class DataServer(Dispatcher):
    def __init__(self, PORT=5006, save_data=False, remember=True, name='DataServer'):
        super(DataServer, self).__init__(PORT, name, defaultRequest=('data',{}))
        self.data_dict = {}
        self.data_dict['scan'] = {}
        self.data_dict['stream'] = {}

        self.formats = {}
        
        self.no_of_rows = {}
        self.no_of_rows['scan'] = {}
        self.no_of_rows['stream'] = {}

        self.buffer_size = 50000

        self.save_data = save_data
        if save_data:
            self.savedScan = -np.inf
            self.saveDir = "C:\\Data\\"
            self.save_output,self.save_input = mp.Pipe(duplex=False)

        self.start_saving()

    def default_cb(self):
        return 'data', {}

    def start_saving(self):
        self.saveProcess = mp.Process(target = save_continuously_dataserver,
                                      args = (self.save_output,
                                              self.saveDir))
        self.saveProcess.start()

    @try_call
    def stream(self, params):
        self.data(params,prefix='stream')

    @try_call
    def scan(self,params):
        self.data(params,prefix='scan')

    def data(self,params,prefix):
        no_of_rows = params['no_of_rows']
        x,y = params['x'],params['y']

        buffers_cleard = False # set to True if the radio has
                               # more data than the server

        if x == [] and y == []:
            # no specific columns sent; user does not know
            # the options yet
            return {'data':[],'format':self.formats,
                    'no_of_rows':self.no_of_rows[prefix],
                    'buffers_cleard':buffers_cleard}
        else:
            return_list = []
            for i in [x,y]:
                # decide on the column and from what row onwards
                col = self.formats[i[0]].index(i[1])
                row = min(self.no_of_rows[prefix][i[0]]-no_of_rows[i[0]],
                          self.buffer_size)
                if row < 0:
                    # radio has more data than server; 
                    # buffers were just cleared
                    buffers_cleard = True
                    # send all we have!
                    dataset = self.data_dict[prefix][i[0]].T
                    return_list.append(list(dataset[0])) #timestamp as well
                    return_list.append(list(dataset[col]))
                elif row > 0:
                    dataset = self.data_dict[prefix][i[0]].T
                    return_list.append(list(dataset[0,-row:])) #timestamp as well
                    return_list.append(list(dataset[col,-row:]))
                else:
                    # row == 0 means the radio is up to date, nothing to send
                    return_list.append([])
                    return_list.append([])

            return {'data': return_list,
                    'no_of_rows':self.no_of_rows[prefix],
                    'buffers_cleard':buffers_cleard}

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
        return {'data_format': self.formats}

    def data_reply(self,track,params):
        data,scan_data = params['data'],params['scan_data']
        scan_just_started = params['scan_just_started']
        format = params['format']
        origin, track_id = track[-1]

        # add the stream data to a rolling buffer
        if not data == []:
            try:
                if len(self.data_dict['stream'][origin])<self.buffer_size:
                    self.data_dict['stream'][origin] = np.concatenate((self.data_dict['stream'][origin],data))
                else:
                    self.data_dict['stream'][origin] = np.roll(self.data_dict['stream'][origin],-len(data),axis=0)
                    self.data_dict['stream'][origin][-len(data):] = data

            except KeyError:
                self.data_dict['stream'][origin] = np.row_stack(data)
                self.no_of_rows['stream'][origin] = 0
            finally:
                self.no_of_rows['stream'][origin] += len(data)
                self.formats[origin] = format

            self.save_input.send((origin,format,data))
        
        # add the scan data to a growing buffer
        if not scan_data == []:
            if scan_just_started: # clear buffer if this is a new scan
                self.data_dict['scan'][origin] = np.row_stack(scan_data)
                self.no_of_rows['scan'][origin] = 0
            else:
                self.data_dict['scan'][origin] = np.concatenate((self.data_dict['scan'][origin],scan_data))
                self.no_of_rows['scan'][origin] += len(scan_data)
            self.formats[origin] = format

def makeServer(PORT=5006, save=True, remember=True):
    return DataServer(PORT, save, remember)

def main():
    try:
        d = makeServer(5005, save=1, remember=1)
        style = "QLabel { background-color: green }"
        e = ''
    except Exception as error:
        e = str(error)
        style = "QLabel { background-color: red }"

    from PyQt4 import QtCore, QtGui
    # Small visual indicator that this is running
    app = QtGui.QApplication(sys.argv)
    w = QtGui.QWidget()

    w.setWindowTitle('Data Server')
    layout = QtGui.QGridLayout(w)
    label = QtGui.QLabel(e)
    label.setStyleSheet(style)
    layout.addWidget(label)
    w.show()

    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
