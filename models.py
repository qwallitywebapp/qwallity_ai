from flask import Flask, render_template, flash, redirect, url_for, session,\
     logging, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import update
from wtforms import Form, StringField, PasswordField, validators
from wtforms.validators import Regexp
from flask_mysqldb import MySQL
from datetime import datetime
from flask_marshmallow import Marshmallow


app = Flask(__name__)
mysql = MySQL(app)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://admin:qwallity_db#@qwallitydb.cvy8c6y8c0ri.eu-central-1.rds.amazonaws.com:3306/qwallity_db'
db = SQLAlchemy(app)
ma = Marshmallow(app)

# Create Users table in DB
class Users(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(300), nullable=False)
    username = db.Column(db.Text, nullable=False)
    password = db.Column(db.Text, nullable=False)
    role_id = db.Column(db.Integer)
    account = db.Column(db.Integer)
    country = db.Column(db.String(50))
    city = db.Column(db.String(50))
    address = db.Column(db.String(50))
    phone_number = db.Column(db.Integer)
    gender = db.Column(db.String(50))
    marital_status = db.Column(db.String(50))


    def __repr__(self):
        return '<Users %r>'%self.id


# Create Courses table in DB
class Courses(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    body = db.Column(db.String(300), nullable=False)
    author = db.Column(db.Text, nullable=False)
    date_created = db.Column(db.DateTime, default=datetime.now())
    coursetype = db.Column(db.Text, nullable=False)
    price = db.Column(db.Float)

    def __repr__(self):
        return '<Courses %r>'%self.id

# Create Codes table in DB
class Codes(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(30), nullable=False)
    gen_code = db.Column(db.Integer)
    is_used = db.Column(db.String(300), nullable=False)

    def __repr__(self):
        return '<Codes %r>'%self.id

# Create User_Courses Table
class UserCourses(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, nullable=False)
    user_id = db.Column(db.Integer)

    def __repr__(self):
        return '<User_Courses %r>'%self.id

class UserLoginHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    login_date = db.Column(db.DateTime)
    logout_date = db.Column(db.DateTime)

    def __repr__(self):
        return '<UserTrack %r>'%self.id


class UserPayments(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    payment_amount = db.Column(db.Integer, nullable=False)
    payment_method = db.Column(db.String, nullable=False)
    payment_date = db.Column(db.DateTime)
    card_number = db.Column(db.Integer)
    exp_date = db.Column(db.DateTime)
    card_cvv = db.Column(db.String)

    def __repr__(self):
        return '<UserPayments %r>'%self.id

class UserImage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    image = db.Column(db.TEXT, nullable=False)
    filename = db.Column(db.String, nullable=False)
    username = db.Column(db.String)
    mimetype = db.Column(db.String)

    def __repr__(self):
        return '<UserImage %r>'%self.id

class RegisterForm(Form):

    name = StringField('Name', [validators.Length(min=1, max=25)])  
    username = StringField('Username', [validators. Length(min=4, max=50), Regexp(r'^[A-Za-z]',message='Username should start with letters.')])
    email = StringField('Email', [validators.Length(min=6, max=50), Regexp(r"^\w+([-+.']\w+)*@\w+([-.]\w+)*\.\w+([-.]\w+)*$",message='Email format is not valid.')])
    password = PasswordField('Password', [validators.DataRequired(), validators.Length(min=8,max=14)])
    confirm = PasswordField('Confirm Password',  [validators.EqualTo('password', message='Password do not match!')])


class VerifyAccess(Form):
     
    email = StringField('Email', [validators.Length(min=6, max=50), Regexp(r"^\w+([-+.']\w+)*@\w+([-.]\w+)*\.\w+([-.]\w+)*$",message='Email format is not valid.')])
    code = StringField('Code', [validators.Length(min=1, max=15), Regexp(r"[0-9]+",message='Code format is not valid.')])


class Forgot(Form):
    email = StringField('Email', [validators.Length(min=6, max=50), Regexp(r"^\w+([-+.']\w+)*@\w+([-.]\w+)*\.\w+([-.]\w+)*$",message='Email format is not valid.')])


class Reset(Form):
    new_password = PasswordField('Password', [validators.DataRequired(), validators.Length(min=8,max=14)])
    code = StringField('Code', [validators. Length(7)])


class Calculator(Form):
    number1 = StringField('number1', [validators.Length(max=10), Regexp(r'^[-+]?\d*$', message='Field should accept only numbers')])
    number2 = StringField('number2', [validators.Length(max=10), Regexp(r'^[-+]?\d*$', message='Field should accept only numbers')])


class Blackbox(Form):
    name = StringField('name', [validators.Length(min=3, max=10), Regexp(r'[A-Za-z]', message='Only letters')])
    address = StringField('address', [validators.Length(max=50), Regexp(r'[A-Za-z0-9]', message='Address should be Alphanumeric')])
    phone = StringField('phone', [validators.Length(min=8, max=10), Regexp(r'^[1-9]*$', message='Phone Number should be only numbers')]) 


class Whitebox(Form):
    x_value = StringField('x_value', [validators.Length(min=1, max=10), Regexp(r"[0-9]+", message='Code format is not valid.')])
    y_value = StringField('y_value', [validators.Length(min=1, max=10), Regexp(r"[0-9]+", message='Code format is not valid.')])


class Account(Form):
    account_balance = StringField('Account')
    amount = StringField('Amount', [validators.DataRequired(), validators.Length(min=1, max=10), Regexp(r'^[0-9]*$', message='Amount shoud be numbers only')])


class Admin(Form):
    username = StringField('username')
    role = StringField('Role')


class CourseDiscount(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    coursetype = db.Column(db.Integer, nullable=False)
    discount = db.Column(db.Integer)
    course_count = db.Column(db.Integer)

    def __repr__(self):
        return '<Course_Discount %r>'%self.id

class Profile(Form):
    country = StringField('country', [validators.Length(min=3, max=50), Regexp(r'[A-Za-z]', message='Only letters')])
    city = StringField('city', [validators.Length(min=3, max=50), Regexp(r'[A-Za-z]', message='Only letters')])
    address = StringField('address', [validators.Length(min=3, max=50)])
    phone_number = StringField('phone_number', [Regexp(r'^[1-9]*$', message='Phone Number should be only numbers')]) 
    gender = StringField('gender')
    marital_status = StringField('marital_status')