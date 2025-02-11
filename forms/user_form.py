from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, PasswordField
from wtforms.validators import DataRequired, Email
from models.user import UserType, Country

class UserCreateForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    user_type = SelectField('User Type', 
        choices=[
            (UserType.SUPER_ADMIN.value, 'Super Admin'),
            (UserType.SUPERVISOR.value, 'Supervisor'),
            (UserType.COUNTRY_ADMIN.value, 'Country Admin')
        ],
        validators=[DataRequired()]
    )
    assigned_country = SelectField('Assigned Country',
        choices=[
            (country.value, country.value) for country in Country
        ],
        validators=[]
    ) 