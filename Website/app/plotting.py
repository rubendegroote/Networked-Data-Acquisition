import time
from threading import Thread
from bokeh.models import GlyphRenderer
from flask import render_template, flash, redirect, session, url_for, request, g

import numpy as np
import pandas as pd

from bokeh.embed import autoload_server


class Population(object):

    location = 'y'

    def __init__(self):
        from bokeh.models import ColumnDataSource
        from bokeh.document import Document
        from bokeh.session import Session

        self.document = Document()
        self.session = Session(root_url='http://ksf712:5006/')
        self.session.use_doc('population_reveal')
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
        from bokeh.models import (DataRange1d, LinearAxis, Grid,
                                  Legend, SingleIntervalTicker)
        from bokeh.models.glyphs import Line
        from bokeh.plotting import figure
        xdr = DataRange1d(sources=[self.source_pyramid.columns("x")])
        ydr = DataRange1d(sources=[self.source_pyramid.columns("y")])

        TOOLS = "pan,wheel_zoom,box_zoom,reset,save"
        self.plot = figure(x_range=xdr, y_range=ydr, tools=TOOLS,
                           plot_width=600, plot_height=600)
        # self.plot = Plot(title="Widgets", x_range=xdr, y_range=ydr,
        #                  plot_width=600, plot_height=600,
        #                  tools="pan")

        # xaxis = LinearAxis()
        # self.plot.add_layout(xaxis, 'below')
        # yaxis = LinearAxis(ticker=SingleIntervalTicker(interval=5))
        # self.plot.add_layout(yaxis, 'left')

        # self.plot.add_layout(Grid(dimension=0, ticker=xaxis.ticker))
        # self.plot.add_layout(Grid(dimension=1, ticker=yaxis.ticker))

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
            x=self.df['x'].values,
            y=pyramid.values
        )

        self.session.store_document(self.document)


def update_population(plot):
    while True:
        for i in np.linspace(1, -1):
            plot.df['y'], plot.df['z'] = i * np.sin(plot.df['x']), i * np.exp(plot.df['x'])
            plot.update_pyramid()
            plot.session.load_document(plot.document)
            # time.sleep(0.1)

            # rmin = ds.data["inner_radius"]
        #     ds.data["inner_radius"] = rmin

        #     rmax = ds.data["outer_radius"]
        #     rmax = roll(rmax, -1)
        #     ds.data["outer_radius"] = rmax

        #     cursession().store_objects(ds)


def render_plot():
    """
    Get the script tags from each plot object and "insert" them into the template.
    This also starts different threads for each update function, so you can have
    a non-blocking update.
    """
    # dist_plot, dist_session = distribution()
    # dist_tag = autoload_server(dist_plot, dist_session)

    # anim_plot, anim_session = animated()
    # anim_tag = autoload_server(anim_plot, anim_session)
    # # for update_animation as target we need to pass the anim_plot and anim_session as args
    # thread = Thread(target=update_animation, args=(anim_plot, anim_session))
    # thread.start()

    pop = Population()
    pop_tag = autoload_server(pop.layout, pop.session)
    # for update_population as target we need to pass the pop instance as args
    # thread = Thread(target=update_population, args=(pop,))
    # thread.start()

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
    with open("templates/app_plot.html", "w+") as f:
        f.write(html)

render_plot()
