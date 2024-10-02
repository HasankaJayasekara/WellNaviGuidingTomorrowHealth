from . import db
from flask_login import UserMixin
from sqlalchemy.sql import func
from datetime import datetime

# Note Model
class Note(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.String(200), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

# User Model
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    first_name = db.Column(db.String(150), nullable=False)

    # One-to-Many relationship: User -> Notes
    notes = db.relationship('Note', backref='user', passive_deletes=True)

    # One-to-Many relationship: User -> Appointments
    appointments = db.relationship('Appointment', backref='user', passive_deletes=True)

# Admin Model
class Admin(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    name = db.Column(db.String(150), nullable=False)
    is_admin = db.Column(db.Boolean, default=True)

    # Admin-specific roles can be added here later if necessary.

# Doctor Model
class Doctor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    specialization = db.Column(db.String(150), nullable=False)
    contact_number = db.Column(db.String(15), nullable=False)
    password = db.Column(db.String(150))
    email = db.Column(db.String(150), unique=True, nullable=False)

    # Doctor availability
    available_from = db.Column(db.Time, nullable=False)
    available_to = db.Column(db.Time, nullable=False)

    # One-to-Many relationship: Doctor -> Appointments
    appointments = db.relationship('Appointment', backref='doctor', passive_deletes=True)

# Appointment Model
class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctor.id', ondelete='CASCADE'), nullable=False)
    appointment_date = db.Column(db.DateTime, nullable=False)

    # Status of the appointment (e.g., 'pending', 'confirmed', 'completed', 'canceled')
    status = db.Column(db.String(20), nullable=False, default='pending')

    # Additional details or purpose of the appointment
    details = db.Column(db.String(500), nullable=True)

    # Track when the appointment was created
    created_at = db.Column(db.DateTime(timezone=True), default=func.now())
