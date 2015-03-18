import asynchat
import asyncore
from collections import deque
from datetime import datetime
import logging
import pickle
import socket
import threading as th
import time

from bokeh.embed import autoload_server
from Helpers import *
import numpy as np
import pandas as pd

logging.basicConfig(format='%(asctime)s: %(message)s',
                    level=logging.INFO)


class Population(object):

    location = 'y'
    timeDict = dict(years=['%Y'],
                    months=['%m/%Y'],
                    days=['%d/%m/%Y'],
                    hours=['%d/%m %T'],
                    minutes=['%T'],
                    seconds=['%T'])

    def __init__(self):
        from bokeh.models import ColumnDataSource
        from bokeh.document import Document
        from bokeh.session import Session

        self.document = Document()
        self.session = Session(root_url='http://ksf712:5006/')
        self.session.use_doc('population_reveal')
        self.session.load_document(self.document)

        self.df = pd.DataFrame(
            {'time': np.array([datetime.now()]),
             'y': np.array([0]),
             'z': np.array([0])})
        self.source_pyramid = ColumnDataSource(data=dict())

        # just render at the initialization
        self._render()

    def _render(self):
        self.pyramid_plot()
        self.create_layout()
        self.document.add(self.layout)
        self.update_pyramid()

    def pyramid_plot(self):
        from bokeh.models import DataRange1d, Legend
        from bokeh.models.glyphs import Line
        from bokeh.plotting import figure
        xdr = DataRange1d(sources=[self.source_pyramid.columns("x")])
        ydr = DataRange1d(sources=[self.source_pyramid.columns("y")])

        TOOLS = "pan,wheel_zoom,box_zoom,reset,save"
        self.plot = figure(x_range=xdr, y_range=ydr, tools=TOOLS,
                           plot_width=600, plot_height=600,
                           x_axis_type='datetime')
        self.plot.below[0].formatter.formats = self.timeDict

        testline = Line(x="x", y="y", line_color="#F46D43")
        testLineGlyph = self.plot.add_glyph(self.source_pyramid, testline)

        self.plot.add_layout(Legend(legends=dict(Testline=[testLineGlyph])))

    def on_location_change(self, obj, attr, old, new):
        self.location = new
        self.update_pyramid()

    def create_layout(self):
        from bokeh.models.widgets import Select, HBox, VBox

        source = ['x', 'y', 'z']

        source_select = Select(title="Source:", value="y", options=source)

        source_select.on_change('value', self.on_location_change)

        controls = HBox(source_select)
        self.layout = VBox(controls, self.plot)

    def update_pyramid(self):
        pyramid = self.df[self.location]
        self.source_pyramid.data = dict(
            x=np.array([np.datetime64(v) for v in self.df['time'].values]),
            y=pyramid
        )
        try:
            self.session.store_document(self.document)
        except:
            pass


def update_population(plot, reader):
    plot.df = reader._data
    plot.update_pyramid()
    plot.session.load_document(plot.document)


def render_plot():
    pop = Population()
    pop_tag = autoload_server(pop.layout, pop.session)

    html = """
{%% extends "base.html" %%}
{%% block content %%}
<head>
<meta charset='utf-8' />
<meta http-equiv='content-type' content='text/html; charset=utf-8' />

</head>
<body>
%s
</body>
{%% endblock %%}
"""
    html = html % pop_tag
    with open("Website/app/templates/app_plot.html", "w+") as f:
        f.write(html)
    return pop


SAVE_INTERVAL = 2
SHARED = ['scan','time']

class DataServer():

    def __init__(self, artists=[], save=True, remember=True):
        self._readers = {}
        self.saveDir = "Server"
        self.dQs = {}
        # self.plot = render_plot()
        for address in artists:
            self.addReader(address)
        self._saveThread = th.Timer(1, self.save).start()
        self.save_data = save
        self.remember = remember
        if remember:
            self._data = pd.DataFrame()
            self._data_current_scan = pd.DataFrame()

    def addReader(self, address=None):
        if address is None:
            logging.warning('provide IP address and PORT')
            return
        logging.info('Adding reader')
        # try:
        reader = ArtistReader(IP=address[0], PORT=int(address[1]))
        self._readers[reader.artistName] = reader
        self.dQs[reader.artistName] = deque()
        self._readers[reader.artistName].dQ = self.dQs[reader.artistName]
        # except Exception as e:
        #     print('Connection failed')

    def save(self):
        # This is not doing it right! Data files of all receivers
        # should be merged before saving!
        # should be better now, but never run before!!!
        now = time.time()
        new_data = pd.DataFrame()
        for name, reader in self._readers.items():
            dQ = self.dQs[name]
            l = len(dQ)
            if not l == 0:
                data = [dQ.popleft() for i in range(l)]
                data = mass_concat(flatten(data), format=reader._format)
                if self.save_data:
                    print(len(data))
                    save(data,self.saveDir,reader.artistName)
                new_data = new_data.append(data)

        if not len(new_data) == 0:
            if self.remember:
                self.extractMemory(new_data)

        # slightly more stable if the save runs every 0.5 seconds,
        # regardless of how long the previous saving took
        wait = abs(min(0, time.time() - now - SAVE_INTERVAL))
        print(wait)
        self._saveThread = th.Timer(wait, self.save).start()

    def extractMemory(self, new_data):
        self._data = self._data.append(new_data)
        # save the current scan in memory!
        groups = self._data.groupby('scan')
        # not sure this works - is groups a dictionary?
        # self._data_current_scan = groups[max(groups.keys)]
        # save last 10.000 data points
        self._data = self._data[-100:]

        # self.bin_current()
        # print(self._data)

        # update_population(self.plot, self)

    def bin_current(self):
        # some stuff about binning the current data in some
        # XY format with certain X steps 'n stuff
        pass


class ArtistReader(asynchat.async_chat):

    def __init__(self, IP='KSF402', PORT=5005):
        super(ArtistReader, self).__init__()
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        # self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self.connect((IP, PORT))
        time.sleep(0.1)
        self.send('Server'.encode('UTF-8'))

        self.artistName = self.wait_for_connection()

        self._data = pd.DataFrame()
        self._buffer = b''
        self.set_terminator('STOP_DATA'.encode('UTF-8'))
        self.push('Next'.encode('UTF-8') + 'END_MESSAGE'.encode('UTF-8'))
        self.total = 0

    def wait_for_connection(self):
        # Wait for connection to be made with timeout
        success = False
        now = time.time()
        while time.time() - now < 5:  # Tested: raises RunTimeError after 5 s
            try:
                name = self.recv(1024).decode('UTF-8')
                success = True
                break
            except:
                pass
        if not success:
            raise

        return name

    def collect_incoming_data(self, data):
        self._buffer += data

    def found_terminator(self):
        buff = self._buffer
        self.total += len(self._buffer)
        # try:
        #     print(int(self.total/(time.time() - self.now))/1000000)
        # except:
        #     self.now = time.time()

        self._buffer = b''
        data = pickle.loads(buff)
        if type(data) == tuple:
            self._format = tuple([self.artistName + d if d not in SHARED else d for d in data])
        else:
            if not data == []:
                self.dQ.append(data)
            self.push('Next'.encode('UTF-8') + 'END_MESSAGE'.encode('UTF-8'))


def makeServer(channel=[('KSF402', 5005)], save=True, remember=True):
    return DataServer(channel, save, remember)

def start():
    while True:
        asyncore.loop(count=1)
        time.sleep(0.01)

def main():
    # render_plot()
    channels = input('IP,PORTS?').split(";")
    channels = [c.split(",") for c in channels]
    d = makeServer(channels, save=int(input('save?'))==1, remember=int(input('remember?'))==1)
    asyncore.loop(0.001)

if __name__ == '__main__':
    main()
