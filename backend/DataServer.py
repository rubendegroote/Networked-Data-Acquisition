import sys
from Helpers import *
from save import *
from connectors import Connector, Acceptor
import logbook as lb
from dispatcher import Dispatcher
import multiprocessing as mp

class DataServer(Dispatcher):
    def __init__(self, PORT=5006, name='DataServer'):
        super(DataServer, self).__init__(PORT, name)
        self.data = {}
        self.scan_data = {}

        self.formats = {}
        
        self.no_of_rows = {}
        self.no_of_rows_scan = {}

        self.buffer_size = 50000

        self.saveDir = "C:\\Data\\"
        self.save_output,self.save_input = mp.Pipe(duplex=False)

        self.start_saving()

    def default_cb(self):
        return 'data', {}

    def start_saving(self):
        args = (self.save_output,self.saveDir)
        self.saveProcess = mp.Process(target = save_continuously_dataserver,
                                      args = args)
        self.saveProcess.start()

    def slice_new_data(self,name_info,no_of_rows,
                            DS_no_of_rows,data_set):
        # decide on the column and from what row onwards
        origin = name_info[0]
        par_name = name_info[1]

        col = self.formats[origin].index(par_name)
        row = DS_no_of_rows[origin]-no_of_rows[origin]
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
    def scan(self,params):
        self.data(params,stream=False)

    @try_call
    def stream(self,params):
        self.data(params,stream=True)

    def data(self,params,stream=True):
        x,y = params['x'],params['y']

        no_of_rows = params['no_of_rows']
        if stream:
            DS_no_of_rows = self.no_of_rows
            data_set = self.data[origin].T
        else:
            DS_no_of_rows = self.no_of_rows_scan
            data_set = self.scan_data[origin].T

        if x == [] and y == []:
            # no specific columns sent; user does not know
            # the options yet
            return {'data':[],'format':self.formats,
                    'no_of_rows':DS_no_of_rows}

        return_list = []
        for name_info in [x,y]:
            ret_list = slice_new_data(i,name_info,
                    no_of_rows,DS_no_of_rows,data_set=data_set)
            return_list.extend(ret_list)

        return {'data': return_list,
                'no_of_rows':DS_no_of_rows}
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
        data = params['data']
        format = params['format']
        origin, track_id = track[-1]

        if data == []:
            return

        #send the data as is to be saved
        self.save_input.send((origin,format,data))

        ### do grouping based on scan number here!
        ### once grouped, add current scan to current
        ### scan array (clear it if new scan)
        ### send the grouped scan data to the save pipe as well
        ## to update no_of_rows_scan as well
        
        #add the data to the buffer (a dict of numpy arrays)
        try:
            if len(self.data[origin])<self.buffer_size:
                self.data[origin] = np.concatenate((self.data[origin],data))
            else:
                self.data[origin] = np.roll(self.data[origin],-len(data),axis=0)
                self.data[origin][-len(data):] = data

        except KeyError:
            # first time we see this artist
            self.data[origin] = np.row_stack(data)
            self.no_of_rows[origin] = 0
        finally:
            # some bookkeeping for radio communications
            self.no_of_rows[origin] += len(data)
            self.formats[origin] = format
        
def makeServer(PORT=5006):
    return DataServer(PORT)

def main():
    try:
        d = makeServer(5005)
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
