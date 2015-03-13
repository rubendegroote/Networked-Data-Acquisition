from .forms import LoginForm, ParameterForm
import logging

from bokeh.embed import components
from bokeh.models import ColumnDataSource
from bokeh.plotting import figure
from bokeh.resources import Resources
from bokeh.templates import RESOURCES
from bokeh.utils import encode_utf8
from bokeh.models.widgets import HBox, Paragraph, Slider, VBox

from flask import render_template, flash, redirect, session, url_for, request, g
from flask.ext.login import login_user, logout_user, current_user, login_required
from app import app, db, lm, oid
import numpy as np
from .models import User
from .manager import makeManager, start
import threading as th

logging.basicConfig(level=logging.INFO)
bokeh_url = 'http://ksf712:5006'

m = makeManager([('KSF712', 5005)])
t = th.Thread(target=start).start()

global parameters
parameters = [0, 0, 0, 0, False]


@app.before_request
def before_request():
    g.user = current_user


@app.route('/')
@app.route('/index')
@login_required
def index():
    user = g.user
    posts = [  # fake array of posts
        {
            'author': {'nickname': 'John'},
            'body': 'Beautiful day in Portland!'
        },
        {
            'author': {'nickname': 'Susan'},
            'body': 'The Avengers movie was so cool!'
        }
    ]
    return render_template("index.html",
                           title='Home',
                           user=user,
                           posts=posts)


@app.route('/login', methods=['GET', 'POST'])
@oid.loginhandler
def login():
    if g.user is not None and g.user.is_authenticated():
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        session['remember_me'] = form.remember_me.data
        return oid.try_login(form.openid.data, ask_for=['nickname', 'email'])
    return render_template('login.html',
                           title='Sign In',
                           form=form,
                           providers=app.config['OPENID_PROVIDERS'])

@oid.after_login
def after_login(resp):
    if resp.email is None or resp.email == "":
        flash('Invalid login. Please try again.')
        return redirect(url_for('login'))
    user = User.query.filter_by(email=resp.email).first()
    if user is None:
        nickname = resp.nickname
        if nickname is None or nickname == "":
            nickname = resp.email.split('@')[0]
        user = User(nickname=nickname, email=resp.email)
        db.session.add(user)
        db.session.commit()
    remember_me = False
    if 'remember_me' in session:
        remember_me = session['remember_me']
        session.pop('remember_me', None)
    login_user(user, remember=remember_me)
    return redirect(request.args.get('next') or url_for('index'))


@app.route('/parameters', methods=['GET', 'POST'])
def parameter():
    form = ParameterForm()
    if form.validate_on_submit():
        # print(request.form['submit'])
        # if 'submit' == request.form['submit']:
        #     logging.info('Goes into submit')
        #     setParams(form)
        #     flash('Changed parameters!')
        #     flashParams()
        #     return redirect('/parameters')
        pass
    if request.method == 'POST':
        if 'stop' == request.form['submit']:
            flash('Stop!')
            m.send_instruction('Wouter', ["STOP"])
        if 'start' == request.form['submit']:
            flash('Start!')
            m.send_instruction('Wouter', ["START"])
        if 'restart' == request.form['submit']:
            flash('Restart!')
            m.send_instruction('Wouter', ["RESTART"])
        if 'submit' == request.form['submit']:
            setParams(form)
    return render_template('parameters.html',
                           title='Input parameters',
                           form=form)


def setParams(form):
    # global parameters
    # parameters = [form.parameter1.data,
    #               form.parameter2.data,
    #               form.parameter3.data,
    #               form.parameter4.data,
    #               form.saving.data]
    scanrange = np.linspace(form.parameter1.data,
                            form.parameter2.data,
                            form.parameter3.data)
    m.send_instruction('Wouter', ["Scan", '', scanrange, form.parameter4.data])


def flashParams():
    global parameters
    st = 'Parameter 1: {}, Parameter 2: {}, Parameter 3: {}, Parameter 4: {}, Saving: {}'
    flash(st.format(*parameters))

@app.route('/data')
def render_plot():
    return render_template('app_plot.html')
