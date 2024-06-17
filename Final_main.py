from flask import Flask, render_template, request, url_for, flash, redirect, send_from_directory, jsonify, send_file, make_response, session
from werkzeug.utils import secure_filename
import cv2
import os
import glob as glob
import psycopg2
from pdf2image import convert_from_path
import prediction_pr as pred
import Final_document_scanner as Scanner
import re
# import bcrypt
from psycopg2.extras import DictCursor
import secrets
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_mail import Mail, Message
from flask_bcrypt import Bcrypt
# from itsdangerous import URLSafeTimedSerializer as Serializer
from datetime import datetime
from itsdangerous import URLSafeTimedSerializer
import logging

app = Flask(__name__)

# postgresql database values
DATABASE_URL = ('postgres://root:iY2puGlcWGz8QMOe7NdICb6SJb1VDmWc@dpg-cod5k6a0si5c738pp810-a.oregon-postgres.render'
                '.com/visitingcard_details_4eui')

conn = psycopg2.connect(DATABASE_URL)

cur = conn.cursor()

# cur.execute('''CREATE TABLE IF NOT EXISTS user_data(id serial PRIMARY KEY, username varchar(255),
# email varchar(255), password varchar(255), confirm_password varchar(255));''')

# cur.execute('''CREATE TABLE IF NOT EXISTS visitingcard_data(id serial PRIMARY KEY, first_name varchar(255),
# last_name varchar(255),designation varchar(255), mobile_no INT, email varchar(255), website varchar(255));''')

# cur.execute('''ALTER TABLE data_blobs ALTER COLUMN data TYPE bytea''')

# # cur.execute('''ALTER TABLE visitingcard_data ALTER mobile_no TYPE bigint;''')

# cur.execute('''ALTER TABLE data_blobs AlTER event_time TYPE TIMESTAMPTZ;''')
# conn.commit()
# conn.close()
# cur.close()

app.secret_key = "my_secret_key"

app.config['SECRET_KEY'] = secrets.token_hex(24)
app.config['SECURITY_PASSWORD_SALT'] = secrets.token_hex(16)
app.config['MAIL_SERVER'] = 'smtp.googlemail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
# app.config['MAIL_USERNAME'] = os.environ.get('EMAIL_USER')
# app.config['MAIL_PASSWORD'] = os.environ.get('EMAIL_PASS')
app.config['MAIL_USERNAME'] = 'dipeshtate24@gmail.com'
app.config['MAIL_PASSWORD'] = 'yhyd aqhe iccz uryo'

mail = Mail(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'
bcrypt = Bcrypt(app)
s = URLSafeTimedSerializer(app.secret_key)

image_folder = "Image"
upload_folder = "Upload"
app.config['static_folder'] = 'static'
app.config['img_folder'] = 'img'
allowed_extension = {'jpeg', 'jpg', 'png', 'pdf'}

if not os.path.exists(image_folder):
    os.makedirs(image_folder)   # Check upload folder path is present or not

if not os.path.exists(upload_folder):
    os.makedirs(upload_folder)   # Check upload folder path is present or not


def allowed_type(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extension


# @app.route('/', methods=['POST', 'GET'])
# def home():
#     return render_template('main_page.html')

# new  /home
@app.route('/', methods=['POST', 'GET'])
@login_required
def homepage():
    cursor = conn.cursor()
    # user = get_current_user()
    if request.method == 'POST':
        if 'image' in request.files:
            image = request.files['image']
            if image.filename == '':
                print('Image name is not valid')
                return redirect(request.url)

            if not allowed_type(image.filename):
                flash("That image extension is not allowed", 'danger')
                return redirect(request.url)

            # Get the absolute path of the upload folder
            images_path = os.path.abspath(image_folder)

            # Get the list of files already in the upload folder
            image_files = os.listdir(images_path)

            file_count = 0
            while any(f'{file_count:03d}{ext}' in image_files for ext in ('.jpg', '.png', '.jpeg', 'pdf')):
                file_count += 1
            # Inside the loop (assuming it's a loop where you process multiple images)
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            filename = secure_filename(image.filename)
            filename, extension = os.path.splitext(filename)
            filename = f"{timestamp}{extension}"
            image.save(os.path.join(image_folder, filename))
            file_count += 1  # Increment the file_count after saving each image

            # Get the absolute path of the image folder
            image_path = os.path.abspath(image_folder)

            # Get the absolute path of the upload folder
            upload_path = os.path.abspath(upload_folder)

            # Get the list of files already in the upload folder
            existing_files = os.listdir(upload_path)

            image_counter = 0

            ts = 0
            found = None

            # Loop through each file in the image folder
            for filename in os.listdir(image_path):
                # Split the filename and extension
                name, extension = os.path.splitext(filename)
                file_extension = extension.lower()

                # If the file is a PDF, convert it to images
                if file_extension == '.pdf':
                    pdf_path = os.path.join(image_path, filename)
                    images = convert_from_path(pdf_path)
                    for image in images:
                        while f'{image_counter:03d}.jpg' in existing_files:
                            image_counter += 1
                        image_path = os.path.join(upload_path, f'{image_counter:03d}.jpg')
                        image.save(image_path)
                        image_counter += 1

                # If the file is an image, save it directly
                elif file_extension in {'.jpg', '.jpeg', '.png'}:
                    while f'{image_counter:03d}.jpg' in existing_files:
                        image_counter += 1

                for file_name in glob.glob(os.path.join(image_path, filename)):
                    fts = os.path.getmtime(file_name)
                    if fts > ts:
                        ts = fts
                        found = file_name
                print(found)
                # full_image_path = os.path.join(image_path, filename)
                # print(full_image_path)

                sharpened = Scanner.document_scanner(found)

                image_save_path = os.path.join(upload_path, f'{filename}.jpg')
                cv2.imwrite(image_save_path, sharpened)

                add_data = """INSERT INTO data_blobs(data, event_time) VALUES (%s,%s)"""
                # Read the binary data from the file and execute the statement
                for img_filename in os.listdir(upload_folder):
                    # Read the binary data from each file and execute the statement
                    with open(os.path.join(upload_folder, img_filename), "rb") as file:
                        binary_data = file.read()
                        # Use the current timestamp as event_time or define your own
                        time = datetime.now()
                        cursor.execute(add_data, (psycopg2.Binary(binary_data), time,))

                conn.commit()

                # we take list of image present in folder
                upload_list = os.listdir(upload_path)

                # Get the most recent image file
                if upload_list:
                    latest_upload_image = max(upload_list)
                    upload_url = url_for('get_file', filename=latest_upload_image)
                    return render_template('first_page.html', upload_url=upload_url)

    # return render_template('first_main_page.html')
    return render_template('first_page.html')


@app.route('/image/<filename>')
@login_required
def get_file(filename):
    return send_from_directory(upload_folder, filename)

#
# ###pending loop in not working properly and create repeat image also add doc_scanner
# @app.route('/extract', methods=['POST', 'GET'])
# def extract():
#     # Get the absolute path of the image folder
#     image_path = os.path.abspath(image_folder)
#
#     # Get the absolute path of the upload folder
#     upload_path = os.path.abspath(upload_folder)
#
#     # Get the list of files already in the upload folder
#     existing_files = os.listdir(upload_path)
#
#     image_counter = 0
#
#     # Loop through each file in the image folder
#     for filename in os.listdir(image_path):
#         # Split the filename and extension
#         name, extension = os.path.splitext(filename)
#         file_extension = extension.lower()
#
#         # If the file is a PDF, convert it to images
#         if file_extension == '.pdf':
#             pdf_path = os.path.join(image_path, filename)
#             images = convert_from_path(pdf_path)
#             for image in images:
#                 while f'{image_counter:03d}.jpg' in existing_files:
#                     image_counter += 1
#                 image_path = os.path.join(upload_path, f'{image_counter:03d}.jpg')
#                 image.save(image_path)
#                 image_counter += 1
#
#         # If the file is an image, save it directly
#         elif file_extension in {'.jpg', '.jpeg', '.png'}:
#             while f'{image_counter:03d}.jpg' in existing_files:
#                 image_counter += 1
#             full_image_path = os.path.join(image_path, filename)
#             image = Image.open(full_image_path)
#             new_image_path = os.path.join(upload_path, f'{image_counter:03d}.jpg')
#             image.convert('RGB').save(new_image_path)
#             image_counter += 1
#
#         # we take list of image present in folder
#         upload_list = os.listdir(upload_path)
#
#         # Get the most recent image file
#         if upload_list:
#             latest_upload_image = max(upload_list)
#             upload_url = url_for('image_file', filename=latest_upload_image)
#             return render_template('home.html', upload_url=upload_url)
#
#         return render_template('home.html')
#
#
# # Define the route to get the processed image
# @app.route('/image_file/<filename>')
# def image_file(filename):
#     return send_from_directory(upload_folder, filename)


@app.route('/fetch', methods=['POST', 'GET'])
@login_required
def fetch():
    # user = get_current_user()

    if request.method == 'POST':
        # Assuming you have the necessary imports and variables
        upload_path = os.path.abspath(upload_folder)
        images_list = os.listdir(upload_path)
        # print(images_list)
        table = {"First Name": [], "Last Name": [], "Designation": [], "Mobile Number": [], "Email": [], "Website": []}

        if images_list:
            file = os.path.join(upload_path, max(images_list))
            # print(file)
            img = cv2.imread(file)
            entities = pred.getpredictions(img)

            # Update table with extracted information
            table["First Name"].append(entities.get("First-NAME", ""))
            table["Last Name"].append(entities.get("Last-NAME", ""))
            table["Website"].append(entities.get("WEB", ""))
            table["Mobile Number"].append(entities.get("PHONE", ""))
            table["Designation"].append(entities.get("DESG", ""))

        # Extracting values from table
        first_name = ' '.join(table["First Name"][0]) if table["First Name"] else ""
        last_name = ' '.join(table["Last Name"][0]) if table["Last Name"] else ""
        designation = ' '.join(table["Designation"][0]) if table["Designation"] else ""
        mobile_no = ' '.join(table["Mobile Number"][0]) if table["Mobile Number"] else ""
        email = ' '.join(table["Email"][0]) if table["Email"] else ""
        website = ' '.join(table["Website"][0]) if table["Website"] else ""

        print(first_name, last_name, designation, mobile_no, email, website)
        # Render the template with extracted values
        return render_template('first_page.html', first_name=first_name, last_name=last_name, designation=designation,
                               mobile_no=mobile_no, email=email, website=website)

    # # Render the template without extracted values if no form submitted or GET request
    # return render_template('home.html', first_name="", last_name="", designation="",
    #                         mobile_no="", email="", website="")

    # return jsonify({
    #     "First Name": first_name,
    #     "Last Name": last_name,
    #     "Designation": designation,
    #     "Mobile Number": mobile_no,
    #     "Email": email,
    #     "Website": website
    # })


@app.route('/save', methods=['POST', 'GET'])
@login_required
def save():
    if request.method == 'POST':
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        designation = request.form['designation']
        mobile_no = re.sub(r'\s+', '', request.form['mobile_no'])
        email = request.form['email']
        website = request.form['website']

        # Check if any of the required fields are empty
        if not first_name and not last_name and not designation and not mobile_no and not email and not website:
            return render_template('first_page.html', message="Please Upload Image.")

        # Insert the data into the MySQL database
        cursor = conn.cursor()
        add_data = ("INSERT INTO visitingcard_data (first_name, last_name, designation, mobile_no, email, website) "
                    "VALUES (%s, %s, %s, %s, %s, %s)")
        cursor.execute(add_data, (first_name, last_name, designation, mobile_no, email, website))
        conn.commit()
        # return 'data successfully store'
    return redirect(url_for('index'))  # Redirect to the fetch route after saving the data


@app.route('/index', methods=['POST', 'GET'])
@login_required
def index():
    # user = get_current_user()
    cursor = conn.cursor()

    # id = "SELECT id FROM person_details ORDER BY id"
    # cur.execute(id)
    # id_num = [row[0] for row in cur.fetchall()]
    #
    # sequential = all(x == id_num[x] for i, x in enumerate(range(id_num[0],len(id_num)+id_num[0])))
    #
    # if not sequential:
    #     # Auto increment id value start from 1
    #     auto_increment = "ALTER TABLE person_details AUTO_INCREMENT = 1"
    #     cur.execute(auto_increment)
    #     mysql.connection.commit()
    #
    # #Fetch data from database
    # fetch_data = "SELECT * FROM person_details"
    # cur.execute(fetch_data)
    # data = cur.fetchall()
    # # for row in cur.fetchall():
    #     id_num.append(row[0])
    #     for x, i in enumerate(range(id_num[0],len(id_num))):
    #         if i == id_num[x]:
    #             return 'unsccessful'
    # return 'successful'
    tab = "SELECT * FROM visitingcard_data"
    cursor.execute(tab)
    data = cursor.fetchall()
    return render_template('table.html', visitingcard_details=data)

# @app.route('/insert', methods=['POST'])
# def insert():
#     if request.method == 'POST':
#         first_name = request.form["first_name"]
#         last_name = request.form["last_name"]
#         mob_no = request.form["mob_no"]
#         gmail_id = request.form["gmail_id"]
#         company_name = request.form["company_name"]
#         company_add = request.form["company_add"]
#
#         # Check for duplicate entry based on some criteria based on (e.g., mob_no and gmail_id)
#         cur = mysql.connection.cursor()
#         array = "SELECT id FROM person_details WHERE mob_no = %s OR gmail_id = %s"
#         cur.execute(array, (mob_no, gmail_id))
#         current_table = cur.fetchone()
#
#         if current_table:
#             flash('Duplicate entry. This record already exists.')
#         else:
#             # insert non-duplicate record
#             add = ("INSERT INTO person_details (first_name, last_name, mob_no, gmail_id, company_name, company_add) "
#                    "VALUES (%s, %s, %s, %s, %s, %s)")
#             cur.execute(add, (first_name, last_name, mob_no, gmail_id, company_name, company_add))
#             cur.connection.commit()
#             flash('Row inserted into the table successfully')
#         return redirect(url_for('index'))


@app.route('/edit/<string:id>', methods=['GET'])
@login_required
def edit(id):
    # user = get_current_user()
    cursor = conn.cursor()
    ed = "SELECT * FROM visitingcard_data WHERE id = %s"
    cursor.execute(ed, (id,))
    data = cursor.fetchall()
    # print(data)
    # return 'received'
    return render_template('update_details.html', visitingcard_details=data)


@app.route('/update', methods=['POST'])
@login_required
def update():
    if request.method == 'POST':
        id = request.form["id"]
        first_name = request.form["first_name"]
        last_name = request.form["last_name"]
        designation = request.form["designation"]
        mobile_no = request.form["mobile_no"]
        email = request.form["email"]
        website = request.form["website"]
        cursor = conn.cursor()
        ud = """UPDATE visitingcard_data SET First_name = %s, Last_name = %s, Designation = %s, Mobile_No = %s,
                Email = %s, Website = %s WHERE id = %s"""
        cursor.execute(ud, (first_name, last_name, designation, mobile_no, email, website, id))
        conn.commit()
        flash("Data update successfully",'success')
        return redirect(url_for('index'))


@app.route('/delete/<string:id>')
@login_required
def delete(id):
    cursor = conn.cursor()
    dl = "DELETE FROM visitingcard_data WHERE id=%s "
    cursor.execute(dl, (id,))
    conn.commit()
    flash("remove row from table successfully", 'success')
    return redirect(url_for('index'))


# new code
# Route to render the image gallery template
@app.route('/gallery', methods=['GET'])
# @login_required
def image_gallery():
    cursor = conn.cursor()
    img_query = "SELECT * FROM data_blobs"
    cursor.execute(img_query)
    data = cursor.fetchall()
    images_data = []

    # for index, image_data in enumerate(data):
    #     # Save the image to a file
    #     image_file_name = f"{index}.jpg"  # Use index as filename
    #     image_path = os.path.join(app.config['static_folder'], image_file_name)
    #
    #     # Create the directory if it doesn't exist
    #     os.makedirs(os.path.dirname(image_path), exist_ok=True)
    #
    #     with open(image_path, 'wb') as f:
    #         f.write(image_data['data'])
    #
    #     # Append the filename to the list of images_data
    #     images_data.append(image_file_name)
    #
    # return render_template('gallery.html', images_data=images_data, images=data)
    for index, image_data in enumerate(data):
        # Use a secure filename based on index
        image_id = image_data[0]
        image_file_name = secure_filename(f"{image_id}.jpg")
        image_path = os.path.join(app.config['static_folder'], image_file_name)

        # Create the directory if it doesn't exist
        os.makedirs(os.path.dirname(image_path), exist_ok=True)

        # Write the image data to the file if it doesn't already exist
        if not os.path.exists(image_path):
            with open(image_path, 'wb') as f:
                f.write(image_data[1])  # Access the 'data' field correctly

        # Append the filename to the list of images_data
        images_data.append({'id': image_id, 'filename': image_file_name})

    return render_template('gallery.html', images_data=images_data)


@app.route('/delete/<int:file_id>', methods=['POST'])
# @login_required
def delete_image(file_id):
    # user = get_current_user()

    try:
        cursor = conn.cursor()
        dl_img = "DELETE FROM data_blobs WHERE id=%s"
        cursor.execute(dl_img, (file_id,))
        # conn.commit()
        image_filename = cursor.fetchone()

        logging.debug(f"Fetched filename: {image_filename}")

        if image_filename and image_filename[0]:
            # Delete the image entry from the database
            dl_img = "DELETE FROM data_blobs WHERE id=%s"
            cursor.execute(dl_img, (file_id,))
            conn.commit()

            # Delete the image file from the static folder
            # image_filename = cursor.fetchone()
            #     if image_filename:
            image_path = os.path.join(app.config['static_folder'], image_filename[0])
            if os.path.exists(image_path):
                os.remove(image_path)
        flash("Image removed successfully", 'success')
        # else:
        #     flash("Image not found")
    except Exception as e:
        flash(f"Error occurred: {str(e)}")
    # finally:
    #     cursor.close()  # Close cursor to avoid potential resource leak
    return redirect(url_for('image_gallery'))

# Route to handle image deletion
# @app.route('/delete/<int:file_id>', methods=['POST'])
# def delete_image(file_id):
#     try:
#         cursor = conn.cursor()
#         dl_img = "DELETE FROM visitingcard_image WHERE id=%s"
#         cursor.execute(dl_img, (file_id,))
#         conn.commit()
#         flash("Image removed successfully")
#     except Exception as e:
#         flash(f"Error occurred: {str(e)}")
#     finally:
#         cur.close()  # Close cursor to avoid potential resource leak
#     return redirect(url_for('image_gallery'))


#  login and register part

# conn.cursor_factory = DictCursor
#
#
# def get_current_user():
#     user = None
#     if 'user' in session:
#         user = session['user']
#         cursor = conn.cursor()
#         user_cursor = cursor.execute("SELECT * from user_data WHERE username=%s", (user,))
#         user = user_cursor.fetchone()
#     return user
#
#
# @app.route('/register', methods=['POST', 'GET'])
# def register():
#     user = get_current_user()
#     # if request.method == 'GET':
#     #     return render_template('register.html')
#     # else:
#     #     username = request.form['username']
#     #     email = request.form['email']
#     #     password = request.form['password'].encode('utf-8')
#     #     confirm_password = request.form['confirm_password'].encode('utf-8')
#     #
#     #     if password != confirm_password:
#     #         return "Passwords do not match!"
#     #
#     #     hashed_password = bcrypt.generate_passwrod_hash(password)
#     #
#     #     cursor = conn.cursor()
#     #     useradd_data = """INSERT INTO user_data (username, email, password) VALUES (%s, %s, %s)"""
#     #     cursor.execute(useradd_data, (username, email, hashed_password,))
#     #     conn.commit()
#     #     return render_template('login_page.html')
#     if request.method == 'GET':
#         return render_template('register.html', user=user)
#     else:
#         username = request.form['username']
#         email = request.form['email']
#         password = request.form['password'].encode('utf-8')
#         confirm_password = request.form['confirm_password'].encode('utf-8')
#
#         if password != confirm_password:
#             return "Passwords do not match!"
#
#         hashed_password = bcrypt.hashpw(password, bcrypt.gensalt()).decode('utf-8')
#
#         cursor = conn.cursor()
#
#         # checking  for duplicate username in the database
#         user_cursor = cursor.execute("SELECT * from user_data WHERE username = %s", (username,))
#         existing_user = user_cursor.fetchone()
#
#         if existing_user:
#             register_error = "Username already taken, please select a different username."
#             return render_template('register.html', register_error=register_error)
#
#         useradd_data = """INSERT INTO user_data (username, email, password) VALUES (%s, %s, %s)"""
#         try:
#             cursor.execute(useradd_data, (username, email, hashed_password,))
#             conn.commit()
#         except psycopg2.Error as err:
#             conn.rollback()
#             return f"Error: {err}"
#
#         cursor.close()
#         return redirect(url_for('login'))
#
#
# @app.route('/login', methods=['POST', 'GET'])
# def login():
#     user = get_current_user()
#
#     if request.method == 'POST':
#         username = request.form['username']
#         password = request.form['password'].encode('utf-8')
#
#         cursor = conn.cursor()
#         cursor.execute('SELECT * FROM user_data WHERE username=%s', (username,))
#         user = cursor.fetchone()
#         cursor.close()
#
#         if len(user) > 0:
#             if bcrypt.hashpw(password, user["password"].encode('utf-8')) == user["password"].encode('utf-8'):
#                 session['user'] = user['username']
#                 flash("Login successful")
#                 return render_template('first_page.html')
#             else:
#                 return "Username and password do not match."
#         else:
#             return "Error: User not found."
#     else:
#         return render_template('login_page.html', user=user)
#
#     #     if len(user) > 0:
#     #         if  bcrypt.hashpw(password, user["password"].encode('utf-8')) == user["password"].encode('utf-8'):
#     #         # hashed_password = user["password"].encode('utf-8')
#     #         # if bcrypt.checkpw(password, hashed_password):
#     #             flash("Login successful")
#     #             return render_template('first_page.html')
#     #         else:
#     #             return "Error: Username and password do not match."
#     #     else:
#     #         return "Error: User not found."
#     # else:
#     #     return render_template('login_page.html')
#
#
# @app.route('/logout')
# def logout():
#     session.clear()
#     return render_template('first_page.html')


# @app.route('/forgot', methods=['POST', 'GET'])
# def forgot():
#     if request.method == 'POST':
#         email = request.form['email']
#         token = str(uuid.uuid4())
#         cursor = conn.cursor()
#         result = cur.execute("SELECT * FROM user_data WHERE email=%s", [email])
#
#
# def get_reset_token(self, expires_sec=3600):
#     s = Serializer(app.config['SECRET_KEY'], expires_sec)
#     return s.dumps({'user.id': self.id}.decode('utf-8'))
#
# @staticmethod
# def verify_reset_token(token):
#     s = Serializer(app.config['SECRET_KEY'])
#     try:
#         user_id = s.loads(token)
#     except:
#         return None
#     return User.query.get(user_id)
#
#
# def valiate_email(self, email):
#     user = User.query.filter_by(email=email.data).first()
#     if user is None:
#         raise ValidationError('There is no account with that email.You must register first')
#
#
# def send_reset_email(user):
#     token = user.get_reset_token()
#     msg = Message('Password Reset Request', sender='noreply@demo.com', recipients=[user.email])
#     msg.body = f'''To reset your password, visit the following link;
#    {url_for('reset_token', token=token, _external=True)}
#
#     If you did not make this request then simply ignore this email and no change.
# '''
#     mail.send(msg)
#
# @app.route('/reset_password', methods=['GET', 'POST'])
# def rest_request():
#     if current_user.is_authenticated:
#         return redirect(url_for('login'))
#     if form.validate_on_submit():
#         user = User.query.filter_by(email= email.data).first()
#         send_reset_email(user)
#         flash('An email has been sent with instructions to reset your password.', 'info')
#         return redirect(url_for('login'))
#     return render_template('reset_request.html', title='Reset Password')
#
#
# @app.route('/reset_password/<token>', methods=['GET', 'POST'])
# def rest_token(token):
#     if current_user.is_authenticated:
#         return redirect(url_for('login'))
#     user = User.verify_reset_token(token)
#     if user is None:
#         flash('that is an invalid or expired token', 'warning')
#         return redirect(url_for(rest_request))
#     if form.validate_on_submit():
#         hashed_password = bcrypt.hashpw(password, bcrypt.gensalt()).decode('utf-8')
#         user.password = hashed_password
#         cursor = conn.cursor()
#         useradd_data = """INSERT INTO user_data (username, email, password) VALUES (%s, %s, %s)"""
#         cursor.execute(useradd_data, (username, email, hashed_password,))
#         conn.commit()
#         flash('Your password has been update! You are now able to log in', 'success')
#         return redirect(url_for('login'))
#     return render_template('reset_token.html', title='Reset Password')


# class User(UserMixin):
#     def __init__(self, user_id, username, email):
#         self.id = user_id
#         self.name = username
#         self.email = email
#
#     @staticmethod
#     def get(user_id):
#         cursor = conn.cursor()
#         cursor.execute('SELECT username, email FROM user_data WHERE id=%s', (user_id,))
#         result = cursor.fetchone()
#         cursor.close()
#         if result:
#             return User(user_id, result[0], result[1])
#         return None
#
#     # @staticmethod
#     # def verify_reset_token(token):
#     #     s = URLSafeTimedSerializer(app.config['SECRET_KEY'])
#     #     try:
#     #         user_id = s.loads(token, salt=app.config['SECURITY_PASSWORD_SALT'], max_age=3600)['user_id']
#     #     except:
#     #         return None
#     #     cursor = conn.cursor()
#     #     cursor.execute("SELECT * FROM user_data WHERE id = %s", (user_id,))
#     #     user = cursor.fetchone()
#     #     cursor.close()
#     #     return user
#
#
# @login_manager.user_loader
# def load_user(user_id):
#     return User.get(user_id)
#
#
# @app.route('/login', methods=['GET', 'POST'])
# def login():
#     if request.method == 'POST':
#         email = request.form['email']
#         password = request.form['password'].encode('utf-8')
#
#         cursor = conn.cursor()
#         cursor.execute('SELECT id, username, email, password FROM user_data WHERE email=%s', (email,))
#         user_data = cursor.fetchone()
#         cursor.close()
#
#         if user_data and bcrypt.check_password_hash(user_data[3], password):
#             user = User(user_data[0], user_data[1], user_data[2])
#             login_user(user)
#             return redirect(url_for('homepage'))
#         else:
#             return render_template('login_page.html', error="Invalid email or password")
#
#     return render_template('login_page.html')
#
#
# @app.route('/register', methods=['GET', 'POST'])
# def register():
#     if request.method == 'POST':
#         username = request.form['username']
#         email = request.form['email']
#         password = request.form['password'].encode('utf-8')
#         # confirm_password = request.form['confirm_password'].encode('utf-8')
#
#         hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
#
#         cursor = conn.cursor()
#         try:
#             cursor = conn.cursor()
#
#             # checking for duplicate username in the database
#             cursor.execute("SELECT * from user_data WHERE username = %s", (username,))
#             existing_user = cursor.fetchone()
#
#             if existing_user:
#                 register_error = "Username already taken, please select a different username."
#                 return render_template('register.html', register_error=register_error)
#             else:
#
#                 useradd_data = """INSERT INTO user_data (username, email, password) VALUES (%s, %s, %s)"""
#                 cursor.execute(useradd_data, (username, email, hashed_password,))
#                 cursor.commit()
#                 return redirect(url_for('login'))
#         finally:
#             cursor.close()
#     return render_template('register.html')
#
#
# @app.route('/logout')
# @login_required
# def logout():
#     logout_user()
#     return redirect(url_for('login'))
#
#
# def get_reset_token(self, expires_sec=3600):
#     s = URLSafeTimedSerializer(app.config['SECRET_KEY'])
#     return s.dumps({'user_id': user_id}, salt=app.config['SECURITY_PASSWORD_SALT']).decode('utf-8')
#
#
# def verify_reset_token(token):
#     s = URLSafeTimedSerializer(app.config['SECRET_KEY'])
#     user_id = s.loads(token, salt=app.config['SECURITY_PASSWORD_SALT'], max_age=3600)['user_id']
#     cursor = conn.cursor()
#     cursor.execute("SELECT * FROM user_data WHERE id = %s", (user_id,))
#     user = cursor.fetchone()
#     cursor.close()
#     return user
#
#
# def send_reset_email(user):
#     token = get_reset_token(user[0])
#     msg = Message('Password Reset Request', sender='noreply@demo.com', recipients=[user.mail])
#     msg.body = f'''To reset your password, visit the following link:
#     {url_for('reset_token', token=token, _external=True)}
#     If you did not make this request then simply ignore this email and no change
#     '''
#     mail.send(msg)
#
#
# @app.route('/reset_password', methods=['GET', 'POST'])
# def reset_password():
#     if request.method == 'POST':
#         email = request.form['email']
#         cursor = conn.cursor()
#         cursor.execute("SELECT email FROM user_data WHERE email = %s", (email,))
#         user = cursor.fetchone()
#         cursor.close()
#
#         # cursor = conn.cursor()
#         # try:
#         #     cursor = conn.cursor()
#         #
#         #     # checking for duplicate username in the database
#         #     cursor.execute("SELECT * from user_data WHERE email = %s", (email,))
#         #     user = cursor.fetchone()
#
#         if user:
#             send_reset_email(user)
#             flash('An email has been sent with instruction to reset your password')
#             return redirect(url_for('login'))
#         else:
#             flash('Email not found!', 'danger')
#             return render_template('reset_password.html')
#         # finally:
#         #     cursor.close()
#     return render_template('reset_password.html', title='Reset Password')
#
#
# # def get_reset_token(self, expires_sec=3600):
# #     s = URLSafeTimedSerializer(app.config['SECRET_KEY'])
# #     return s.dumps({'user_id': self.id}).decode('utf-8')
# #
# #
# # def verify_reset_token(token):
# #     s = URLSafeTimedSerializer(app.config['SECRET_KEY'])
# #     try:
# #         user_id = s.loads(token, salt=app.config['SECURITY_PASSWORD_SALT'], max_age=3600)['user_id']
# #     except:
# #         return None
# #     cursor = conn.cursor()
# #     cursor.execute("SELECT * FROM user_data WHERE id = %s", (user_id,))
# #     user = cursor.fetchone()
# #     cursor.close()
# #     return user
# #
# # # @staticmethod
# # # def verify_reset_token(token):
# # #     s = URLSafeTimedSerializer(app.config['SECRET_KEY'])
# # #     try:
# # #         user_id = s.load(token)['user_id']
# # #     except:
# # #         return None
# # #     return User.query.get(user_id)
# #
# #
# # def send_reset_email(user):
# #     token = get_reset_token(user[0])
# #     msg = Message('Password Reset Request', sender='noreply@demo.com', recipients=[user.mail])
# #     msg.body = f'''To reset your password, visit the following link:
# #     {url_for('reset_token', token=token, _external=True)}
# #     If you did not make this request then simply ignore this email and no change
# #     '''
# #     mail.send(msg)
#
#
# @app.route('/reset_password/<token>', methods=['GET', 'POST'])
# def reset_token(token):
#     if current_user.is_authenticated:
#         return redirect(url_for('homepage'))
#
#     user = verify_reset_token(token)
#
#     if request.method == 'POST':
#         password = request.form['password']
#         confirm_password = request.form['confirm_password']
#
#         if password != confirm_password:
#             flash('Passwords do not match!', 'danger')
#             return render_template('reset_token.html', token=token, title='Reset Password')
#
#     # if user is None:
#     #     flash('That is a invalid or expired token', 'warning')
#     #     return redirect(url_for('reset_password'))
#     # password = request.form['password'].encode('utf-8')
#     # confirm_password = request.form['confirm_password'].encode('utf-8')
#     #
#     # if password != confirm_password:
#     #     return "Passwords do not match!"
#
#         hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
#
#         cursor = conn.cursor()
#
#         cursor.execute("UPDATE user_data SET password = %s WHERE id = %s", (hashed_password, user['id']))
#         conn.commit()
#         cursor.close()
#         flash('Your password has been update! You are now able to log in', 'sucess')
#         return redirect(url_for('login'))
#
#     return render_template('reset_token.html', title='Reset Password')

    #
    # try:
    #     email = s.loads(token, salt='email-confirm', max_age=3600)
    # except SignatureExpired:
    #     flash('The token is expired!', 'danger')
    #     return redirect(url_for('reset_password'))
    # except BadSignature:
    #     flash('Invalid token!', 'danger')
    #     return redirect(url_for('reset_password'))
    #
    # if request.method == 'POST':
    #     password = request.form['password']
    #     confirm_password = request.form['confirm_password']
    #
    #     if password != confirm_password:
    #         flash('Passwords do not match!', 'danger')
    #     else:
    #         hashed_password = bcrypt.generate_password_hash(password)
    #         cursor = conn.cursor()
    #         cursor.execute("UPDATE user_data SET password=%s WHERE email=%s", (hashed_password, email))
    #         conn.commit()
    #         cursor.close()
    #         flash('Your password has been reset!', 'success')
    #         return redirect(url_for('login'))
    #
    # return render_template('reset_token.html')

def email_validation(email):
    email_condition = r'^[a-z0-9]+[\._]?[a-z0-9]+[@]\w+[.]\w{2,3}$'

    if re.search(email_condition, email.lower()):
        return True
    else:
        return False


def password_validation(password):
    pwd_len = len(password)
    if pwd_len < 7 or pwd_len > 20:
        return False
    if not re.search('[A-Z]', password):
        return False
    if not re.search('[a-z]', password):
        return False
    if not re.search('[0-9]', password):
        return False
    if not re.search('[$#@!?]', password):
        return False
    if re.search('\s', password):
        return False
    return True


def confirm_password_validation(confirm_password):
    pwd_len = len(confirm_password)
    if pwd_len < 7 or pwd_len > 20:
        return False
    if not re.search('[A-Z]', confirm_password):
        return False
    if not re.search('[a-z]', confirm_password):
        return False
    if not re.search('[0-9]', confirm_password):
        return False
    if not re.search('[$#@!?]', confirm_password):
        return False
    if re.search('\s', confirm_password):
        return False
    return True


class User(UserMixin):
    def __init__(self, user_id, username, email):
        self.id = user_id
        self.name = username
        self.email = email

    @staticmethod
    def get(user_id):
        with conn.cursor() as cursor:
            cursor.execute('SELECT username, email FROM user_data WHERE id=%s', (user_id,))
            result = cursor.fetchone()
            if result:
                return User(user_id, result[0], result[1])
        return None


@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        with conn.cursor() as cursor:
            cursor.execute('SELECT id, username, email, password FROM user_data WHERE email=%s', (email,))
            user_data = cursor.fetchone()

        if user_data:
            if bcrypt.check_password_hash(user_data[3], password):
                user = User(user_data[0], user_data[1], user_data[2])
                login_user(user)
                session['loggedin'] = True
                session['user_id'] = user_data[0]
                session['username'] = user_data[1]
                session['email'] = user_data[2]
                return redirect(url_for('homepage'))
            else:
                flash("Invalid email or password", 'danger')
        else:
            flash("Email not registered. Please register first.", 'warning')

        return render_template('login_page.html')

    return render_template('login_page.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if not email_validation(email):
            flash('Invalid email address.', 'danger')
            return redirect(url_for('register'))

        if not password_validation(password):
            flash('Password must be 7-20 characters long, include an uppercase letter, '
                  'a lowercase letter, a number, and a special character, and must not contain spaces.', 'warning')
            return redirect(url_for('register'))

        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

        if password != confirm_password:
            flash("Passwords do not match.", 'danger')
            return redirect(url_for('register'))

        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM user_data WHERE username = %s", (username,))
            existing_user = cursor.fetchone()

            if existing_user:
                register_error = "Username already taken, please select a different username."
                return render_template('register.html', register_error=register_error)
            else:
                cursor.execute("INSERT INTO user_data (username, email, password) VALUES (%s, %s, %s)",
                               (username, email, hashed_password))
                conn.commit()
                flash('register account successfully', 'success')
                return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/logout')
@login_required
def logout():
    # logout_user()
    # return redirect(url_for('login'))
    logout_user()

    # Optionally, flash a message to the user
    flash('You have been logged out.', 'success')

    # Log the logout event
    logging.info('User logged out successfully.')

    # Redirect to the login page
    return redirect(url_for('login'))


# def get_reset_token(user_id, expires_sec=3600):
#     u = URLSafeTimedSerializer(app.config['SECRET_KEY'], expires_sec)
#     return s.dumps({'user_id': user_id}, salt=app.config['SECURITY_PASSWORD_SALT'])

def get_reset_token(user_id, expires_sec=3600):
    s = URLSafeTimedSerializer(app.config['SECRET_KEY'])
    return s.dumps({'user_id': user_id}, salt=app.config['SECURITY_PASSWORD_SALT'])


def verify_reset_token(token):
    s = URLSafeTimedSerializer(app.config['SECRET_KEY'])
    try:
        data = s.loads(token, salt=app.config['SECURITY_PASSWORD_SALT'], max_age=3600)
        user_id = data.get('user_id')

        # Validate that user_id is an integer
        if not isinstance(user_id, int):
            print(f"Invalid user_id type: {type(user_id)}")
            return None

    except Exception as e:
        print(f"Error decoding token: {e}")
        return None

    # Database query
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id, username, email FROM user_data WHERE id = %s", (user_id,))
            user = cursor.fetchone()
        return user if user else None

    except psycopg2.Error as db_error:
        print(f"Database error: {db_error}")
        return None


def send_reset_email(user):
    token = get_reset_token(user[0])
    msg = Message('Password Reset Request', sender='noreply@demo.com', recipients=[user[2]])
    msg.body = f'''To reset your password, visit the following link:
{url_for('reset_token', token=token, _external=True)}
If you did not make this request then simply ignore this email and no change will be made.
'''
    mail.send(msg)


@app.route('/reset_password', methods=['GET', 'POST'])
def reset_password():
    if request.method == 'POST':
        email = request.form['email']
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM user_data WHERE email = %s", (email,))
            user = cursor.fetchone()

            if user:
                send_reset_email(user)
                flash('An email has been sent with instructions to reset your password', 'info')
                return redirect(url_for('login'))
            else:
                flash('Email not found!', 'danger')

    return render_template('reset_password.html', title='Reset Password')


@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_token(token):
    if current_user.is_authenticated:
        return redirect(url_for('homepage'))

    user = verify_reset_token(token)
    # print(user[0])
    if user is None:
        flash('That is an invalid or expired token', 'warning')
        return render_template('reset_password.html')

    if request.method == 'POST':
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if not password_validation(password):
            flash('Password must be 7-20 characters long, include an uppercase letter, '
                  'a lowercase letter, a number, and a special character, and must not contain spaces.',
                  'warning')
            return render_template('reset_token.html', token=token, title='Reset Password')

        elif password != confirm_password:
            flash('Passwords do not match!', 'danger')
            return render_template('reset_token.html', token=token, title='Reset Password')

        # Hash the new password
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

        # try:
        cursor = conn.cursor()
        cursor.execute("UPDATE user_data SET password = %s WHERE id = %s", (hashed_password, user[0]))
        # Ensure user_id is defined
        conn.commit()

        flash('Your password has been updated! You are now able to log in', 'success')
        return redirect(url_for('login'))
        # except Exception as e:
        #     conn.rollback()
        #     flash('An error occurred. Please try again.', 'danger')
        #     return render_template('reset_token.html', token=token, title='Reset Password')

    return render_template('reset_token.html', token=token, title='Reset Password')


# @app.route("/account", methods=['GET', 'POST'])
# @login_required
# def account():
#     user_id = current_user.id
#     cursor = conn.cursor()
#     cursor.execute("SELECT username, email FROM user_data WHERE id = %s", (user_id,))
#     user_data = cursor.fetchone()
#
#     if user_data:
#         username, email = user_data
#
#         return render_template('edit_page.html', title='Account', username=username, email=email)
#
#
# @app.route("/account_update", methods=['GET', 'POST'])
# @login_required
# def account_update():
#     user_id = current_user.id
#     username = request.form.get('username')
#     email = request.form.get('email')
#     cursor = conn.cursor()
#     ud = """UPDATE user_data SET username = %s, Email = %s WHERE id = %s"""
#     cursor.execute(ud, (username, email, user_id))
#     conn.commit()
#     flash("Data update successfully")
#
#     return redirect(url_for('account'))

@app.route("/account", methods=['GET', 'POST'])
@login_required
def account():
    user_id = current_user.id
    cursor = conn.cursor()
    cursor.execute("SELECT username, email FROM user_data WHERE id = %s", (user_id,))
    user_data = cursor.fetchone()

    username = user_data[0] if user_data else ""
    email = user_data[1] if user_data else ""

    return render_template('edit_page.html', title='Account', username=username, email=email)


@app.route("/account_update", methods=['POST'])
@login_required
def account_update():
    # print("Form data received:", request.form)

    try:
        user_id = current_user.id
        username = request.form['username']
        email = request.form['email']
        # print(username, email)
        cursor = conn.cursor()
        cursor.execute("UPDATE user_data SET username = %s, email = %s WHERE id = %s", (username, email, user_id))
        conn.commit()

        flash("Data updated successfully", 'success')
        return redirect(url_for('account'))
    except KeyError as e:
        # Handle the KeyError if any form field is missing
        flash(f"Error: Missing form field {e.args[0]}")
        return redirect(url_for('account'))

    except Exception as e:
        # General exception handling
        flash(f"An error occurred: {str(e)}")
        return redirect(url_for('account'))


@app.route('/settings', methods=['GET'])
@login_required
def settings():
    user_id = current_user.id
    return render_template('setting.html', user_id=user_id)


@app.route('/delete_account', methods=['POST'])
@login_required
def delete_account():
    user_id = current_user.id

    try:
        cursor = conn.cursor()
        dl_acc = "DELETE FROM user_data WHERE id=%s"
        cursor.execute(dl_acc, (user_id,))
        conn.commit()
        cursor.close()

        flash('Account successfully deleted.', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'Account deletion failed: {str(e)}', 'danger')

    return redirect(url_for('login'))


@app.route('/back_to_homepage', methods=['POST', 'GET'])
def go_back_to_homepage():
    upload_path = os.path.abspath(upload_folder)
    image_paths = os.path.abspath(image_folder)

    try:
        for filename in os.listdir(upload_path):
            file_path = os.path.join(upload_path, filename)
            os.remove(file_path)
        for filename in os.listdir(image_paths):
            file_path = os.path.join(image_paths, filename)
            os.remove(file_path)
    except FileNotFoundError:
        return "File not found"

    return redirect(url_for("homepage"))


if __name__ == '__main__':
    app.run(debug=True)
