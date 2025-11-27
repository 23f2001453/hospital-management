# app/models.py
from app import db, login
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from datetime import datetime

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, index=True, nullable=False)
    email = db.Column(db.String(120), unique=True, index=True, nullable=False)
    password_hash = db.Column(db.String(128))
    role = db.Column(db.String(20), nullable=False)  # 'admin','doctor','patient'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    age = db.Column(db.Integer)
    gender = db.Column(db.String(10))

    # common contact/profile fields
    first_name = db.Column(db.String(64))
    last_name = db.Column(db.String(64))
    phone = db.Column(db.String(20))
    address = db.Column(db.Text)
    profile_photo = db.Column(db.String(256), nullable=True)  # path under static/uploads/

    doctor = db.relationship('Doctor', back_populates='user', uselist=False)
    patient = db.relationship('Patient', back_populates='user', uselist=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def full_name(self):
        if self.first_name or self.last_name:
            return f"{(self.first_name or '').strip()} {(self.last_name or '').strip()}".strip()
        return self.username

    def __repr__(self):
        return f"<User {self.username} ({self.role})>"

class Department(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    doctors = db.relationship('Doctor', back_populates='department')

class Doctor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), unique=True, nullable=False)

    specialization = db.Column(db.String(100))
    experience_years = db.Column(db.Integer)
    date_of_joining = db.Column(db.Date)

    # text fallback; prefer availabilities relationship
    availability = db.Column(db.Text)

    department_id = db.Column(db.Integer, db.ForeignKey('department.id'))
    user = db.relationship('User', back_populates='doctor')
    department = db.relationship('Department', back_populates='doctors')

    appointments = db.relationship('Appointment', back_populates='doctor')
    availabilities = db.relationship('DoctorAvailability', back_populates='doctor',
                                     cascade='all, delete-orphan', order_by='DoctorAvailability.date,DoctorAvailability.start_time')

    def __repr__(self):
        return f"<Doctor {self.user.username} ({self.specialization})>"

class DoctorAvailability(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctor.id'), nullable=False, index=True)
    date = db.Column(db.Date, nullable=False, index=True)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    slot_capacity = db.Column(db.Integer, default=1)   # how many patients allowed in this slot
    status = db.Column(db.String(20), default='open')  # open | blocked
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    doctor = db.relationship('Doctor', back_populates='availabilities')
    appointments = db.relationship('Appointment', back_populates='availability', cascade='all, delete-orphan')

    def human_label(self):
        # e.g. "09:00 - 12:00 (2 slots)"
        start = self.start_time.strftime("%H:%M")
        end = self.end_time.strftime("%H:%M")
        return f"{start} - {end}"

    def remaining_slots(self, session):
        # returns slot_capacity - current_bookings
        booked = session.scalar(
            db.select(db.func.count()).select_from(Appointment).where(Appointment.availability_id == self.id)
        )
        if booked is None:
            booked = 0
        return max(0, (self.slot_capacity or 0) - int(booked))

class Patient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), unique=True, nullable=False)

    emergency_contact = db.Column(db.String(50))

    user = db.relationship('User', back_populates='patient')
    appointments = db.relationship('Appointment', back_populates='patient')

    def __repr__(self):
        return f"<Patient {self.user.username}>"

class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctor.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    time = db.Column(db.Time, nullable=False)
    status = db.Column(db.String(20), default="Booked")  # Booked/Completed/Cancelled

    availability_id = db.Column(db.Integer, db.ForeignKey('doctor_availability.id'), nullable=True)

    # relationships
    doctor = db.relationship('Doctor', back_populates='appointments')
    patient = db.relationship('Patient', back_populates='appointments')
    availability = db.relationship('DoctorAvailability', back_populates='appointments')

    treatment = db.relationship('Treatment', back_populates='appointment', 
                                uselist=False, overlaps="treatment_record")

    def __repr__(self):
        return f"<Appt D{self.doctor_id} P{self.patient_id} {self.date} {self.time} {self.status}>"

# Optionally keep Treatment table for detailed records (can keep/update)
class Treatment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointment.id'), unique=True, nullable=False)
    diagnosis = db.Column(db.Text, nullable=True)
    prescription = db.Column(db.Text, nullable=True)
    treatment_notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    appointment = db.relationship('Appointment', back_populates='treatment')

@login.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))
