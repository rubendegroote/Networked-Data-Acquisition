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
        self.formats = {}
        self.no_of_rows = {}
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
    def data(self, params):
        no_of_rows,x,y = params['no_of_rows'],params['x'],params['y']

        if x == [] and y == []:
            return {'data':[],'format':self.formats,'no_of_rows':self.no_of_rows}
        else:
            return_list = []

            for i in [x,y]:
                col = self.formats[i[0]].index(i[1])
                row = min(self.no_of_rows[i[0]] - no_of_rows[i[0]],self.buffer_size)
                if not row == 0:
                    dataset = self.data_dict[i[0]].T
                    return_list.append(list(dataset[0,-row:])) #timestamp as well
                    return_list.append(list(dataset[col,-row:]))
                else:
                    return_list.append([])
                    return_list.append([])

            return {'data': return_list,'no_of_rows':self.no_of_rows}

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
        data,format = params['data'],params['format']
        origin, track_id = track[-1]
        if data == []:
            return
        try:
            if len(self.data_dict[origin])<self.buffer_size:
                self.data_dict[origin] = np.concatenate((self.data_dict[origin],data))
            else:
                self.data_dict[origin] = np.roll(self.data_dict[origin],-len(data),axis=0)
                self.data_dict[origin][-len(data):] = data

        except KeyError:
            self.data_dict[origin] = np.row_stack(data)
            self.no_of_rows[origin] = 0
        finally:
            self.no_of_rows[origin] += len(data)
            self.formats[origin] = format

        self.save_input.send((origin,format,data))

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
