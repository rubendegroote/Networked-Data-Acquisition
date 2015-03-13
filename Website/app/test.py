import time
from threading import Thread

import numpy as np
import pandas as pd
import scipy.special

from bokeh.embed import autoload_server
from bokeh.models import GlyphRenderer
from bokeh.plotting import cursession, figure, output_server, push


class Population(object):

    location = 'y'

    def __init__(self):
        from bokeh.models import ColumnDataSource
        from bokeh.document import Document
        from bokeh.session import Session

        self.document = Document()
        self.session = Session(root_url='http://ksf712:5006/')
        self.session.use_doc(name='population_reveal')
        self.session.load_document(self.document)

        self.df = pd.DataFrame(
            {'x': np.linspace(-10, 0), 'y': np.sin(np.linspace(-10, 0)), 'z': np.exp(np.linspace(-10, 0))})
        self.source_pyramid = ColumnDataSource(data=dict())

        # just render at the initialization
        self._render()

    def _render(self):
        self.pyramid_plot()
        self.create_layout()
        self.document.add(self.layout)
        self.update_pyramid()

    def pyramid_plot(self):
        from bokeh.models import (Plot, DataRange1d, LinearAxis, Grid,
                                  Legend, SingleIntervalTicker)
        from bokeh.models.glyphs import Line
        xdr = DataRange1d(start=-10, end=10)
        ydr = DataRange1d(start=-1, end=1)

        self.plot = Plot(title="Widgets", x_range=xdr, y_range=ydr,
                         plot_width=600, plot_height=600)

        xaxis = LinearAxis()
        self.plot.add_layout(xaxis, 'below')
        yaxis = LinearAxis(ticker=SingleIntervalTicker(interval=5))
        self.plot.add_layout(yaxis, 'left')

        self.plot.add_layout(Grid(dimension=0, ticker=xaxis.ticker))
        self.plot.add_layout(Grid(dimension=1, ticker=yaxis.ticker))

        testline = Line(x="x", y="y", line_color="#F46D43", line_width=6, line_alpha=0.6)
        testLineGlyph = self.plot.add_glyph(self.source_pyramid, testline)

        self.plot.add_layout(Legend(legends=dict(Testline=[testLineGlyph])))

    def on_location_change(self, obj, attr, old, new):
        self.location = new
        self.update_pyramid()

    def create_layout(self):
        from bokeh.models.widgets import Select, HBox, VBox

        source = ['y', 'z']

        source_select = Select(title="Source:", value="y", options=source)

        source_select.on_change('value', self.on_location_change)

        controls = HBox(source_select)
        self.layout = VBox(controls, self.plot)

    def update_pyramid(self):
        pyramid = self.df[self.location]

        self.source_pyramid.data = dict(
            x=self.df['x'].data,
            y=pyramid.data
        )
        self.session.store_document(self.document)
