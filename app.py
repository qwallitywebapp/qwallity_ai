import os
import random
import smtplib
import ssl
import string
from cgitb import text
from datetime import datetime, timedelta
from email.mime.multipart import MIMEBase, MIMEMultipart
from email.mime.text import MIMEText
from functools import wraps

from flask import (Flask, Response, flash, redirect, render_template, request,
                   send_file, session, url_for, send_from_directory)
from flask_mail import Mail, Message
from flask_mysqldb import MySQL
from flask_socketio import (SocketIO, SocketIOTestClient, emit, join_room,
                            leave_room)
from flask_swagger_ui import get_swaggerui_blueprint
from passlib.handlers.sha2_crypt import sha256_crypt
from PIL import Image
from sqlalchemy.sql import text
from werkzeug.utils import secure_filename
from wtforms import Form, StringField, TextAreaField, validators

import data_access
from api import *
from flask_session import Session
from models import *
import RAG_AI
import logging
import sys

#variables
admin = False

sess = Session()
UPLOAD_FOLDER = os.path.join(os.getcwd(), "static", "Upload")
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
app.config['SESSION_TYPE'] = 'filesystem'

socketio = SocketIO(app, allow_upgrades=False, cors_allowed_origins='*')
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logged_in_username = None
@app.before_request
def make_session_permanent():
    session.permanent = True
    global  logged_in_username
    with open('creds.txt', 'r') as file:
        logged_in_username = file.readline().strip()


def send_mail(email, subject, message_text):
    msg = MIMEMultipart()
    from_address = 'qwallityapp@gmail.com'
    msg['From'] = from_address
    msg['To'] = email
    msg['Subject'] = subject
    password = 'xcdiewpngtgftwff'
    body = message_text
    body = MIMEText(body) # convert the body to a MIME compatible string
    msg.attach(body)
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.ehlo()
    server.starttls()

    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.ehlo()
    server.starttls()
    server.login(from_address, password)
    server.sendmail(msg["From"], msg["To"], msg.as_string())
    flash('Secure code sent to your email.', 'success') 
    server.close()


port = 465  # For SSL

context = ssl.create_default_context()

SWAGGER_URL = '/swagger'
authorizations = '"Bearer": {"type": "Bearer Token", "in": "header", "name": "Authorization"}'
API_URL = '/static/swagger.json'
SWAGGER_BLUEPRINT = get_swaggerui_blueprint(
    SWAGGER_URL,
    API_URL,
    config={
        "app_name": "QwallityApp API"
    }
)
app.register_blueprint(blueprint=SWAGGER_BLUEPRINT, url_prefix=SWAGGER_URL, authorizations=authorizations)
key =''.join(random.choices(string.ascii_uppercase +
                             string.digits, k = 10))
app.config['SECRET_KEY'] = key
sess.init_app(app)
api_key = '3d22940be1eb70fcfe47f0fc0de9a7fa'

def mkdocs_route(path):
    def decorator(func):
        @app.route('/mkdocs/' + path)
        def wrapped(*args, **kwargs):
            return func(*args, **kwargs)
        return wrapped
    return decorator

@app.route('/docs')
def docs():
    return redirect('/mkdocs/home/index.html')

@app.route('/mkdocs/<path:path>')
@mkdocs_route('<path:path>')
def send_mkdocs(path):
    pages = ['home', 'login_page', 'registration_page', 'account_balance', 
             'course_actions', 'forget_password', 'login_tracking_page', 'print_receipt', 'profile_page', 'weather_page']
    site_path = os.path.join(os.getcwd(), "qwallity_app_doc-pkg", "site")
    for page in pages: 
        if page in request.path:
            path = f'{page}/index.html'
    return send_from_directory(site_path, path=path)


def is_logged_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        global logged_in_username  # Declare the variable as global
        try:
            with open('creds.txt', 'r') as file:
                logged_in_username = file.readline().strip()  # Read the first line and strip whitespace
            
            if logged_in_username:
                return f(*args, **kwargs)
        except Exception as e:
            flash('Unauthorized user. Please register or log in.', 'danger')
            return redirect(url_for('login'))
    
    return wrap

def is_verified(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'verified' in session:
            return f(*args, **kwargs)
        else:
            flash('Unauthorized', 'danger')
            return redirect(url_for('index'))
    return wrap


# About us page funtion
@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/python_code')
def python_code():
    return render_template('python_code.html')

@app.route('/', methods=['GET','POST'])
def index():
    form = VerifyAccess(request.form)
    if request.method == 'POST':
        email = form.email.data
        sec_code = form.code.data
        result = data_access.assign_code(email, sec_code)
        if result == 1:
            session['verified'] = True
            return redirect(url_for('home_index'))
        else:
            flash("You don't have access to Qwallity app, please contact administrator!", "danger")
    return render_template('verify_access.html', form=form)

@app.route('/upload', methods=['GET','POST'])
@is_logged_in
def upload():
    ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg'])
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('there is no file in form!')
        file = request.files['file']
        mimetype = file.mimetype
        filename = secure_filename(file.filename)
        if file.filename.rsplit('.', 1)[1].lower() not in ALLOWED_EXTENSIONS:
            flash('Allowed file types are png, jpg, jpeg', 'error')
        else:
            new_image = UserImage(username=username, image=file.read(), filename=filename, mimetype=mimetype)
            db.session.add(new_image)
            db.session.commit()
            flash('New Image uploaded', 'success')
    return render_template('upload.html')


@app.route('/upload/img', methods=['GET', 'POST'])
def get_iamge():
    img = UserImage.query.filter_by(username=username).order_by(UserImage.id.desc()).first()
    if not img:
        flash(f'No image found for {session["username"]} username')
        return render_template('upload.html')
    else:
        return Response(img.image, mimetype=img.mimetype)


@app.route('/receipt', methods=['GET', 'POST'])
def get_receipt():
    filename = "Receipt.docx"

    try:
        file_path = os.path.join(os.getcwd(),filename)
        return send_file(file_path, download_name='Receipt.docx')
    except:
         return render_template('user_action.html')
    
# User registration
@app.route('/register', methods=['GET','POST'])

def user_register():
    form=RegisterForm(request.form)

    if request.method == 'POST' and form.validate():
        first_name = form.name.data
        email = form.email.data
        username = form.username.data
        password = sha256_crypt.encrypt(str(form.password.data))
        role_id = 2
        account = 100
        #Create Users object
        new_user = Users(first_name=first_name, email=email, username=username, password=password, role_id=role_id, account=account)
        existing_email = Users.query.filter_by(email=email).first()            #return top 1 email
        existing_username = Users.query.filter_by(username=username).first()   #return top 1 username
        if existing_email:
            flash('User with this email is already exists', 'error')
            return (render_template('register.html', form=form))
            
        elif existing_username:    
            flash('User with this username is already exists', 'error')   
            return (render_template('register.html', form=form))         
        else:
            db.session.add(new_user)
            db.session.commit()
    
            flash('Your account has been successfully registered.', 'success')
            return redirect(url_for('login'))
    return(render_template('register.html', form=form))

@app.route('/login', methods=['GET', 'POST'])
def login():          
    if request.method == 'GET':
        return render_template('login.html')

    
@is_logged_in
def get_role():   
    try:
        role = Users.query.with_entities(Users.role_id).filter_by(username=logged_in_username).first()[0]
    except:
        print('user not found')
    return role   

@app.route('/user_action', methods=['Get', 'Post'])
@is_logged_in
def user_action():
    username = Users.query.filter_by(username=logged_in_username).first()
    form1 = Account(request.form)
    form1.account_balance.data = (db.session.query(Users.account).filter_by(username=logged_in_username)).first()[0]
    form2 = Admin(request.form)
    roles = ['admin', 'non_admin']
    return render_template('user_action.html', form1=form1)


@app.route('/user_action_admin', methods=['Get', 'Post'])
@is_logged_in
def user_action_admin():
    username = Users.query.filter_by(username=logged_in_username).first()
    form1 = Account(request.form)
    form2 = Admin(request.form)
    roles = ['admin', 'non_admin']

    if request.method == 'POST':
        if request.form.get('roles') == 'admin':
            Users.query.filter(Users.username == form2.username.data).\
            update({Users.role_id: 1})
        else:
            Users.query.filter(Users.username == form2.username.data).\
            update({Users.role_id: 2})
        db.session.commit()
        flash('Role is changed', 'success') 
        return render_template('user_action_admin.html', form2=form2, roles=roles)
    return render_template('user_action_admin.html', form2=form2, roles=roles)   
# Logout
@app.route('/logout')
def logout():
    user_id = db.session.query(Users.id).filter_by(username=logged_in_username).first()[0]
    user_action = UserLoginHistory.query.filter_by(user_id=user_id).order_by(UserLoginHistory.login_date.desc()).first()
    user_action.logout_date = datetime.now()
    db.session.commit()
    if os.path.isfile('Receipt.docx'):
        os.remove('Receipt.docx')
    session.clear()
    with open('creds.txt', 'w+') as f:
        f.write('')
    flash('You are now logged out', 'success')
    return redirect(url_for('login'))

# TODO mysql connection
@app.route('/profile', methods=['Get', 'Post'])
@is_logged_in
def profile():
    form=Profile(request.form)
    form.country.data = db.session.query(Users.country).filter_by(username=logged_in_username).first()[0] 
    form.city.data = db.session.query(Users.city).filter_by(username=logged_in_username).first()[0] 
    form.address.data = db.session.query(Users.address).filter_by(username=logged_in_username).first()[0] 
    form.phone_number.data = db.session.query(Users.phone_number).filter_by(username=logged_in_username).first()[0] 
    form.gender.data = db.session.query(Users.gender).filter_by(username=logged_in_username).first()[0] 
    form.marital_status.data = db.session.query(Users.marital_status).filter_by(username=logged_in_username).first()[0] 
    genders = ['male', 'female']
    marital_statuses = ['single', 'married', 'divorced']

    if request.method == 'POST':
        id = (db.session.query(Users.id).filter(Users.username==logged_in_username).first())[0]
        user=Users.query.get(id)
        user.country = request.form['country']
        user.city = request.form['city']
        user.address = request.form['address']
        user.phone_number = request.form['phone_number']
        user.gender = request.form['gender']
        user.marital_status = request.form['marital_status']
        try:
            db.session.commit()
            flash('Your changes are done.', 'success')
            return redirect(url_for('profile'))
        except:
            flash('Your changes are failed.', 'danger')

    return render_template('profile.html', form=form, genders=genders, marital_statuses=marital_statuses)  


# # TODO mongodb connection
# @app.route('/profile', methods=['Get', 'Post'])
# @is_logged_in
# @is_verified
# def profile():
#     form=Profile(request.form)
#     document = [i for i in db_mongo.Users.find({"username":session["username"]})]
#     form.country.data = document[0]["country"] 
#     form.city.data = document[0]["city"]
#     form.address.data = document[0]["address"]
#     form.phone_number.data = document[0]["phone_number"]
#     form.gender.data = document[0]["gender"]
#     form.marital_status.data = document[0]["marital_status"]
#     genders = ['male', 'female']
#     marital_statuses = ['single', 'married', 'divorced']

#     if request.method == 'POST':
#         id = document[0]["_id"]
#         try:
#             db_mongo.Users.update_one({"_id":id},{"$set":{
#             "country":request.form['country'],
#             "city":request.form['city'], 
#             "address":request.form['address'],
#             "phone_number":request.form['phone_number'],
#             "gender":request.form['gender'],
#             "marital_status":request.form['marital_status'],
#             }})

#             flash('Your changes are done.', 'success')
#             return redirect(url_for('profile'))
#         except:
#             flash('Your changes are failed.', 'danger')
#     return render_template('profile.html', form=form, genders=genders, marital_statuses=marital_statuses)  


#Homepage
@app.route('/home')
def home_index():
    courses = Courses.query.order_by(Courses.id.desc()).all()
    return render_template('home.html', courses=courses)

# -----------------------------------------------courses--------------------------------

# create course form
class courseForm(Form):
    title = StringField('Title', [validators.Length(min=1, max=200)])
    body = TextAreaField('Description')
    course_type = StringField('Type')
    price = StringField('Price')

# insert new course
    @app.route('/add_course', methods=['GET', 'POST'])
    def add_course():
#     form=courseForm(request.form)
#     # if request.method=='POST' and form.validate():
        
#     #     title       = form.title.data
#     #     body        = form.body.data
#     #     coursetype  = request.form.get('type')
#     #     price = form.price.data
#     #     new_course=Courses(title=title, body=body, coursetype=coursetype, author=username, price=price)
#     #     db.session.add(new_course)
#     #     db.session.commit()
#     #     return redirect(url_for('index'))

        return(render_template('add_course.html'))

# edit course page
@app.route('/edit_course/<string:id>', methods=['GET','POST'])
@is_logged_in
def edit_course(id):
    course = Courses.query.get(id)
    return (render_template("edit_course.html", course=course))

# update course details
@app.route('/course/<int:id>/update', methods=["POST","GET"])
def course_update(id):
    course = Courses.query.get(id)

    form = courseForm(request.form)
    form.title.data = (db.session.query(Courses.title).filter(Courses.id==id).first())[0]
    form.body.data = (db.session.query(Courses.body).filter(Courses.id==id).first())[0]

    if request.method == "POST":
        course.title = request.form['title']
        course.body = request.form['body']
        try:
            db.session.commit()
            flash('Your changes are done', 'success')
            
            return redirect('/courses') 
            
        except:
            return "Something went wrong"
    else:
        
        return(render_template("edit_course.html", form=form))

@app.route('/course/<int:id>/details')
def course_details(id):
    course = Courses.query.get(id)

    form = courseForm(request.form)
    form.title.data = (db.session.query(Courses.title).filter(Courses.id==id).first())[0]
    form.body.data = (db.session.query(Courses.body).filter(Courses.id==id).first())[0]

    return (render_template("course_details.html", form=form))
          

# delete course
@app.route('/course/<int:id>/delete')
def course_delete(id):
    course = Courses.query.get_or_404(id)
    db.session.delete(course)
    db.session.commit()
    flash('Course is deleted', 'success')
    return redirect('/courses')


# get article detail
@app.route('/courses/course/<int:id>', methods=['GET', 'POST'])
def art_detail(id):
    course = Courses.query.get(id)
    users = [user.user_id for user in UserCourses.query.filter_by(course_id=id)]
    user_id = db.session.query(Users.id).filter_by(username=logged_in_username).first()[0]
    if get_role() == 1:
        return(render_template("art_details.html", course=course))
    elif get_role() == 2 and request.method == 'POST' or user_id in users:
        if request.method == 'POST':
            user_course = UserCourses(user_id=user_id, course_id=id)
            db.session.add(user_course)
            username = Users.query.filter_by(username=logged_in_username).first()
            username.account = db.session.query(Users.account).filter_by(username=logged_in_username).first()[0] - course.price
            if username.account < 0:
                flash('Account balance insufficient ', 'error')
                return (render_template("art_details_nonadmin.html", course=course))
            try:
                db.session.commit()
            except Exception as e:
                db.session.rollback()  # Rollback changes if commit fails
                flash('Error occurred while updating the account: {}'.format(str(e)), 'error')
                return render_template("art_details_nonadmin.html", course=course)
      
        return redirect(url_for('my_courses'))
    else:
        return (render_template("art_details_nonadmin.html", course=course))

# display all courses in courses page
@app.route('/courses')
def courses():
    return render_template('courses.html')

# foundamental courses page
@app.route('/courses/fundamental')
@is_logged_in
def fundamental_courses():
    user_id = db.session.query(Users.id).filter_by(username=logged_in_username).first()[0]
    courses = db.session.execute(text(f'call Get_Fundamental_Courses({user_id})'))
    if get_role() == 2:

        return render_template('fundamental_courses.html', courses=courses)
    else:
        return render_template('fundamental_courses_admin.html', courses=courses)



@app.route('/mycourses')
@is_logged_in
def my_courses():
    user_id = db.session.query(Users.id).filter_by(username=logged_in_username)[0][0]
    courses = db.session.execute(text(f'call Get_User_Courses({user_id})'))
    return render_template('my_courses.html', courses=courses)


# advanced courses page
@app.route('/courses/advanced')
@is_logged_in
def advanced_courses():
    user_id = db.session.query(Users.id).filter_by(username=logged_in_username).first()[0]
    courses = db.session.execute(text(f'call Get_Advanced_Courses({user_id})'))
    if get_role()==2:
        return render_template('advanced_courses.html', courses=courses)
    else:
        return render_template('advanced_courses_admin.html', courses=courses)

# display course by id
@app.route('/courses/course/<int:id>')
def course_detail(id):
    course = Courses.query.get(id)
    return (render_template("course.html", course=course))



@app.route('/sendmail', methods=["POST","GET"])
def send_pass():
    form = Forgot(request.form)
    existing_email=Users.query.filter_by(email=form.email.data).first() 
    if request.method == 'POST' and form.validate():
        if existing_email:
            code = ''.join(random.choice(string.digits) for i in range(7))
            send_mail(form.email.data, 'Verification_code', code)
            flash('Secure code sent to your email.', 'success') 
            new_code = Codes(email=form.email.data, gen_code=code, is_used=0)
            db.session.add(new_code)
            db.session.commit()
        else:
            flash('Email is not registered, try registered email', 'error')
    return render_template('sendmail.html', form=form)


@app.route('/resetpass', methods=["POST","GET"])
def reset_pass():
    form = Reset(request.form)
    if request.method == 'POST' and form.validate():
        users = Users.query.get(id)
        try:
            code_usage = Codes.query.with_entities(Codes.is_used).filter_by(gen_code=form.code.data).first()[0]
            code_email = Codes.query.with_entities(Codes.email).filter_by(gen_code=form.code.data).first()[0]
            if code_usage == 0:
                Codes.query.filter(Codes.gen_code==form.code.data).\
                update({Codes.is_used: 1}, synchronize_session=False)
                Users.query.filter(Users.email==code_email).\
                update({Users.password:sha256_crypt.encrypt(str(form.new_password.data)) })
                db.session.commit()
                flash('Your password is changed', 'success') 
            else:
                flash('Code is expired', 'error')
        except:
            flash('Code is not valid', 'error')
    return render_template('resetpass.html', form=form)

    
# After each request check response, if response is 404, redirect to main page
@app.after_request
def after_request_func(response):
    response_code=response.status_code
    if response_code==404:
        url_list=request.url.split('/')
        redirect_url=url_list[0]+'//'+url_list[2]+'/'+url_list[-1]
        return redirect(redirect_url)
 
    return response

@app.after_request
def add_header(r):
    """
    Add headers to both force latest IE rendering engine or Chrome Frame,
    and also to cache the rendered page for 10 minutes.
    """
    r.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    r.headers["Pragma"] = "no-cache"
    r.headers["Expires"] = "0"
    r.headers['Cache-Control'] = 'public, max-age=0'
    return r
@app.route('/calculator', methods=["POST","GET"])
def calculate():
    form = Calculator(request.form)
    output=0
    thing = ''
    if request.method=='POST' and form.validate():
        if request.form.get('Calculate'):
            thing = request.form.get('thing','')
            number1 = form.number1.data if form.number1.data else '0'
            number2 = form.number2.data if form.number2.data else '0'
            num1     = float(number1.replace(',','.'))
            num2     = float(number2.replace(',','.'))
            if request.form.get('thing')=='addition':
                output=num1+num2
            elif request.form.get('thing')=='subtraction':
                 output=num1-num2
            elif request.form.get('thing')=='multiplication':
                if num1==0 or num2==0:
                    output == 0
                else:
                    output=num1*num2           
            elif request.form.get('thing')=='division':
                if num2==0:
                    flash('Can not devide by zero', 'danger')
                elif  num1==0:
                    output == 0.0
                else:
                    output=float(num1/num2)
        elif request.form.get('Reset'):
            form.number1.data = 0
            form.number2.data = 0
    return render_template('calculator.html', form=form, output=output, thing=thing)

@app.route('/exercises')
def exercises():
    return render_template('exercises.html')

@app.route('/blackbox', methods=["POST","GET"])
def blackbox():
    form = Blackbox(request.form)
    if request.method=='POST' :
        if request.form.get('Reset'):
            form.name.data = ''
            form.address.data = ''
            form.phone.data = ''
        elif request.form.get('Check') and form.validate():
            flash('Information is correct', 'success')              
    return render_template('blackbox.html', form=form)

@app.route('/whitebox', methods=["POST","GET"])
def whitebox():
    form = Calculator(request.form)
    output=0
    thing = ''
    if request.method=='POST' and form.validate():
        if request.form.get('Calculate'):
            thing = request.form.get('thing','')
            number1 = form.number1.data if form.number1.data!='' else '0'
            number2 = form.number2.data if form.number2.data!='' else '0'
            num1 = float(number1.replace(',','.'))
            num2 = float(number2.replace(',','.'))
            if request.form.get('thing')=='addition':
                output=num1+num2
            elif request.form.get('thing')=='subtraction':
                 output=num1-num2
            elif request.form.get('thing')=='multiplication':
                if num1==0 or num2==0:
                    output == 0
                else:
                    output=num1*num2           
            elif request.form.get('thing')=='division':
                if num2==0:
                    flash('Can not devide by zero', 'danger')
                elif  num1==0:
                    output == 0.0
                else:
                    output=float(num1/num2)
        elif request.form.get('Reset'):
            form.number1.data = 0
            form.number2.data = 0
    return render_template('whitebox.html', form=form, output=output, thing=thing)


@app.route('/chat_room', methods=['GET', 'POST'])
def chat_room():
    return render_template('chat_room.html')    



@app.route('/weather', methods=['GET', 'POST'])
def get_weather():
    return render_template('weather.html')

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    user_message = data.get('message')
    user_prompt = data.get('systemPromptInput', '')  # optional prompt, default empty string

    if not user_message:
        return jsonify({'error': 'No message provided'}), 400

    # Call generate_answer with separate question and user_prompt arguments
    answer = RAG_AI.generate_answer(user_message, user_prompt)

    return jsonify({'answer': answer})

if __name__=='__main__':
    with app.app_context():
        db.create_all()
    app.secret_key='secret'
    app.run()
    app.logger.info("testttttttttttttttttttttttttttttttttttttttttttttttt")
    socketio.run(app)

