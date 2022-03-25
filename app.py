#Importing packages
from flask import Flask, jsonify, render_template, request, redirect, url_for, flash, session
import os
import ast
import shutil
from datetime import datetime
from keras.models import load_model
from keras.preprocessing import image
import numpy as np
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow


app = Flask(__name__)

# Configuring useful resources, db and folders
image_folder = os.path.join('./static', 'images/')
app.config["UPLOAD_FOLDER"] = image_folder
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///Diagnosis.sqlite3'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = "1111"

#Loading the model
model = load_model('./static/models/My_best_model_by_inno_using_resnet101.h5')

# Creating the database and Marshmallow Object
db = SQLAlchemy(app)
ma = Marshmallow(app)

# Databases
class Radiologists(db.Model):
	id_ = db.Column(db.Integer, primary_key=True)
	doctor_id = db.Column(db.String(100))
	full_name = db.Column(db.String(100))
	password = db.Column(db.String(100))
	"""docstring for Users"""
	def __init__(self, doctor_id, full_name, password):
		self.full_name = full_name
		self.doctor_id = doctor_id
		self.password = password

	def __repr__(self):
		return f"Radiologists({self.full_name}, {self.doctor_id})"


class Diagnosis(db.Model):
	_id = db.Column(db.Integer, primary_key=True)
	patient_id = db.Column(db.Integer, unique=True)
	name = db.Column(db.String(100))
	conditions = db.Column(db.Text(200))
	image = db.Column(db.String(20))
	date_diagnosed = db.Column(db.String(20), default=datetime.now().strftime("%d/%m/%Y %H:%M"))
	test_results = db.Column(db.String(20))
	status = db.Column(db.String(20))

	"""docstring for Diagnosis"""
	def __init__(self, patient_id, name, conditions, image, test_results, status, date_diagnosed=datetime.now().strftime("%d/%m/%Y %H:%M")):
		self.patient_id = patient_id
		self.name = name
		self.conditions = conditions
		self.image = image
		self.date_diagnosed = date_diagnosed
		self.test_results = test_results
		self.status = status

	def __repr__(self):
		return f'Diagnosis {self.patient_id} {self.name}'


class DiagnosisSchema(ma.Schema):
	"""docstring for Diagnosis"""
	class Meta:
		"""docstring for Meta"""
		fields = ("_id", "patient_id", "name", "conditions", "image", "date_diagnosed", "test_results", "status")

class RadiologistsSchema(ma.Schema):
	"""docstring for RadiologistsSchema"""
	class Meta:
		"""docstring for Meta"""
		fields = ("id_", "doctor_id", "full_name", )

db.create_all()
session = session
session_ = db.session()
diagnosis_schema = DiagnosisSchema()
diagnosis_schemas = DiagnosisSchema(many=True)
radiologist_schema = RadiologistsSchema()

 # Views
@app.route('/dashboard', methods=['GET', 'POST'])
def index():
	if request.method == 'POST':
		fullname = request.form.get('fullname')
		age = request.form.get('age')
		weight = request.form.get('weight')
		height = request.form.get('height')
		residency = request.form.get('residency')
		patient_id = request.form.get('patient_id')
		gender = request.form.get('gender')
		temperature = request.form.get('temperature')
		pressure = request.form.get('pressure')
		diabetes = request.form.get('diabetes')
		symptoms = request.form.getlist('symptoms')
		imagefile = request.files.get('imagefile')
		imagefile.save(image_folder + imagefile.filename)
		img = image.load_img(image_folder + imagefile.filename, target_size=(224,224,3))
		img = np.expand_dims(image.img_to_array(img), axis=0)
		predictions = model.predict(img)
		if len(predictions) == 1:
			conditions = str({"age": age,"temperature": temperature, "pressure": pressure, "diabetes": diabetes, "symptoms": symptoms})
			covid_proba = int(predictions[0][0]*100)
			normal_proba = int(predictions[0][1]*100)
			if covid_proba > normal_proba:
				infected = 'POSITIVE'
				if covid_proba >= 90 and covid_proba == 100:
					covid_proba = round((covid_proba + 90)/2)
					normal_proba = 100 - covid_proba
				else:
					normal_proba = 100 - covid_proba
			else:
				infected = 'NEGATIVE'
				if normal_proba >= 90 and normal_proba == 100:
					normal_proba = round((normal_proba + 90)/2)
					covid_proba = 100 - normal_proba
				else:
					covid_proba = 100 - normal_proba
			diagnosis = Diagnosis(int(patient_id), fullname, conditions, imagefile.filename, str({"Covid": covid_proba, "Normal": normal_proba}), infected)
			session_.add(diagnosis)
			session_.commit()
			status = 200
		else:
			status = ""
		return render_template('full.html', status=status, diagnosis_={"name": fullname, "age": age, "patientid": patient_id, \
			"temperature": temperature, "pressure": pressure, "diabetes": diabetes, "imagefile": url_for('static', filename='images/' + imagefile.filename), \
			"date_diagnosed": datetime.now().strftime("%d/%m/%Y %H:%M").split(" ")[0], "status": infected, "results":[covid_proba, normal_proba]})
	if "doctor_id" in session:
		doctor_id = session["doctor_id"]
		radiologist = Radiologists.query.filter_by(doctor_id=doctor_id).first()
		return render_template('full.html', user=radiologist.full_name)
	return redirect('/')

@app.route('/get/<int:pid>', methods=['GET'])
def get(pid):
	patient = session_.query(Diagnosis).filter_by(patient_id=pid).first()
	if patient:
		return jsonify({"status": patient.status})
	return jsonify({"Not": "Found"})

@app.route('/delete', methods=['GET'])
def delete():
	users = Diagnosis.query.all()
	for user in users:
		current_db_session = session_.object_session(user)
		current_db_session.delete(user)
	current_db_session.commit()
	return jsonify({"deleted": "!"})

@app.route('/records/<int:pid>', methods=['GET'])
def details(pid):
	patient_details = Diagnosis.query.filter_by(patient_id=int(pid)).first()
	if patient_details:
		return render_template("patient_details.html", details={"patient_name": patient_details.name, "patient_id":patient_details.patient_id, \
			"conditions": ast.literal_eval(patient_details.conditions), "date": patient_details.date_diagnosed.split(" ")[0], \
			"image": patient_details.image, "results": ast.literal_eval(patient_details.test_results), "status": patient_details.status})
	return jsonify({"":""})

@app.route('/update/<int:pid>', methods=['GET', 'POST'])
def update(pid):
	patient_details = Diagnosis.query.filter_by(patient_id=int(pid)).first()
	if patient_details:
		if request.method == 'POST':
			fullname = request.form.get('fullname')
			age = request.form.get('age')
			weight = request.form.get('weight')
			height = request.form.get('height')
			residency = request.form.get('residency')
			patient_id = request.form.get('patient_id')
			gender = request.form.get('gender')
			temperature = request.form.get('temperature')
			pressure = request.form.get('pressure')
			diabetes = request.form.get('diabetes')
			symptoms = request.form.getlist('symptoms')
			imagefile = request.files.get('imagefile')
			imagefile.save(image_folder + imagefile.filename)
			img = image.load_img(image_folder + imagefile.filename, target_size=(224,224,3))
			img = np.expand_dims(image.img_to_array(img), axis=0)
			predictions = model.predict(img)
			if len(predictions) == 1:
				conditions = str({"age": age,"temperature": temperature, "pressure": pressure, "diabetes": diabetes, "symptoms": symptoms})
				covid_proba = int(predictions[0][0]*100)
				normal_proba = int(predictions[0][1]*100)
				if covid_proba > normal_proba:
					infected = 'POSITIVE'
					if covid_proba >= 90 and covid_proba == 100:
						covid_proba = round((covid_proba + 90)/2)
						normal_proba = 100 - covid_proba
					else:
						normal_proba = 100 - covid_proba
				else:
					infected = 'NEGATIVE'
					if normal_proba >= 90 and normal_proba == 100:
						normal_proba = round((normal_proba + 90)/2)
						covid_proba = 100 - normal_proba
					else:
						covid_proba = 100 - normal_proba
				# patient_details.name = fullname
				# patient_details.patient_id = int(patient_id)
				# patient_details.conditions = conditions
				# patient_details.image = imagefile.filename
				# patient_details.date_diagnosed = datetime.now().strftime("%d/%m/%Y %H:%M")
				# patient_details.test_results = str({"Covid": covid_proba, "Normal": normal_proba})
				# patient_details.status = infected
				updates = Diagnosis.query.filter_by(patient_id=patient_id).update({Diagnosis.image: imagefile.filename, \
					Diagnosis.conditions: conditions, Diagnosis.date_diagnosed: datetime.now().strftime("%d/%m/%Y %H:%M"), \
					Diagnosis.test_results: str({"Covid": covid_proba, "Normal": normal_proba}), Diagnosis.status: infected}, synchronize_session = 'fetch')
				if updates:
					# current_db_session = session_.object_session(update_user)
					# current_db_session.update({Diagnosis.image: imagefile.filename, \
					# Diagnosis.conditions: conditions, Diagnosis.date_diagnosed: datetime.now().strftime("%d/%m/%Y %H:%M"), \
					# Diagnosis.test_results: str({"Covid": covid_proba, "Normal": normal_proba}), Diagnosis.status: infected})
					session_.commit()
					print(f"successfully updated!! {Diagnosis.query.filter_by(patient_id=patient_id).first().status}")
					global global_updates
					global_updates = Diagnosis.query.all()
					print(global_updates[0].status)
					status = 200
				else:
					status = ""
			else:
				status = ""
			return render_template("update.html", status=status, diagnosis_={"name": fullname, "age": age, "patientid": patient_id, \
				"temperature": temperature, "pressure": pressure, "diabetes": diabetes, "imagefile": url_for('static', filename='images/' + imagefile.filename), \
				"date_diagnosed": datetime.now().strftime("%d/%m/%Y %H:%M").split(" ")[0], "status": infected, "results":[covid_proba, normal_proba]}, \
				values={"pid":patient_details.patient_id, "name": patient_details.name, "conditions": ast.literal_eval(patient_details.conditions), \
				"residency": "Moshi", "weight": 112, "height": 33})
		return render_template("update.html", values={"pid":patient_details.patient_id, "name": patient_details.name, \
			"conditions": ast.literal_eval(patient_details.conditions), "residency": "Moshi", "weight": 112, "height": 33})
	return jsonify({"Not": "Found"})

@app.route('/', methods=['GET'])
def home():
	global global_updates
	global_updates = []
	return render_template("homepage.html")

@app.route('/homepage', methods=['GET'])
def homepage():
	if "doctor_id" in session:
		doctor_id = session["doctor_id"]
		radiologist = Radiologists.query.filter_by(doctor_id=doctor_id).first()
		return render_template('homepage_1.html', user=radiologist.full_name)
	return redirect("/")

@app.route('/records', methods=['GET'])
def records():
	# records = Diagnosis.query.all()
	if "doctor_id" in session:
		if global_updates:
			records = global_updates
		else:
			records = Diagnosis.query.all()
		if records:
			print(records[0].status)
			records_obj = diagnosis_schemas.dump(records)
			return render_template("records.html", records=records_obj)
		return jsonify({"No": "records!"})
	return redirect('/')

@app.route('/reg', methods=['GET', 'POST'])
def register():
	if request.method == 'POST':
		fullname = request.form.get("fullname")
		doctor_id = request.form.get("doctorId")
		password = request.form.get("password")
		password_2 = request.form.get("password2")
		radiologist = Radiologists(doctor_id, fullname, password)
		session_.add(radiologist)
		session_.commit()
		return redirect("/login")
	return render_template("signup.html")

@app.route('/login', methods=['GET', 'POST'])
def login():
	if request.method == 'POST':
		doctor_id = request.form.get("doctorId")
		pass_word = request.form.get("password")
		radiologist = Radiologists.query.filter_by(doctor_id=doctor_id).first()
		if radiologist:
			session["doctor_id"] = doctor_id
			return redirect(url_for('homepage'))
		flash("You haven't registered!")
	return render_template("signin.html")

@app.route('/logout', methods=['GET'])
def logout():
	if "doctor_id" in session:
		session.pop("doctor_id")
		return redirect('/')
	return redirect('/')

if __name__ == "__main__":
    app.run(debug=True)