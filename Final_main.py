from flask import Flask, render_template, request, url_for, flash, redirect, send_from_directory, jsonify
from flask_mysqldb import MySQL
from werkzeug.utils import secure_filename
import cv2
# import pandas as pd
# import numpy as np
import pytesseract
import os
import re
import mysql.connector
from pdf2image import convert_from_path
from PIL import Image
import prediction_pr as pred
from Final_document_scanner import document_scanner
# import matplotlib.pyplot as plt
# import re

app = Flask(__name__)

mysql_connection = mysql.connector.connect(
                host='localhost',
                user='root',
                password='',
                database='crud'
)

app.secret_key = "my_secret_key"


image_folder = "Image"
upload_folder = "Upload"
allowed_extension = {'jpeg', 'jpg', 'png', 'pdf'}

if not os.path.exists(image_folder):
    os.makedirs(image_folder)   # Check upload folder path is present or not

if not os.path.exists(upload_folder):
    os.makedirs(upload_folder)   # Check upload folder path is present or not


def allowed_type(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extension


# @app.route('/', methods=['POST', 'GET'])
# def home():
#     return render_template('first_main_page.html')


@app.route('/', methods=['POST', 'GET'])
def homepage():
    if request.method == 'POST':
        if 'image' in request.files:
            image = request.files['image']
            if image.filename == '':
                print('Image name is not valid')
                return redirect(request.url)

            if not allowed_type(image.filename):
                print("That image extension is not allowed")
                return redirect(request.url)

            filename = secure_filename(image.filename)
            image.save(os.path.join(image_folder, filename))
            return render_template('home.html')

    # return render_template('first_main_page.html')
    return render_template('home.html')


@app.route('/image/<filename>')
def get_file(filename):
    return send_from_directory(upload_folder, filename)


@app.route('/extract', methods=['POST', 'GET'])
def extract():
        # abspath is used to complete path of the file in the system.

        image_path = os.path.abspath(image_folder)

        # Get the absolute path of the upload folder
        upload_path = os.path.abspath(upload_folder)

        # Get the list of files in the folder
        file_list = os.listdir(image_path)

        image_counter = 0

        for i, filename in enumerate(file_list):
            a = filename.rsplit('.', 1)
            file_extension = a[1].lower()

            if file_extension == 'pdf':
                images_path = os.path.join(image_path, filename)
                images = convert_from_path(images_path)
                for j, image in enumerate(images):
                    image_path = os.path.join(upload_path, f'{image_counter:03d}.jpg')
                    image.save(image_path)
                    image_counter += 1


            elif file_extension in {'jpg', 'jpeg', 'png'}:

                # Create the full path to the image file

                full_image_path = os.path.join(image_path, filename)

                # Load the image

                image = Image.open(full_image_path)

                # Convert and save to jpg

                new_image_path = os.path.join(upload_path, f'{image_counter:03d}.jpg')

                image.convert('RGB').save(new_image_path)

                image_counter += 1

        upload_path = os.path.abspath(upload_folder)

        upload_list = os.listdir(upload_path)

        # Get the most recent image file
        if upload_list:
            # Create a list of tuples containing (filename, modification time)
            file_mod_times = [(file, os.path.getmtime(os.path.join(upload_path, file))) for file in upload_list]
            # Sort the list based on modification time in descending order
            file_mod_times.sort(key=lambda x: x[1], reverse=True)

            # Iterate through the sorted list
            for filename, _ in file_mod_times:
                upload_url = url_for('image_file', filename=filename)
                return render_template('home.html', upload_url=upload_url)

        return render_template('home.html')


# Define the route to get the processed image
@app.route('/image_file/<filename>')
def image_file(filename):
    return send_from_directory(upload_folder, filename)


@app.route('/fetch', methods=['POST', 'GET'])
def fetch():
    upload_path = os.path.abspath(upload_folder)
    image_list = os.listdir(upload_path)

    table = {"First Name": [], "Last Name": [], "Designation": [], "Mobile Number": [], "Email": [], "Website": []}

    if image_list:
        file_mod_times = [(file, os.path.getmtime(os.path.join(upload_path, file))) for file in image_list]
        # Sort the list based on modification time
        file_mod_times.sort(key=lambda x: x[1], reverse=True)
        latest_image = file_mod_times[0][0]
        file = os.path.join(upload_path, latest_image)
        img = cv2.imread(file)
        entities = pred.getPredictions(img)

        table["First Name"].append(entities["First-NAME"])
        table["Last Name"].append(entities["Last-NAME"])
        table["Website"].append(entities["WEB"])
        table["Mobile Number"].append(entities['PHONE'])
        table["Designation"].append(entities['DESG'])

    # Assuming you have only one record from the image (based on your implementation)
    first_name = table["First Name"][0] if table["First Name"] else ""
    last_name = table["Last Name"][0] if table["Last Name"] else ""
    designation = table["Designation"][0] if table["Designation"] else ""
    mobile_no = table["Mobile Number"][0] if table["Mobile Number"] else ""
    email = table["Email"][0] if table["Email"] else ""
    website = table["Website"][0] if table["Website"] else ""

    return render_template('home.html', first_name=first_name, last_name=last_name, designation=designation,
                           mobile_no=mobile_no, email=email, website=website)
    # return jsonify({
    #     "First Name": first_name,
    #     "Last Name": last_name,
    #     "Designation": designation,
    #     "Mobile Number": mobile_no,
    #     "Email": email,
    #     "Website": website
    # })


@app.route('/save', methods=['POST', 'GET'])
def save():
    if request.method == 'POST':
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        designation = request.form['designation']
        mobile_no = request.form['mobile_no']
        email = request.form['email']
        website = request.form['website']

        # Insert the data into the MySQL database
        cursor = mysql_connection.cursor()
        add_data = ("INSERT INTO visitingcard_details (first_name, last_name, designation, mobile_no, email, website) "
                    "VALUES (%s, %s, %s, %s, %s, %s)")
        cursor.execute(add_data, (first_name, last_name, designation, mobile_no, email, website))
        mysql_connection.commit()
        # return 'data successfully store'
        return redirect(url_for('index'))  # Redirect to the fetch route after saving the data


@app.route('/index', methods=['POST', 'GET'])
def index():
    cur = mysql_connection.cursor()
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
    tab = "SELECT * FROM visitingcard_details"
    cur.execute(tab)
    data = cur.fetchall()
    return render_template('New.html', visitingcard_details=data)


#
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
#
#
@app.route('/edit/<string:id>', methods=['GET'])
def edit(id):
    cursor = mysql_connection.cursor()
    ed = "SELECT * FROM visitingcard_details WHERE id = %s"
    cursor.execute(ed, (id,))
    data = cursor.fetchall()
    # print(data)
    # return 'received'
    return render_template('update_details.html', visitingcard_details=data)


@app.route('/update', methods=['POST'])
def update():
    if request.method == 'POST':
        id = request.form["id"]
        first_name = request.form["first_name"]
        last_name = request.form["last_name"]
        designation = request.form["designation"]
        mobile_no = request.form["mobile_no"]
        email = request.form["email"]
        website = request.form["website"]
        cursor = mysql_connection.cursor()
        ud = """UPDATE visitingcard_details SET First_name = %s, Last_name = %s, Designation = %s, Mobile_No = %s, Email =
        %s, Website = %s WHERE id = %s"""
        cursor.execute(ud, (first_name, last_name, designation, mobile_no, email, website, id))
        mysql_connection.commit()
        flash("update data successfully")
        return redirect(url_for('index'))


@app.route('/delete/<string:id>')
def delete(id):
    cursor = mysql_connection.cursor()
    dl = "DELETE FROM visitingcard_details WHERE id=%s "
    cursor.execute(dl, (id,))
    mysql_connection.commit()
    flash("remove row from table successfully")
    return redirect(url_for('index'))


if __name__ == '__main__':
    app.run(debug=True)
