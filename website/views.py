import os
from werkzeug.security import generate_password_hash
from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user
from .models import Appointment, Doctor, User, Note
from . import db
import json
import pickle
from datetime import datetime
from werkzeug.security import check_password_hash
views = Blueprint('views', __name__)

# Load the machine learning model for heart disease prediction
with open('website/heartdiseaseprediction.pkl', 'rb') as f:
    model = pickle.load(f)

# Home Route
@views.route('/', methods=['GET', 'POST'])
@login_required
def home():
    if request.method == 'POST': 
        note = request.form.get('note')
        if len(note) < 1:
            flash('Note is too short!', category='error') 
        else:
            new_note = Note(data=note, user_id=current_user.id)
            db.session.add(new_note)
            db.session.commit()
            flash('Note added!', category='success')

    return render_template("home.html", user=current_user)

# Delete Note Route
@views.route('/delete-note', methods=['POST'])
@login_required
def delete_note():  
    note = json.loads(request.data)
    note_id = note.get('noteId')
    note = Note.query.get(note_id)
    if note and note.user_id == current_user.id:
        db.session.delete(note)
        db.session.commit()
        return jsonify({}), 204
    return jsonify({'error': 'Note not found or unauthorized'}), 404

# Prediction Route
@views.route('/predict', methods=['GET', 'POST'])
@login_required
def predict():
    if request.method == 'POST':
        try:
            # Gather form data
            age = int(request.form['age'])
            sex = request.form['sex']
            chest_pain_type = request.form['chest_pain_type']
            resting_bp = int(request.form['resting_bp'])
            cholesterol = int(request.form['cholesterol'])
            fasting_bs = request.form['fasting_bs']
            resting_ecg = request.form['resting_ecg']
            max_hr = int(request.form['max_hr'])
            exercise_angina = request.form['exercise_angina']
            oldpeak = float(request.form['oldpeak'])
            st_slope = request.form['st_slope']

            # Dictionary-based mapping for categorical values
            mappings = {
                "fasting_bs": {"Less Than 120 mg/dl": 0, "Greater Than 120 mg/dl": 1},
                "sex": {"Male": 1, "Female": 0},
                "chest_pain_type": {
                    "Typical Angina": [0, 0, 1],  
                    "Atypical Angina": [1, 0, 0],
                    "Non-anginal Pain": [0, 1, 0],
                    "Asymptomatic": [0, 0, 0]
                },
                "resting_ecg": {"Normal": [1, 0], "ST": [0, 1], "LVH": [0, 0]},
                "exercise_angina": {"Yes": 1, "No": 0},
                "st_slope": {"Up": [0, 1], "Flat": [1, 0], "Down": [0, 0]}
            }

            # Create the feature vector
            new_data = [
                age, resting_bp, cholesterol, mappings["fasting_bs"][fasting_bs],
                mappings["sex"][sex], max_hr, oldpeak, mappings["exercise_angina"][exercise_angina],
                *mappings["chest_pain_type"][chest_pain_type], 
                *mappings["resting_ecg"][resting_ecg],
                *mappings["st_slope"][st_slope]
            ]

            # Make prediction
            predicted_value = model.predict([new_data])[0]
            prediction_prob = model.predict_proba([new_data])[0]

            return render_template(
                'prediction.html',
                prediction=predicted_value,
                prediction_probability=prediction_prob,
                user=current_user
            )
        except (ValueError, KeyError) as e:
            flash(f"Error processing input: {e}. Please check your data and try again.", category='error')

    return render_template('prediction.html', user=current_user)

# Manage Users
@views.route('/manage_users')
@login_required
def manage_users():
    users = User.query.all()
    return render_template('manage_users.html', users=users, user=current_user)

@views.route('/delete_user/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    flash('User deleted successfully', category='success')

    # Check if there are any users left after deletion
    users = User.query.all()
    if not users:
        flash('No users found', category='info')

    return redirect(url_for('views.manage_users'))


# Manage Doctors

@views.route('/manage_doctors', methods=['GET', 'POST'])
@login_required
def manage_doctors():
    if request.method == 'POST':
        name = request.form.get('name')
        specialization = request.form.get('specialization')
        contact_number = request.form.get('contact_number')
        email = request.form.get('email')
        password = request.form.get('password', os.urandom(16).hex())  # Generate random password if not provided

        # Convert the form string values to Python time objects
        available_from_str = request.form.get('available_from')
        available_to_str = request.form.get('available_to')

        available_from = datetime.strptime(available_from_str, '%H:%M').time()
        available_to = datetime.strptime(available_to_str, '%H:%M').time()

        if not all([name, specialization, contact_number, email, available_from, available_to]):
            flash('All fields are required', category='error')
        else:
            hashed_password = generate_password_hash(password, method='pbkdf2:sha256')  # Hash the password
            new_doctor = Doctor(
                name=name, 
                specialization=specialization, 
                contact_number=contact_number, 
                email=email, 
                password=hashed_password,  # Store the hashed password
                available_from=available_from,
                available_to=available_to
            )
            db.session.add(new_doctor)
            db.session.commit()
            flash('Doctor added successfully!', category='success')

    doctors = Doctor.query.all()
    return render_template('manage_doctors.html', doctors=doctors, user=current_user)

@views.route('/edit_doctor/<int:doctor_id>', methods=['GET', 'POST'])
def edit_doctor(doctor_id):
    doctor = Doctor.query.get_or_404(doctor_id)
    
    if request.method == 'POST':
        # Get data from the form
        doctor.name = request.form.get('name')
        doctor.specialization = request.form.get('specialization')
        doctor.contact_number = request.form.get('contact_number')
        doctor.email = request.form.get('email')

        # Get available_from and available_to from the form and convert to time object
        available_from_str = request.form.get('available_from')
        available_to_str = request.form.get('available_to')

         # Check if a new password is provided
        new_password = request.form.get('password')
        if new_password:  # If a new password is entered, hash it
            doctor.password = generate_password_hash(new_password, method='pbkdf2:sha256')

        try:
            # Use only hours and minutes (ignore any seconds that may be passed)
            available_from = datetime.strptime(available_from_str[:5], '%H:%M').time()
            available_to = datetime.strptime(available_to_str[:5], '%H:%M').time()
            
            doctor.available_from = available_from
            doctor.available_to = available_to

            # Commit changes to the database
            db.session.commit()
            flash('Doctor updated successfully!', category='success')
            return redirect(url_for('views.manage_doctors'))

        except ValueError as e:
            flash(f"Invalid time format: {e}. Please provide time in HH:MM format.", category='error')
    
    return render_template('edit_doctor.html', doctor=doctor, user=current_user)


@views.route('/delete_doctor/<int:doctor_id>', methods=['POST'])
@login_required
def delete_doctor(doctor_id):
    doctor = Doctor.query.get_or_404(doctor_id)
    db.session.delete(doctor)
    db.session.commit()
    flash('Doctor deleted successfully!', category='success')
    return redirect(url_for('views.manage_doctors'))

# Search and Book Doctor Appointments
@views.route('/doctors', methods=['GET'])
@login_required
def search_doctors():
    search_query = request.args.get('search', '')
    doctors = Doctor.query.filter((Doctor.name.ilike(f'%{search_query}%')) | 
                                  (Doctor.specialization.ilike(f'%{search_query}%'))).all()
    return render_template('doctors.html', doctors=doctors, user=current_user)

@views.route('/book_appointment/<int:doctor_id>', methods=['GET', 'POST'])
@login_required
def book_appointment(doctor_id):
    doctor = Doctor.query.get_or_404(doctor_id)
    
    if request.method == 'POST':
        appointment_date_str = request.form.get('appointment_date')
        
        try:
            # Convert the string to a Python datetime object
            appointment_date = datetime.strptime(appointment_date_str, '%Y-%m-%dT%H:%M')
            
            # Create a new appointment
            new_appointment = Appointment(
                user_id=current_user.id, 
                doctor_id=doctor_id, 
                appointment_date=appointment_date
            )
            
            db.session.add(new_appointment)
            db.session.commit()
            
            # Flash a success message and redirect to the doctor search page
            flash('Appointment booked successfully!', category='success')
            return redirect(url_for('views.search_doctors'))
        
        except ValueError as e:
            flash(f"Invalid date format: {e}. Please use the correct format.", category='error')
    
    return render_template('book_appointment.html', doctor=doctor, user=current_user)
# Feedback management route
@views.route('/manage_feedback')
@login_required
def manage_feedback():
    # Query all notes (feedback)
    notes = Note.query.all()
    return render_template('manage_feedback.html', notes=notes, user=current_user)

# Route to delete feedback
@views.route('/delete_feedback/<int:note_id>', methods=['POST'])
@login_required
def delete_feedback(note_id):
    note = Note.query.get_or_404(note_id)
    db.session.delete(note)
    db.session.commit()
    flash('Feedback deleted successfully', category='success')
    return redirect(url_for('views.manage_feedback'))


@views.route('/doctor_login', methods=['GET', 'POST'])
def doctor_login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        doctor = Doctor.query.filter_by(email=email).first()
        if doctor and check_password_hash(doctor.password, password):  # Verify hashed password
            flash('Login successful', category='success')
            # Logic to log in the doctor and redirect to the dashboard
            return redirect(url_for('views.manage_appointments'))
        else:
            flash('Invalid credentials', category='error')

    return render_template('doctor_login.html', doctor=current_user)


@views.route('/manage_appointments', methods=['GET', 'POST'])
@login_required
def manage_appointments():
    doctor = current_user  # Assuming doctor login handled similarly to User login
    appointments = Appointment.query.filter_by(doctor_id=doctor.id).all()
    return render_template('manage_appointments.html', appointments=appointments,doctor=doctor)

