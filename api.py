from flask import make_response
from passlib.handlers.sha2_crypt import sha256_crypt
from functools import wraps
import jwt
from datetime import timedelta
from models import *
import time
from werkzeug.utils import secure_filename
from sqlalchemy.sql import text
from docxtpl import DocxTemplate
import jinja2
from datetime import datetime
import os
import ctypes
import requests
import matplotlib
import random
import string
import re


key =''.join(random.choices(string.ascii_uppercase +
                             string.digits, k = 10))
app.config['SECRET_KEY'] = key
api_key = '3d22940be1eb70fcfe47f0fc0de9a7fa'


matplotlib.use('Agg')

ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg'])

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def validate_email(email):
        pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
        if re.match(pattern, email):
            return True
        else:
            return False
        
# Check if user logged in
def is_logged_in_api(f):
    @wraps(f)
    def login_decorator(*args, **kwargs):
        token = None
        tries = 5
        time_1 = time.time()
        try:
            token = request.headers['Authorization'].split('Bearer')[1].strip()
            time.sleep(3)
        
        except:
            return jsonify({'message': 'Token is missing'}), 401
        try:
            while tries > 0 and (time.time() - time_1) > 3:
                jwt.decode(token, app.config['SECRET_KEY'], algorithms="HS256")
                tries = tries - 1
        except:
            return jsonify({'message': 'Invalid token'}), 401
        return f(*args, **kwargs)
    return login_decorator

def get_data_from_token(data='username'):
    token = request.headers['Authorization'].split(' ')[1]
    tries = 7
    time_1 = time.time()
    docode_token = None
    while tries > 0:
        docode_token = jwt.decode(token, app.config['SECRET_KEY'], algorithms="HS256")
        tries = tries - 1
    return docode_token[data]

# check if user is admin
def is_admin_api(f):
    @wraps(f)
    def admin_decorator(*args, **kwargs):
        token = request.headers['Authorization'].split('Bearer')[1].strip()
        data = jwt.decode(token, app.config['SECRET_KEY'], algorithms="HS256")
        if data['role'] != 1:
            return jsonify({'message': 'Unauthorized'}), 401
        return f(*args, **kwargs)

    return admin_decorator


# User login
@app.route('/login/api', methods=['POST'])
def login_api():
    if request.method == 'POST':
        try:
            data = request.get_json()
            username = data['username']
            password_candidate = data['password']
        except:

            auth = request.authorization
            # get form fields
            username = auth.username
            password_candidate = auth.password
        with open('creds.txt', 'w') as f:
            f.write(username)
            # get username from db
        result = Users.query.filter_by(username=username).first()
        if result and sha256_crypt.verify(password_candidate, result.password):
            token = jwt.encode({'username': username, 'id': result.id, 'role': result.role_id,
                                'exp': datetime.utcnow() + timedelta(minutes=30)}, \
                            app.config['SECRET_KEY'])
            return jsonify({'token': token, "role": result.role_id})
        else:
            return make_response('Could not Verify', 401, {'WWW-Authenticate': 'Basic realm=Login Required'})
    
    return render_template('login.html')



@app.route('/register/api', methods=['POST'])
def user_register_api():
    first_name = request.json['first_name']
    email = request.json['email']
    username = request.json['username']
    password = sha256_crypt.encrypt(request.json['password'])
    role_id = 2
    account = 100
    if any(value is None or value == '' for value in [first_name, username, email, password]):
        return jsonify({'message': 'Required data is missing'})
    if not validate_email(email):
        return jsonify({'message': 'Invalid email format'})
    # Create Users object
    new_user = Users(first_name=first_name, email=email, username=username, password=password, role_id=role_id,
                     account=account)
    existing_email = Users.query.filter_by(email=email).first()  # return top 1 email
    existing_username = Users.query.filter_by(username=username).first()  # return top 1 username

    if existing_email:
        return jsonify({'message': 'User with this email is already exists'})

    elif existing_username:
        return jsonify({'message': 'User with this username is already exists'})
    else:
        db.session.add(new_user)
        db.session.commit()
        result = Users.query.filter_by(username=username).first()
        session['logged_in'] = True
        return make_response({"message": "User is created", "user_id": result.id}, 201, )


class TaskSchema(ma.Schema):
    class Meta:
        fields = ('id', 'title')


task_schema = TaskSchema()
tasks_schema = TaskSchema(many=True)


# get advanced courses
@app.route('/courses/advanced/api')
@is_logged_in_api
def advanced_courses_api():
    count_result = Courses.query.filter_by(coursetype=2).count()
    courses = Courses.query.filter_by(coursetype=2).order_by(Courses.id.desc())
    result = tasks_schema.dump(courses)
    payload = {
        "count": count_result,
        "result": result
    }
    return jsonify(payload)


# get fundamental courses
@app.route('/courses/fundamental/api')
@is_logged_in_api
def fundamental_courses_api():
    count_result = Courses.query.filter_by(coursetype=1).count()
    courses = Courses.query.filter_by(coursetype=1).order_by(Courses.id.desc())

    result = tasks_schema.dump(courses)

    payload = {
        "count": count_result,
        "result": result

    }
    return jsonify(payload)


# add new article
@app.route('/add_course/api', methods=['POST'])
# @is_logged_in_api
# @is_admin_api
def add_course_api():
    if request.method == 'POST':
        data = request.get_json(force=True)

        title = data['title']
        body = data['body']
        coursetype = data['coursetype']
        price = data['price']
        try:
            author = session['username']
        except:
            author = 'Admin'

        new_course = Courses(title=title, body=body, coursetype=coursetype, price=price, author=author)
        if coursetype not in ("1", "2"):
            return (f"Course type should be 1 or 2")
        db.session.add(new_course)
        db.session.commit()
        print(new_course.id)
        data['id'] = str(new_course.id)
        return (data)

# add amount
@app.route('/add_account_balance/payment_api', methods=["POST"])
# @is_logged_in_api
def add_account_balance_api():

    tpl = DocxTemplate('Receipt_template.docx')
    card_number = None
    exp_date = None
    card_cvv = None
    if request.method == "POST":
        # get data form fields

        username_app = get_data_from_token()
        data = request.get_json(force=True)
        payment_method = data['payment']
        amount = int(data['amount'])
        if payment_method == 'Credit Card':
            card_number = data['card_num']
            exp_date = data['exp_date']
            card_cvv = data['card_cvv']
        if payment_method == '2' and (card_number == '' or exp_date == '' or card_cvv == ''):
            return jsonify({"message": "Card data is required"})
        elif amount < 0:
            return jsonify({"message": "Price should be positive"})
        db.session.execute(text(f'call Add_Payment("{username_app}", "{payment_method}", {amount}, "{card_number}", "{exp_date}", "{card_cvv}")'))
        balance = db.session.query(Users.account).filter_by(username=username_app).first()[0]
        if os.path.isfile('Receipt.docx'):
            os.remove('Receipt.docx')
        context = {
            "date": datetime.now(),
            "username": username_app,
            "amount": amount,
            "payment_method": payment_method,
            "account_balance": balance,
        }
        jinja_env = jinja2.Environment()
        tpl.render(context, jinja_env)
        tpl.save('Receipt.docx')
        return jsonify({"message": "Payment is done"})


# delete article

@app.route('/courses/course/<int:id>', methods=['DELETE'])
@is_logged_in_api
@is_admin_api
def course_delete_api(id):
    if request.method == 'DELETE':
        course = Courses.query.get_or_404(id)
        db.session.delete(course)
        db.session.commit()
        return (f"The course with id {id} is deleted")


# buy course
@app.route('/buy_course/api/<int:id>/<string:user>', methods=['POST'])
@is_logged_in_api
def buy_course_api(id, user):
    course = Courses.query.get(id)
    users = [user.user_id for user in UserCourses.query.filter_by(course_id=id)]
    user_id = db.session.query(Users.id).filter_by(username=user).first()[0]
    if user_id not in users:
        user_course = UserCourses(user_id=user_id, course_id=id)
        db.session.add(user_course)
        username = Users.query.filter_by(username=user).first()
        print(db.session.query(Users.account).filter_by(username=user).first()[0])
        print(course.price)
        username.account = db.session.query(Users.account).filter_by(username=user).first()[0] - course.price
        if username.account < 0:
            return ('Account Balance is insufficient')
        db.session.commit()
        return ('Successfully Done')
    else:
        return ('You already bought this course')


# get account balance
@app.route('/balance/balance_api', methods=['GET'])
# @is_logged_in_api
def get_user_balance():
    username = get_data_from_token()
    balance = db.session.query(Users.account).filter_by(username=username).first()[0]
    return jsonify({'balance': str(balance)})


@app.route('/course/<int:id>/update/', methods=["PATCH"])
@is_logged_in_api
@is_admin_api
def course_update_api(id):
    course = Courses.query.get(id)
    if request.method == "PATCH":
        course.title = request.json['title']
        course.body = request.json['body']
        try:
            db.session.commit()
            flash('Your changes are done', 'success')

            return (f"The course with id {id} is updated")

        except:
            return "Something went wrong"


# get user's courses tiotle and id
@app.route('/usercourses/api/<int:user_id>', methods=['GET'])
def user_courses_api(user_id):
    user_course_id = db.session.query(UserCourses.course_id).filter_by(user_id=user_id)
    result = [res[0] for res in user_course_id]
    courses_title = []
    courses_id = []
    for course_id in result:
        c_title = [courses.title for courses in Courses.query.filter_by(id=course_id)]
        c_id = [courses.id for courses in Courses.query.filter_by(id=course_id)]
        if len(c_title) > 0 and len(c_id) > 0:
            courses_title.append(c_title[0])
            courses_id.append(c_id[0])
    res = [{'title': title, 'id': id} for title, id in zip(courses_title, courses_id)]
    return (jsonify(res))


# get course price by id 
@app.route('/course_price/api/<int:id>', methods=['GET'])
def course_price_api(id):
    course_price = db.session.query(Courses.price).filter_by(id=id)
    result = [res[0] for res in course_price]
    payload = {"course_price": result[0]}

    return jsonify(payload)


# update user role
@app.route('/user_role/<string:username>', methods=["PATCH"])
def role_update_api(username):
    # user=Users.query.get(username)
    user = Users.query.filter_by(username=username).first()  # return firts row
    if request.method == "PATCH":
        user.role_id = request.json['role_id']
        try:
            db.session.commit()
            flash('Your changes are done', 'success')
            return (f"{username} user role is changed.")

        except:
            return "Update is failed!"


# get user role
@app.route('/get_user_role/<string:username>', methods=["GET"])
def get_role_update_api(username):
    user = Users.query.filter_by(username=username).first()  # return firts row
    payload = {"role_id": user.role_id}
    return jsonify(payload)


# set discount per course type(fundamental/advance)
@app.route('/set_discount/api', methods=['POST'])
def set_discount_api():
    if request.method == 'POST':
        data = request.get_json(force=True)
        course_type = data['course_type']
        discount = data['discount']
        course_count = data['course_count']

        if course_type == 'Fundamental':
            CourseDiscount.query.filter(CourseDiscount.coursetype == 1). \
                update({CourseDiscount.discount: discount, CourseDiscount.course_count: course_count})
        elif course_type == 'Advanced':
            CourseDiscount.query.filter(CourseDiscount.coursetype == 2). \
                update({CourseDiscount.discount: discount, CourseDiscount.course_count: course_count})
        db.session.commit()

        return jsonify({"message": f"{discount}% discount is set for {course_type} course type."})


@app.route('/file-upload/<string:username>/api', methods=['POST'])
def upload_file(username):
    # check if the post request has the file part
    if 'file' not in request.files:
        resp = jsonify({'message': 'No file part in the request'})
        resp.status_code = 400
        return resp
    file = request.files['file']
    if file.filename == '':
        resp = jsonify({'message': 'No file selected for uploading'})
        resp.status_code = 400
        return resp
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        mimetype = file.mimetype
        resp = jsonify({'message': f'{filename} File successfully uploaded'})
        resp.status_code = 201
        new_image = UserImage(username=username, image=file.read(), filename=filename, mimetype=mimetype)
        db.session.add(new_image)
        db.session.commit()
        return resp
    else:
        resp = jsonify({'message': 'Allowed file types are png, jpg, jpeg'})
        resp.status_code = 400
        return resp

@app.route('/file-delete/<string:username>/api', methods=['DELETE'])
def delete_file(username):
    # check if the post request has the file part
    if request.method == 'DELETE':
        UserImage.query.filter_by(username=username).delete()
        db.session.commit()
        return (f"The image(s) for {username} is deleted")
