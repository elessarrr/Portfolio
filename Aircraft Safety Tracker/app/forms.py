from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, Email, Optional

class RequestDataForm(FlaskForm):
    aircraft_model = StringField('Aircraft Model', validators=[DataRequired()])
    email = StringField('Your Email (Optional)', validators=[Optional(), Email()])
    submit = SubmitField('Request Data')