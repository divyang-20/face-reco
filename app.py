from flask_mysqldb import MySQL, MySQLdb
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from flask import Flask, render_template, redirect, request, flash, url_for
import json
import os
import cv2
import face_recognition

app = Flask(__name__)

load_dotenv()

app.secret_key = os.getenv('SECRET_KEY')

app.config['MYSQL_HOST'] = os.getenv('HOST')
app.config['MYSQL_USER'] = os.getenv('USER')
app.config['MYSQL_PASSWORD'] = os.getenv('PASSWORD')
app.config['MYSQL_DB'] = os.getenv('DATABASE')
app.config['MYSQL_CURSORCLASS'] = os.getenv('CURSOR_CLASS')
mysql = MySQL(app)

UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

DB_FOLDER = os.getenv('DB_FOLDER')
app.config['DB_FOLDER'] = DB_FOLDER

ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif'])


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/')
def index():
    for file_name in os.listdir(UPLOAD_FOLDER):
        if allowed_file(file_name):
            file = UPLOAD_FOLDER + file_name
            os.remove(file)
    return render_template('index.html')


@app.route('/', methods=['POST'])
def upload():
    if 'file' not in request.files:
        flash('No file part')
        return redirect(request.url)
    file = request.files['file']
    if file.filename == '':
        flash('No image selected for uploading')
        return redirect(request.url)
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file.save(os.path.join(UPLOAD_FOLDER, filename))
        flash('Image successfully uploaded')
        return render_template('index.html', filename=filename)
    else:
        flash('Allowed images types are - png, jpg, jpeg, gif')
        return redirect(request.url)


@app.route('/display/<filename>')
def display_image(filename):
    return redirect(url_for('static', filename='uploads/' + filename), code=301)


@app.route('/match_image/<filename>')
def match_image(filename):
    msg = ""
    k = 0
    name = ""
    dob = ""
    file = ""

    imgDiv = face_recognition.load_image_file(UPLOAD_FOLDER + filename)
    imgDiv = cv2.cvtColor(imgDiv, cv2.COLOR_BGR2RGB)
    try:
        encodeDiv = face_recognition.face_encodings(imgDiv)[0]
    except IndexError as e:
        k = 2
        pass

    path = DB_FOLDER
    myList = os.listdir(path)

    if(k != 2):
        for cu_img in myList:
            imgTest = face_recognition.load_image_file(f'{path}/{cu_img}')
            imgTest = cv2.cvtColor(imgTest, cv2.COLOR_BGR2RGB)
            encodeTest = face_recognition.face_encodings(imgTest)[0]
            result = face_recognition.compare_faces([encodeDiv], encodeTest)
            if result[0]:
                file = cu_img
                fullname = os.path.splitext(file)[0]
                name = fullname.split('_')[0]
                dob = fullname.split('_')[1]
                msg = "MATCH FOUND!"
                k = 1
                break

    if k == 0:
        msg = "NO MATCH FOUND!"
    if k == 2:
        msg = "Couldn't recognise any face!"
    value = {
        "msg": msg,
        "name": name,
        "dob": dob,
        "file": file,
        "k": k
    }
    return json.dumps(value)


@app.route('/form')
def form():
    return render_template('form.html')


@app.route('/form', methods=['POST'])
def uploadinfo():
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    name = request.form["name"]
    description = request.form["description"]
    dob = request.form["dob"]
    gender = request.form["gender"]
    file = request.files["file"]

    filename = secure_filename(file.filename)
    ext = filename.rsplit('.', 1)[1].lower()
    renamedfilename = f"{name}_{dob}.{ext}"
    file.save(os.path.join(DB_FOLDER, filename))
    os.rename(f"{DB_FOLDER}{filename}", f"{DB_FOLDER}{renamedfilename}")
    cur.execute("INSERT INTO infos (name, description, dob, gender) VALUES (%s, %s, %s, %s)",
                (name, description, dob, gender))
    flash("Details uploaded successfully!")
    mysql.connection.commit()
    return redirect('/')


@app.route('/search', methods=['GET'])
def search():
    file = request.args.get('file')
    fullname = file.split('.')[0]
    name = fullname.split('_')[0]
    dob = fullname.split('_')[1]
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute("SELECT * FROM infos WHERE name = %s AND dob = %s", (name, dob))
    details = cur.fetchone()
    return render_template('search.html', details=details, file=file)


@app.route('/change', methods=['GET', 'POST'])
def change():
    user = request.args.get('user')
    fullname = user.split('.')[0]
    name = fullname.split('_')[0]
    dob = fullname.split('_')[1]
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    if request.method == 'GET':
        cur.execute(
            "SELECT * FROM infos WHERE name = %s AND dob = %s", (name, dob))
        details = cur.fetchone()
        return render_template('change.html', details=details, file=user)
    else:
        updescription = request.form["description"]
        cur.execute("UPDATE infos SET description = %s WHERE name = %s AND dob = %s",
                    (updescription, name, dob))
        flash('Details updated successfully!')
        mysql.connection.commit()
        return redirect('/')


if __name__ == '__main__':
    app.run(debug=True)
