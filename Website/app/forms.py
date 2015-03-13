from flask.ext.wtf import Form
from wtforms import StringField, BooleanField, FloatField
from wtforms.validators import DataRequired


class LoginForm(Form):
    openid = StringField('openid', validators=[DataRequired()])
    remember_me = BooleanField('remember_me', default=False)


class ParameterForm(Form):
    parameter1 = FloatField('parameter_1', validators=[DataRequired()])
    parameter2 = FloatField('parameter_2', validators=[DataRequired()])
    parameter3 = FloatField('parameter_3', validators=[DataRequired()])
    parameter4 = FloatField('parameter_4', validators=[DataRequired()])
    saving = BooleanField('saving_boolean', default=False)
