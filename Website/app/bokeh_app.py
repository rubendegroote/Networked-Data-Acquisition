import logging


from os import listdir
from os.path import dirname, join, splitext

import numpy as np
import pandas as pd

from bokeh.models import ColumnDataSource, Plot
from bokeh.plotting import figure, curdoc, output_server, Session

from bokeh.properties import String, Instance
from bokeh.models.widgets import HBox, VBox, VBoxForm, PreText, Select

logging.basicConfig(level=logging.DEBUG)


def get_data(ticker1, ticker2):
    data = {'A_returns': np.linspace(0, 10, 100),
            'B_returns': np.linspace(20, 100, 100),
            'date': np.linspace(200, 300, 100)}
    data = pd.DataFrame(data)
    return data


class DatashowingApp(VBox):
    extra_generated_classes = [["DatashowingApp", "DatashowingApp", "VBox"]]
    jsmodel = "VBox"

    # text statistics
    pretext = Instance(PreText)

    # plots
    plot = Instance(Plot)
    line_plot1 = Instance(Plot)
    line_plot2 = Instance(Plot)
    hist1 = Instance(Plot)
    hist2 = Instance(Plot)

    # data source
    source = Instance(ColumnDataSource)

    # layout boxes
    mainrow = Instance(HBox)
    histrow = Instance(HBox)
    statsbox = Instance(VBox)

    # inputs
    ticker1 = String(default="A")
    ticker2 = String(default="B")
    ticker1_select = Instance(Select)
    ticker2_select = Instance(Select)
    input_box = Instance(VBoxForm)

    def __init__(self, *args, **kwargs):
        super(DatashowingApp, self).__init__(*args, **kwargs)
        self._dfs = {}

    @classmethod
    def create(cls):
        """
        This function is called once, and is responsible for
        creating all objects (plots, datasources, etc)
        """
        # create layout widgets
        obj = cls()
        obj.mainrow = HBox()
        obj.histrow = HBox()
        obj.statsbox = VBox()
        obj.input_box = VBoxForm()

        # create input widgets
        obj.make_inputs()

        # outputs
        obj.pretext = PreText(text="", width=500)
        obj.make_source()
        obj.make_plots()
        obj.make_stats()

        # layout
        obj.set_children()
        return obj

    def make_inputs(self):

        self.ticker1_select = Select(
            name='ticker1',
            value='A',
            options=['A', 'B']
        )
        self.ticker2_select = Select(
            name='ticker2',
            value='B',
            options=['A', 'B']
        )

    @property
    def selected_df(self):
        pandas_df = self.df
        selected = self.source.selected
        if selected:
            pandas_df = pandas_df.iloc[selected, :]
        return pandas_df

    def make_source(self):
        self.source = ColumnDataSource(data=self.df)

    def line_plot(self, ticker, x_range=None):
        p = figure(
            title=ticker,
            x_range=x_range,
            x_axis_type='datetime',
            plot_width=1000, plot_height=200,
            title_text_font_size="10pt",
            tools="pan,wheel_zoom,box_select,reset"
        )
        return p

    def hist_plot(self, ticker):
        global_hist, global_bins = np.histogram(self.df[ticker + "_returns"], bins=50)
        hist, bins = np.histogram(self.selected_df[ticker + "_returns"], bins=50)
        width = 0.7 * (bins[1] - bins[0])
        center = (bins[:-1] + bins[1:]) / 2
        start = global_bins.min()
        end = global_bins.max()
        top = hist.max()

        p = figure(
            title="%s hist" % ticker,
            plot_width=500, plot_height=200,
            tools="",
            title_text_font_size="10pt",
            x_range=[start, end],
            y_range=[0, top],
        )
        p.rect(center, hist / 2.0, width, hist)
        return p

    def make_plots(self):
        ticker1 = self.ticker1
        ticker2 = self.ticker2
        p = figure(
            title="%s vs %s" % (ticker1, ticker2),
            plot_width=400, plot_height=400,
            tools="pan,wheel_zoom,box_select,reset",
            title_text_font_size="10pt",
        )
        p.circle(ticker1 + "_returns", ticker2 + "_returns",
                 size=2,
                 nonselection_alpha=0.02,
                 source=self.source
        )
        self.plot = p

        self.line_plot1 = self.line_plot(ticker1)
        self.line_plot2 = self.line_plot(ticker2, self.line_plot1.x_range)
        self.hist_plots()

    def hist_plots(self):
        ticker1 = self.ticker1
        ticker2 = self.ticker2
        self.hist1 = self.hist_plot(ticker1)
        self.hist2 = self.hist_plot(ticker2)

    def set_children(self):
        self.children = [self.mainrow, self.histrow, self.line_plot1, self.line_plot2]
        self.mainrow.children = [self.input_box, self.plot, self.statsbox]
        self.input_box.children = [self.ticker1_select, self.ticker2_select]
        self.histrow.children = [self.hist1, self.hist2]
        self.statsbox.children = [self.pretext]

    def input_change(self, obj, attrname, old, new):
        if obj == self.ticker2_select:
            self.ticker2 = new
        if obj == self.ticker1_select:
            self.ticker1 = new

        self.make_source()
        self.make_plots()
        self.set_children()
        curdoc().add(self)

    def setup_events(self):
        super(DatashowingApp, self).setup_events()
        if self.source:
            self.source.on_change('selected', self, 'selection_change')
        if self.ticker1_select:
            self.ticker1_select.on_change('value', self, 'input_change')
        if self.ticker2_select:
            self.ticker2_select.on_change('value', self, 'input_change')

    def make_stats(self):
        stats = self.selected_df.describe()
        self.pretext.text = str(stats)

    def selection_change(self, obj, attrname, old, new):
        self.make_stats()
        self.hist_plots()
        self.set_children()
        curdoc().add(self)

    @property
    def df(self):
        return get_data(self.ticker1, self.ticker2)
