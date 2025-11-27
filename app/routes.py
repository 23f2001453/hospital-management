# app/routes.py
import os
from flask import (
    render_template, redirect, url_for, flash, request,
    current_app, send_from_directory
)
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
from app import app, db
import sqlalchemy as sa
from sqlalchemy.orm import joinedload, selectinload
from datetime import datetime, date, timedelta

from app.models import (
    User, Doctor, Patient, Appointment, 
    DoctorAvailability, Treatment, Department
)

# Upload configuration
UPLOAD_FOLDER = os.path.join('uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
ALLOWED_EXT = {"png", "jpg", "jpeg", "gif"}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXT


###############################################
# HOME
###############################################
@app.route('/')
@app.route('/index')
def index():
    return render_template("index.html")


###############################################
# LOGIN
###############################################
@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        # redirect by role
        if current_user.role == "patient":
            return redirect(url_for('patient_dashboard'))
        if current_user.role == "doctor":
            return redirect(url_for('doctor_dashboard'))
        return redirect(url_for('admin_dashboard'))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        user = db.session.scalar(sa.select(User).where(User.username == username))

        if user is None:
            flash("INVALID USERNAME", "danger")
            return render_template("login.html")

        if not user.check_password(password):
            flash("INVALID PASSWORD", "danger")
            return render_template("login.html")

        login_user(user)
        flash("Login successful!", "success")

        # Redirect based on role
        if user.role == "patient":
            return redirect(url_for("patient_dashboard"))
        if user.role == "doctor":
            return redirect(url_for("doctor_dashboard"))
        return redirect(url_for("admin_dashboard"))

    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        # BASIC USER FIELDS
        username = (request.form.get("username") or "").strip()
        email = (request.form.get("email") or "").strip()
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")
        role = request.form.get("role")

        # GENERAL PERSONAL FIELDS (both doctor + patient)
        first_name = request.form.get("first_name", "").strip()
        last_name = request.form.get("last_name", "").strip()
        age = request.form.get("age", "").strip()
        gender = request.form.get("gender", "").strip()
        phone = request.form.get("phone", "").strip()
        address = request.form.get("address", "").strip()

        # PATIENT FIELD
        emergency_contact = request.form.get("emergency_contact", "").strip()

        # DOCTOR FIELDS
        specialization = request.form.get("specialization", "").strip()
        experience = request.form.get("experience", "").strip()
        date_joined = request.form.get("date_joined", "").strip()
        availability = request.form.get("availability", "").strip()

        # Basic validation
        if not username or not email or not password or not role:
            flash("Please fill required fields.", "danger")
            return render_template("register.html")

        if password != confirm_password:
            flash("Passwords do not match.", 'danger')
            return render_template("register.html")

        # Prevent duplicate username/email
        existing_user = db.session.scalar(
            sa.select(User).where(sa.or_(User.username == username, User.email == email))
        )
        if existing_user:
            flash("Username or email already exists.", "danger")
            return render_template("register.html")
        
        profile_picture_path = None 

        if 'profile_photo' in request.files:
            file = request.files['profile_photo']

            if file.filename != '':
                if not allowed_file(file.filename):
                    flash("Invalid file type for profile photo.", "danger")
                    return redirect(url_for('register'))
                
                try:
                    filename = secure_filename(file.filename)
                    save_path = os.path.join(UPLOAD_FOLDER, filename)
                    print("picture is located:")
                    print(filename)

                    if not os.path.exists(UPLOAD_FOLDER):
                        os.makedirs(UPLOAD_FOLDER)
                        
                    file.save(save_path)
                    
                    profile_picture_path = os.path.join(UPLOAD_FOLDER, filename).replace(os.path.sep, '/')

                except Exception as e:
                    flash(f"Error saving file: {e}", "danger")
                    return redirect(url_for('register'))

        try:
            # 1. CREATE USER BASE MODEL
            new_user = User(
                username=username,
                email=email,
                role=role,
                phone=phone,
                age=age,
                gender=gender,
                first_name=first_name,
                last_name=last_name,
                address=address,
                profile_photo=profile_picture_path
            )
            new_user.set_password(password)
            db.session.add(new_user)
            db.session.flush()  # to get new_user.id

            # 2. CREATE ROLE-SPECIFIC PROFILE
            if role == "patient":
                patient_profile = Patient(
                    user_id=new_user.id,
                    emergency_contact=emergency_contact or None
                )
                db.session.add(patient_profile)

            elif role == "doctor":
                # Fetch default department or None
                department = db.session.scalar(
                    sa.select(Department).where(Department.name == "General Practice")
                )
                if date_joined:
                    try:
                        date_joined_obj = datetime.strptime(date_joined, "%Y-%m-%d")
                    except Exception:
                        date_joined_obj = datetime.utcnow()
                else:
                    date_joined_obj = datetime.utcnow()

                doctor_profile = Doctor(
                    user_id=new_user.id,
                    specialization=specialization or None,
                    experience_years=int(experience) if experience.isdigit() else 0,
                    availability=availability or None,
                    date_of_joining=date_joined_obj,
                    department=department
                )
                db.session.add(doctor_profile)
            else:
                # unknown role: rollback and error
                db.session.rollback()
                flash("Invalid role selected.", "danger")
                return render_template("register.html")

            db.session.commit()
            flash(f"{role.capitalize()} account created successfully! Please log in.", "success")
            return redirect(url_for("login"))

        except Exception as e:
            db.session.rollback()
            app.logger.exception("Registration error")
            flash(f"Registration error: {str(e)}", "danger")
            return render_template("register.html")

    return render_template("register.html")



###############################################
# LOGOUT
###############################################
@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Logged out!", "info")
    return redirect(url_for("index"))


###############################################
# ADMIN DASHBOARD & CRUD
###############################################
###############################################
# ADMIN DASHBOARD & CRUD
###############################################
@app.route("/admin/dashboard")
@login_required
def admin_dashboard():
    if current_user.role != "admin":
        return redirect(url_for("login"))

    # Fetch doctors by joining to User
    doctors = db.session.query(Doctor).join(User, Doctor.user_id == User.id).all()
    patients = db.session.query(Patient).join(User, Patient.user_id == User.id).all()

    doctor_count = len(doctors)
    patient_count = len(patients)

    # Fetch upcoming appointments (today and future, excluding cancelled)
    today = date.today()
    upcoming_appointments = db.session.scalars(
        sa.select(Appointment)
        .where(
            Appointment.date >= today,
            Appointment.status != 'Cancelled',
            Appointment.status != 'Completed'
        )
        .order_by(Appointment.date, Appointment.time)
        .limit(20)  # Limit to 20 most recent appointments
    ).all()

    completed_appointments = db.session.scalars(
        sa.select(Appointment)
        .where(
            Appointment.status == 'Completed'
        )
        .order_by(Appointment.date, Appointment.time)
        .limit(20)  # Limit to 20 most recent appointments
    ).all()

    appointment_count = len(upcoming_appointments)
    completed_count = len(completed_appointments)

    return render_template(
        "admin_dashboard.html",
        doctors=doctors,
        patients=patients,
        doctor_count=doctor_count,
        patient_count=patient_count,
        appointments=upcoming_appointments,
        appointment_count=appointment_count,
        completed_appointments=completed_appointments,
        completed_count=completed_count
    )


@app.route("/admin/doctor/add", methods=["GET", "POST"])
@login_required
def admin_add_doctor():
    if current_user.role != "admin":
        return redirect(url_for("index"))

    errors = {}

    if request.method == "POST":
        # Get form data
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        password = request.form.get("password", "").strip()
        confirm_password = request.form.get("confirm_password", "").strip()

        # Validation - Basic fields
        if not username:
            errors["username"] = "Username is required"

        if not email:
            errors["email"] = "Email is required"

        if not phone:
            errors["phone"] = "Phone number is required"

        if not password:
            errors["password"] = "Password is required"
        elif len(password) < 6:
            errors["password"] = "Password must be at least 6 characters"

        if password != confirm_password:
            errors["confirm_password"] = "Passwords do not match"

        # Personal fields
        first_name = request.form.get("first_name", "").strip()
        last_name = request.form.get("last_name", "").strip()
        age = request.form.get("age", "").strip()
        gender = request.form.get("gender", "").strip()
        address = request.form.get("address", "").strip()

        if not first_name:
            errors["first_name"] = "First name is required"

        if not last_name:
            errors["last_name"] = "Last name is required"

        if not age or not age.isdigit():
            errors["age"] = "Valid age is required"
        elif int(age) < 1 or int(age) > 120:
            errors["age"] = "Age must be between 1 and 120"

        if not gender:
            errors["gender"] = "Gender is required"

        if not address or len(address) < 10:
            errors["address"] = "Please provide a valid address"

        # Doctor fields
        specialization = request.form.get("specialization", "").strip()
        experience_years = request.form.get("experience_years", "").strip()
        date_joined = request.form.get("date_joined", "").strip()

        if not specialization:
            errors["specialization"] = "Specialization is required"

        if not experience_years or not experience_years.isdigit():
            errors["experience_years"] = "Valid experience years is required"

        # If there are validation errors, return form with errors
        if errors:
            return render_template("admin_add_doctor.html", errors=errors, form_data=request.form)

        # Check for duplicate username/email
        existing = db.session.scalar(
            sa.select(User).where(
                sa.or_(User.username == username, User.email == email)
            )
        )
        if existing:
            if existing.username == username:
                errors["username"] = "Username already exists"
            if existing.email == email:
                errors["email"] = "Email already exists"
            return render_template("admin_add_doctor.html", errors=errors, form_data=request.form)

        try:
            # Create user account
            user = User(
                username=username,
                email=email,
                phone=phone,
                role="doctor",
                first_name=first_name,
                last_name=last_name,
                address=address
            )
            user.set_password(password)
            db.session.add(user)
            db.session.flush()  # Get user.id

            # Parse date_joined
            if date_joined:
                try:
                    date_joined_obj = datetime.strptime(date_joined, "%Y-%m-%d")
                except Exception:
                    date_joined_obj = datetime.utcnow()
            else:
                date_joined_obj = datetime.utcnow()

            # Fetch default department (optional)
            department = db.session.scalar(
                sa.select(Department).where(Department.name == "General Practice")
            )

            # Create doctor profile
            doctor = Doctor(
                user_id=user.id,
                specialization=specialization,
                experience_years=int(experience_years),
                date_of_joining=date_joined_obj,
                department=department
            )

            db.session.add(doctor)
            db.session.commit()

            flash("Doctor added successfully!", "success")
            return redirect(url_for("admin_dashboard"))

        except Exception as e:
            db.session.rollback()
            app.logger.exception("Error adding doctor")
            flash(f"Error adding doctor: {str(e)}", "danger")
            return render_template("admin_add_doctor.html", errors=errors, form_data=request.form)

    # GET request - show empty form
    return render_template("admin_add_doctor.html", errors=errors, form_data={})


@app.route("/admin/doctor/edit/<int:id>", methods=["GET", "POST"])
@login_required
def admin_edit_doctor(id):
    if current_user.role == "patient":
        return redirect(url_for("index"))

    elif current_user.role == "doctor":
        message="Edit Your Details"
        secondary_message="Update Your Information Below"
    
    else:
        message="Edit Doctor's Details"
        secondary_message="Update the Doctor's information below"

    doctor = db.session.get(Doctor, id)
    if not doctor:
        flash("Doctor not found", "danger")
        return redirect(url_for("admin_dashboard"))
    
    user = doctor.user
    errors = {}

    if request.method == "POST":
        # Get form data
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        password = request.form.get("password", "").strip()
        confirm_password = request.form.get("confirm_password", "").strip()
        
        first_name = request.form.get("first_name", "").strip()
        last_name = request.form.get("last_name", "").strip()
        age = request.form.get("age", "").strip()
        gender = request.form.get("gender", "").strip()
        address = request.form.get("address", "").strip()
        
        # Doctor specific fields
        specialization = request.form.get("specialization", "").strip()
        experience_years = request.form.get("experience_years", "").strip()
        date_joined = request.form.get("date_joined", "").strip()

        # Validation
        if not username:
            errors['username'] = "Username is required"
        elif username != user.username and User.query.filter_by(username=username).first():
            errors['username'] = "Username already exists"
            
        if not email:
            errors['email'] = "Email is required"
        elif email != user.email and User.query.filter_by(email=email).first():
            errors['email'] = "Email already exists"
            
        if password and len(password) < 6:
            errors['password'] = "Password must be at least 6 characters"
            
        if password and password != confirm_password:
            errors['confirm_password'] = "Passwords do not match"
            
        if not phone:
            errors['phone'] = "Phone number is required"
            
        if not first_name:
            errors['first_name'] = "First name is required"
            
        if not last_name:
            errors['last_name'] = "Last name is required"
            
        if not age or not age.isdigit():
            errors['age'] = "Valid age is required"
        elif int(age) < 1 or int(age) > 120:
            errors['age'] = "Age must be between 1 and 120"
            
        if not gender:
            errors['gender'] = "Gender is required"
            
        if not address or len(address) < 10:
            errors['address'] = "Please provide a valid address"
            
        if not specialization:
            errors['specialization'] = "Specialization is required"
            
        if not experience_years or not experience_years.isdigit():
            errors['experience_years'] = "Valid experience years is required"

        profile_picture_path = None 

        if 'profile_photo' in request.files:
            file = request.files['profile_photo']

            if file.filename != '':
                if not allowed_file(file.filename):
                    flash("Invalid file type for profile photo.", "danger")
                    return redirect(url_for('register'))
                
                try:
                    filename = secure_filename(file.filename)
                    save_path = os.path.join(UPLOAD_FOLDER, filename)
                    print("picture is located:")
                    print(filename)
                    
                    if not os.path.exists(UPLOAD_FOLDER):
                        os.makedirs(UPLOAD_FOLDER)
                        
                    file.save(save_path)
                    
                    profile_picture_path = os.path.join(UPLOAD_FOLDER, filename).replace(os.path.sep, '/')

                except Exception as e:
                    flash(f"Error saving file: {e}", "danger")
                    return redirect(url_for('register'))

        # If no errors, update the database
        if not errors:
            try:
                user.username = username
                user.email = email
                user.phone = phone
                user.first_name = first_name
                user.last_name = last_name
                user.address = address
                user.age = age
                user.gender = gender
                user.profile_photo = profile_picture_path
                
                if password:  # Only update password if provided
                    user.set_password(password)
                
                doctor.specialization = specialization
                doctor.experience_years = int(experience_years)
                
                # Update date of joining if provided
                if date_joined:
                    try:
                        doctor.date_of_joining = datetime.strptime(date_joined, "%Y-%m-%d")
                    except Exception:
                        pass  # Keep existing date if invalid format

                db.session.commit()
                flash("Doctor updated successfully!", "success")
                if current_user.role == 'admin':
                    return redirect(url_for("admin_dashboard"))
                else:
                    return redirect(url_for("profile"))
                
            except Exception as e:
                db.session.rollback()
                app.logger.exception("Error updating doctor")
                flash(f"Error updating doctor: {str(e)}", "danger")
                form_data = request.form.to_dict()
                return render_template("admin_edit_doctor.html", doctor=doctor, errors=errors, form_data=form_data, message=message, secondary_message=secondary_message)
        else:
            # Return form with errors and submitted data
            form_data = request.form.to_dict()
            return render_template("admin_edit_doctor.html", doctor=doctor, errors=errors, form_data=form_data, message=message, secondary_message=secondary_message)

    # GET request - populate form with existing data
    form_data = {
        'username': user.username,
        'email': user.email,
        'phone': user.phone,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'age': user.age,
        'gender': user.gender, 
        'address': user.address,
        'specialization': doctor.specialization,
        'experience_years': doctor.experience_years,
        'date_joined': doctor.date_of_joining.strftime("%Y-%m-%d") if doctor.date_of_joining else ''
    }

    return render_template("admin_edit_doctor.html", doctor=doctor, errors=errors, form_data=form_data, message=message, secondary_message=secondary_message)

@app.route("/admin/doctor/delete/<int:id>", methods=["POST", "GET"])
@login_required
def admin_delete_doctor(id):
    if current_user.role != "admin":
        return redirect(url_for("index"))

    doctor = db.session.get(Doctor, id)
    if not doctor:
        flash("Doctor not found", "danger")
        return redirect(url_for("admin_dashboard"))

    user = doctor.user

    # DELETE all appointments linked to this doctor FIRST
    Appointment.query.filter_by(doctor_id=id).delete()

    # Now safe to delete doctor
    db.session.delete(doctor)

    # Delete the linked user account
    if user:
        db.session.delete(user)

    db.session.commit()

    flash("Doctor deleted successfully!", "warning")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/patient/add", methods=["GET", "POST"])
@login_required
def admin_add_patient():
    if current_user.role != "admin":
        return redirect(url_for("index"))

    errors = {}

    if request.method == "POST":
        # Get form data
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        password = request.form.get("password", "").strip()
        confirm_password = request.form.get("confirm_password", "").strip()

        # Validation - Basic fields
        if not username:
            errors["username"] = "Username is required"

        if not email:
            errors["email"] = "Email is required"

        if not phone:
            errors["phone"] = "Phone number is required"

        if not password:
            errors["password"] = "Password is required"
        elif len(password) < 6:
            errors["password"] = "Password must be at least 6 characters"

        if password != confirm_password:
            errors["confirm_password"] = "Passwords do not match"

        # Personal fields
        first_name = request.form.get("first_name", "").strip()
        last_name = request.form.get("last_name", "").strip()
        age = request.form.get("age", "").strip()
        gender = request.form.get("gender", "").strip()
        address = request.form.get("address", "").strip()

        if not first_name:
            errors["first_name"] = "First name is required"

        if not last_name:
            errors["last_name"] = "Last name is required"

        if not age or not age.isdigit():
            errors["age"] = "Valid age is required"
        elif int(age) < 1 or int(age) > 120:
            errors["age"] = "Age must be between 1 and 120"

        if not gender:
            errors["gender"] = "Gender is required"

        if not address or len(address) < 10:
            errors["address"] = "Please provide a valid address"

        emergency_contact = request.form.get("emergency_contact", "").strip()

        if not emergency_contact:
            errors["emergency_contact"] = "Secondary contact is required"

        if emergency_contact == phone:
            errors["emergency_contact"] = "Secondary contact and Primary contact should not be same"

        # If there are validation errors, return form with errors
        if errors:
            return render_template("admin_add_patient.html", errors=errors, form_data=request.form)

        # Check for duplicate username/email
        existing = db.session.scalar(
            sa.select(User).where(
                sa.or_(User.username == username, User.email == email)
            )
        )
        if existing:
            if existing.username == username:
                errors["username"] = "Username already exists"
            if existing.email == email:
                errors["email"] = "Email already exists"
            return render_template("admin_add_patient.html", errors=errors, form_data=request.form)

        try:
            # Create user account
            user = User(
                username=username,
                email=email,
                phone=phone,
                age=age,
                gender=gender,
                role="patient",
                first_name=first_name,
                last_name=last_name,
                address=address
            )
            user.set_password(password)
            db.session.add(user)
            db.session.flush()

            patient = Patient(
                user_id=user.id,
                emergency_contact=emergency_contact,
            )

            db.session.add(patient)
            db.session.commit()

            flash("Patient added successfully!", "success")
            return redirect(url_for("admin_dashboard"))

        except Exception as e:
            db.session.rollback()
            app.logger.exception("Error adding patient")
            flash(f"Error adding patient: {str(e)}", "danger")
            return render_template("admin_add_patient.html", errors=errors, form_data=request.form)

    return render_template("admin_add_patient.html", errors=errors, form_data={})




@app.route("/admin/patient/edit/<int:id>", methods=["GET", "POST"])
@login_required
def admin_edit_patient(id):
    if current_user.role == "doctor":
        return redirect(url_for("index"))
    
    if current_user.role == "admin":
        message="Edit Patient's Details"
        secondary_message="Update the patient information below"

    if current_user.role == "patient":
        message="Edit Your Details"
        secondary_message="Update Your information below"

    patient = db.session.get(Patient, id)

    user = patient.user
    errors = {}

    if request.method == "POST":
        # Get form data
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        password = request.form.get("password", "").strip()
        confirm_password = request.form.get("confirm_password", "").strip()
        
        first_name = request.form.get("first_name", "").strip()
        last_name = request.form.get("last_name", "").strip()
        age = request.form.get("age", "").strip()
        gender = request.form.get("gender", "").strip()
        address = request.form.get("address", "").strip()
        emergency_contact = request.form.get("emergency_contact", "").strip()

        # Validation
        if not username:
            errors['username'] = "Username is required"
        elif username != user.username and User.query.filter_by(username=username).first():
            errors['username'] = "Username already exists"
            
        if not email:
            errors['email'] = "Email is required"
        elif email != user.email and User.query.filter_by(email=email).first():
            errors['email'] = "Email already exists"
            
        if password and len(password) < 6:
            errors['password'] = "Password must be at least 6 characters"
            
        if password and password != confirm_password:
            errors['confirm_password'] = "Passwords do not match"
            
        if not phone:
            errors['phone'] = "Phone number is required"
            
        if not age or not age.isdigit():
            errors['age'] = "Valid age is required"
        elif int(age) < 1 or int(age) > 120:
            errors['age'] = "Age must be between 1 and 120"
            
        if not gender:
            errors['gender'] = "Gender is required"
            
        if not address:
            errors['address'] = "Address is required"
            
        if not emergency_contact:
            errors['emergency_contact'] = "Emergency contact is required"

        profile_picture_path = None 

        if 'profile_photo' in request.files:
            file = request.files['profile_photo']

            if file.filename != '':
                if not allowed_file(file.filename):
                    flash("Invalid file type for profile photo.", "danger")
                    return redirect(url_for('register'))
                
                try:
                    filename = secure_filename(file.filename)
                    save_path = os.path.join(UPLOAD_FOLDER, filename)

                    if not os.path.exists(UPLOAD_FOLDER):
                        os.makedirs(UPLOAD_FOLDER)
                        
                    file.save(save_path)
                    
                    profile_picture_path = os.path.join(UPLOAD_FOLDER, filename).replace(os.path.sep, '/')

                except Exception as e:
                    flash(f"Error saving file: {e}", "danger")
                    return redirect(url_for('register'))

        # If no errors, update the database
        if not errors:
            user.username = username
            user.email = email
            user.phone = phone
            user.first_name = first_name
            user.last_name = last_name
            user.address = address
            user.profile_photo = profile_picture_path
            
            if password:  # Only update password if provided
                user.set_password(password)
            
            user.age = int(age)
            user.gender = gender
            patient.emergency_contact = emergency_contact

            db.session.commit()
            flash("Patient updated successfully!", "success")

            if current_user.role == 'admin':
                return redirect(url_for("admin_dashboard"))
            else:
                return redirect(url_for("profile"))
        else:
            # Return form with errors and submitted data
            form_data = request.form.to_dict()
            return render_template("admin_edit_patient.html", patient=patient, errors=errors, form_data=form_data, message=message, secondary_message=secondary_message)

    # GET request - populate form with existing data
    form_data = {
        'username': user.username,
        'email': user.email,
        'phone': user.phone,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'age': user.age,
        'gender': user.gender,
        'address': user.address,
        'emergency_contact': patient.emergency_contact
    }

    return render_template("admin_edit_patient.html", patient=patient, errors=errors, form_data=form_data, message=message, secondary_message=secondary_message)

@app.route("/admin/patient/delete/<int:id>", methods=["POST", "GET"])
@login_required
def admin_delete_patient(id):
    if current_user.role != "admin":
        return redirect(url_for("index"))

    patient = db.session.get(Patient, id)
    if not patient:
        flash("Patient not found", "danger")
        return redirect(url_for("admin_dashboard"))
    user = patient.user

    db.session.delete(patient)
    if user:
        db.session.delete(user)
    db.session.commit()
    flash("Patient deleted successfully!", "warning")
    return redirect(url_for("admin_dashboard"))


# PATIENT DASHBOARD

@app.route("/patient/dashboard")
@login_required
def patient_dashboard():
    if current_user.role != "patient":
        return redirect(url_for("index"))

    patient = db.session.scalar(sa.select(Patient).where(Patient.user_id == current_user.id))
    if not patient:
        flash("Patient profile missing", "warning")
        return redirect(url_for("index"))

    appointments = db.session.scalars(
        sa.select(Appointment)
        .where(Appointment.patient_id == patient.id)
        .order_by(Appointment.date, Appointment.time)
    ).all()

    doctors = db.session.scalars(
        sa.select(Doctor).join(User, Doctor.user_id == User.id).order_by(User.username)
    ).all()

    return render_template(
        "patient_dashboard.html",
        patient=patient,
        appointments=appointments,
        doctors=doctors
    )


# PATIENT BOOKING (slot-aware)

@app.route("/patient/book", methods=["POST","GET"])
@login_required
def book_appointment():
    if current_user.role != 'patient':
        return redirect(url_for('index'))

    patient = db.session.scalar(sa.select(Patient).where(Patient.user_id == current_user.id))
    if not patient:
        flash("Patient profile missing", "danger")
        return redirect(url_for("index"))

    doctor_id = request.form.get("doctor_id")
    date_str = request.form.get("date")
    time_str = request.form.get("time")  

    availability_id = request.form.get("availability_id")
    if availability_id:
        return redirect(url_for('book_slot', availability_id=int(availability_id)))

    # fallback: manual booking by date/time (simple)
    try:
        d = datetime.strptime(date_str, '%Y-%m-%d').date()
        t = datetime.strptime(time_str, '%H:%M').time()
    except Exception:
        flash("Invalid date/time", "danger")
        return redirect(url_for('patient_dashboard'))

    # conflict check
    existing = db.session.scalar(sa.select(Appointment).where(
        Appointment.doctor_id == doctor_id,
        Appointment.date == d,
        Appointment.time == t
    ))
    if existing:
        flash("A booking already exists at this time.", "danger")
        return redirect(url_for('patient_dashboard'))

    appt = Appointment(
        doctor_id=doctor_id,
        patient_id=patient.id,
        date=d,
        time=t,
        status='Booked'
    )
    db.session.add(appt)
    db.session.commit()
    flash("Appointment booked!", "success")
    return redirect(url_for('patient_dashboard'))


@app.route("/patient/<int:patient_id>", methods=["POST","GET"])
@login_required
def patient_profile(patient_id):
     # Use db.session.get for clean fetching by ID
    p = db.session.get(Patient, patient_id)
    if not p:
        flash("Patient not found", "danger")
        return redirect(url_for('index'))

    # permission check
    if current_user.role == 'patient' and p.user_id != current_user.id:
        flash("Not allowed", "danger")
        return redirect(url_for('index'))

    # fetch patient's appointment history with EAGER LOADING (required for performance)
    # This loads Doctor, Doctor's User, and Treatment data in one efficient query.
    stmt = sa.select(Appointment).where(Appointment.patient_id == p.id).options(
        # Load Doctor and nested User for doctor name
        joinedload(Appointment.doctor).joinedload(Doctor.user),
        # Load Treatment record for diagnosis/prescription/notes
        selectinload(Appointment.treatment)
    ).order_by(Appointment.date.desc(), Appointment.time.desc())

    history = db.session.scalars(stmt).all()

    history_with_treatment = [a for a in history if a.treatment is not None]

    return render_template("patient_profile.html", patient=p, history=history_with_treatment)



###############################################
# DOCTOR helpers & DASHBOARD
###############################################
def get_current_doctor():
    return db.session.scalar(sa.select(Doctor).where(Doctor.user_id == current_user.id))


@app.route('/doctor/dashboard', methods=['GET', 'POST'])
@login_required
def doctor_dashboard():
    if current_user.role != 'doctor':
        flash("Access denied", "warning")
        return redirect(url_for('index'))

    doctor = get_current_doctor()
    if not doctor:
        flash("Doctor profile not set up.", "warning")
        return redirect(url_for('index'))

    # Handle POST requests (status updates)
    if request.method == 'POST':
        appointment_id = request.form.get('appointment_id')
        new_status = request.form.get('status', '').strip()
        
        if appointment_id and new_status:
            appointment = db.session.get(Appointment, int(appointment_id))
            
            if appointment and appointment.doctor_id == doctor.id:
                current_status = appointment.status
                
                # Define allowed transitions
                allowed_transitions = {
                    'Booked': ['Confirmed', 'Cancelled'],
                    'Confirmed': ['Treated', 'Cancelled'],
                    'Treated': ['Completed'],
                    'Completed': [],
                    'Cancelled': []
                }
                
                # Check if transition is valid
                if new_status in allowed_transitions.get(current_status, []):
                    appointment.status = new_status
                    db.session.commit()
                    
                    # Success messages
                    messages = {
                        'Confirmed': 'Appointment confirmed successfully!',
                        'Treated': 'Appointment marked as treated!',
                        'Completed': 'Appointment marked as completed!',
                        'Cancelled': 'Appointment cancelled.'
                    }
                    flash(messages.get(new_status, f'Status updated to {new_status}'), 'success')
                else:
                    flash(f"Cannot change status from {current_status} to {new_status}", "warning")
            else:
                flash("Appointment not found or access denied", "danger")
        
        # Redirect to GET to prevent form resubmission
        return redirect(url_for('doctor_dashboard'))

    # GET request - Display dashboard
    today = date.today()
    seven_days = today + timedelta(days=7)

    # Get upcoming appointments
    upcoming = db.session.scalars(
        sa.select(Appointment).where(
            Appointment.doctor_id == doctor.id,
            Appointment.date >= today,
            Appointment.date <= seven_days
        ).order_by(Appointment.date, Appointment.time)
    ).all()

    # Get distinct patients
    patients = db.session.scalars(
        sa.select(Patient).join(Appointment, Appointment.patient_id == Patient.id)
        .where(Appointment.doctor_id == doctor.id)
        .group_by(Patient.id)
    ).all()

    return render_template('doctor_dashboard.html', doctor=doctor, upcoming=upcoming, patients=patients)

@app.route("/doctor/<int:id>", methods=["POST","GET"])
@login_required
def doctor_profile(id):
    doc = db.session.get(Doctor, id)
    if not doc:
        abort(404)

    avail_list = DoctorAvailability.query.filter_by(doctor_id=id).all()

    for s in avail_list:
        booked = db.session.scalar(
            db.select(db.func.count())
            .select_from(Appointment)
            .where(
                Appointment.availability_id == s.id,
                Appointment.status != "Cancelled"
            )
        )
        s.booked = booked or 0

    return render_template("doctor_profile.html",
                           doctor=doc,
                           availabilities=avail_list)




@app.route('/doctor/appointments')
@login_required
def doctor_appointments():
    if current_user.role != 'doctor':
        return redirect(url_for('index'))

    doctor = get_current_doctor()
    appts = db.session.scalars(
        sa.select(Appointment).where(Appointment.doctor_id == doctor.id).order_by(Appointment.date, Appointment.time)
    ).all()
    return render_template('doctor_appointments.html', appointments=appts, doctor=doctor)


@app.route('/doctor/appointment/<int:appointment_id>/status', methods=['POST'])
@login_required
def doctor_update_appointment_status(appointment_id):
    if current_user.role != 'doctor':
        return redirect(url_for('index'))

    status = request.form.get('status')
    appointment = db.session.get(Appointment, appointment_id)
    doctor = get_current_doctor()
    if appointment is None or appointment.doctor_id != doctor.id:
        flash("Invalid appointment.", "danger")
        return redirect(url_for('doctor_appointments'))

    if status not in ('Booked', 'Completed', 'Cancelled'):
        flash("Invalid status.", "danger")
        return redirect(url_for('doctor_appointments'))

    appointment.status = status
    db.session.commit()
    flash("Appointment status updated.", "success")
    return redirect(url_for('doctor_appointments'))


@app.route('/doctor/patients')
@login_required
def doctor_patients():
    if current_user.role != 'doctor':
        return redirect(url_for('index'))

    doctor = get_current_doctor()
    q = sa.select(Patient).join(Appointment).where(Appointment.doctor_id == doctor.id).group_by(Patient.id)
    patients = db.session.scalars(q).all()
    return render_template('doctor_patients.html', patients=patients, doctor=doctor)


@app.route('/doctor/treat/<int:appointment_id>', methods=['GET', 'POST'])
@login_required
def doctor_treat(appointment_id):
    if current_user.role != 'doctor':
        return redirect(url_for('index'))

    appointment = db.session.get(Appointment, appointment_id)
    doctor = get_current_doctor()
    if appointment is None or appointment.doctor_id != doctor.id:
        flash("Invalid appointment.", "danger")
        return redirect(url_for('doctor_dashboard'))

    if request.method == 'POST':
        diagnosis = request.form.get('diagnosis', '').strip()
        prescription = request.form.get('prescription', '').strip()
        notes = request.form.get('notes', '').strip()

        # create or update treatment (one-to-one)
        if appointment.treatment is None:
            treatment = Treatment(
                appointment_id=appointment.id,
                diagnosis=diagnosis or None,
                prescription=prescription or None,
                treatment_notes=notes or None
            )
            db.session.add(treatment)
        else:
            appointment.treatment.diagnosis = diagnosis or appointment.treatment.diagnosis
            appointment.treatment.prescription = prescription or appointment.treatment.prescription
            appointment.treatment.treatment_notes = notes or appointment.treatment.treatment_notes

        appointment.status = 'Completed'
        db.session.commit()
        flash("Treatment saved.", "success")
        return redirect(url_for('doctor_dashboard'))

    return render_template('doctor_treat.html', appointment=appointment)


@app.route('/doctor/availability', methods=['GET', 'POST'])
@login_required
def doctor_availability():

    if current_user.role != 'doctor':
        flash("Access denied", "warning")
        return redirect(url_for('index'))

    doctor = get_current_doctor()
    if not doctor:
        flash("Doctor profile not set up.", "warning")
        return redirect(url_for('index'))

    if request.method == 'POST':
    
        date_str = request.form.get('date', '').strip()
        start_str = request.form.get('start_time', '').strip()
        end_str = request.form.get('end_time', '').strip()
        capacity_str = request.form.get('max_patients', '').strip()  

        errors = {}
        
        try:
            slot_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except Exception:
            errors['date'] = "Invalid date format"

        try:
            start_time = datetime.strptime(start_str, '%H:%M').time()
        except Exception:
            errors['start_time'] = "Invalid time format"

        try:
            end_time = datetime.strptime(end_str, '%H:%M').time()
        except Exception:
            errors['end_time'] = "Invalid time format"


        if not errors and start_time >= end_time:
            errors['end_time'] = "End time must be after start time"

        slot_datetime = datetime.combine(slot_date, start_time)

        if slot_datetime < datetime.now():
            flash("Cannot book a slot that is in the past.", "danger")
            return redirect(url_for('doctor_availability'))


        try:
            capacity = int(capacity_str) if capacity_str else 1
            if capacity < 1:
                errors['max_patients'] = "Capacity must be at least 1"
        except Exception:
            errors['max_patients'] = "Invalid capacity value"


        if not errors:
            overlap_q = sa.select(DoctorAvailability).where(
                DoctorAvailability.doctor_id == doctor.id,
                DoctorAvailability.date == slot_date,
                sa.or_(

                    sa.and_(DoctorAvailability.start_time <= start_time, DoctorAvailability.end_time > start_time),

                    sa.and_(DoctorAvailability.start_time < end_time, DoctorAvailability.end_time >= end_time),

                    sa.and_(DoctorAvailability.start_time >= start_time, DoctorAvailability.end_time <= end_time),
                )
            )
            overlapping = db.session.scalars(overlap_q).first()
            if overlapping:
                errors['general'] = "This slot overlaps with an existing availability slot"

        if errors:
            flash("Please fix the errors in the form", "danger")

        else:

            new_slot = DoctorAvailability(
                doctor_id=doctor.id,
                date=slot_date,
                start_time=start_time,
                end_time=end_time,
                slot_capacity=capacity,
                status='open'
            )
            db.session.add(new_slot)
            db.session.commit()
            flash("Availability slot added successfully!", "success")
            return redirect(url_for('doctor_availability'))


    today = date.today()
    two_weeks = today + timedelta(days=14)

    avail_q = sa.select(DoctorAvailability).where(
        DoctorAvailability.doctor_id == doctor.id,
        DoctorAvailability.date >= today,
        DoctorAvailability.date <= two_weeks
    ).order_by(DoctorAvailability.date, DoctorAvailability.start_time)

    avail_list = db.session.scalars(avail_q).all()

    availabilities = []
    for slot in avail_list:
        booked_count = db.session.scalar(
            sa.select(sa.func.count()).select_from(Appointment).where(
                Appointment.availability_id == slot.id,
                Appointment.status != 'Cancelled'
            )
        ) or 0
        
        capacity = slot.slot_capacity or 0
        remaining = max(capacity - booked_count, 0)
        is_full = (booked_count >= capacity) if capacity > 0 else False
        
        availabilities.append({
            'id': slot.id,
            'date': slot.date,
            'start_time': slot.start_time,
            'end_time': slot.end_time,
            'slot_capacity': capacity,
            'booked_count': booked_count,
            'remaining': remaining,
            'is_full': is_full,
            'status': slot.status
        })

    return render_template(
        "doctor_availability.html", 
        doctor=doctor, 
        availabilities=availabilities,
        today=today,
        two_weeks=two_weeks,
        errors=errors if request.method == 'POST' else {}
    )


@app.route('/doctor/availability/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def doctor_edit_availability(id):
    """Edit an existing availability slot"""
    if current_user.role != 'doctor':
        flash("Access denied", "warning")
        return redirect(url_for('index'))

    doctor = get_current_doctor()
    if not doctor:
        flash("Doctor profile not set up.", "warning")
        return redirect(url_for('index'))

    slot = db.session.get(DoctorAvailability, id)

    if not slot or slot.doctor_id != doctor.id:
        flash("Slot not found or access denied.", "danger")
        return redirect(url_for('doctor_availability'))

    if request.method == 'POST':
        date_str = request.form.get('date')
        start_time_str = request.form.get('start_time')
        end_time_str = request.form.get('end_time')
        status = request.form.get('status')
        slot_capacity_str = request.form.get('slot_capacity')

        try:
            new_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            new_start_time = datetime.strptime(start_time_str, '%H:%M').time()
            new_end_time = datetime.strptime(end_time_str, '%H:%M').time()
            slot_capacity = int(slot_capacity_str) if slot_capacity_str else 1

            if new_start_time >= new_end_time:
                flash("End time must be after start time.", "danger")
                return render_template("doctor_edit_availability.html", slot=slot)
            
        except Exception:
            flash("Invalid date or time format.", "danger")
            return render_template("doctor_edit_availability.html", slot=slot)

        booked_count = db.session.scalar(
            sa.select(sa.func.count()).select_from(Appointment).where(
                Appointment.availability_id == slot.id,
                Appointment.status.notin_(['Cancelled', 'Completed'])
            )
        ) or 0

        if booked_count > 0:
            current_slot_datetime = datetime.combine(slot.date, slot.start_time)
            new_slot_datetime = datetime.combine(new_date, new_start_time)
            
            if current_slot_datetime != new_slot_datetime:
                flash(f"Cannot change date/time of this slot. {booked_count} active booking(s) exist.", "danger")
                return redirect(url_for('doctor_availability'))

            if slot_capacity < booked_count:
                flash(f"Cannot reduce capacity below the current number of booked appointments ({booked_count}).", "danger")
                return redirect(url_for('doctor_availability'))

        slot.date = new_date
        slot.start_time = new_start_time
        slot.end_time = new_end_time
        slot.status = status
        slot.slot_capacity = slot_capacity
        
        db.session.commit()
        flash("Availability slot updated successfully!", "success")
        return redirect(url_for('doctor_availability'))

    return render_template("doctor_edit_availability.html", slot=slot)


@app.route('/doctor/availability/delete/<int:id>', methods=['POST'])
@login_required
def doctor_delete_availability(id):
    """Delete an availability slot"""
    if current_user.role != 'doctor':
        flash("Access denied", "warning")
        return redirect(url_for('index'))

    doctor = get_current_doctor()
    if not doctor:
        flash("Doctor profile not set up.", "warning")
        return redirect(url_for('index'))

    slot = db.session.get(DoctorAvailability, id)
    if not slot or slot.doctor_id != doctor.id:
        flash("Slot not found", "danger")
        return redirect(url_for('doctor_availability'))

    booked_count = db.session.scalar(
        sa.select(sa.func.count()).select_from(Appointment).where(
            Appointment.availability_id == slot.id,
            Appointment.status.notin_(['Cancelled', 'Completed'])
        )
    ) or 0

    if booked_count > 0:
        flash(f"Cannot delete slot with {booked_count} booked appointment(s). Cancel appointments first.", "danger")
        return redirect(url_for('doctor_availability'))

    db.session.delete(slot)
    db.session.commit()
    flash("Availability slot deleted successfully!", "success")
    return redirect(url_for('doctor_availability'))

@app.route("/book/<int:availability_id>", methods=["POST","GET"])
@login_required
def book_slot(availability_id):
    if current_user.role != 'patient':
        flash("Only patients can book", "danger")
        return redirect(url_for("index"))

    slot = db.session.get(DoctorAvailability, availability_id)
    if not slot or slot.status != 'open':
        flash("Slot not available", "danger")
        return redirect(url_for("patient_dashboard"))

    booked_count = db.session.scalar(
        sa.select(sa.func.count()).select_from(Appointment).where(
            Appointment.availability_id == slot.id,
            Appointment.status != 'Cancelled'
        )
    ) or 0

    cap = slot.slot_capacity or 0
    if cap > 0 and booked_count >= cap:
        flash("Slot is full", "danger")
        return redirect(url_for("patient_dashboard"))

    patient = db.session.scalar(sa.select(Patient).where(Patient.user_id == current_user.id))
    if not patient:
        flash("Create patient profile first", "danger")
        return redirect(url_for("index"))

    existing_booking = db.session.scalar(
        sa.select(Appointment).where(
            Appointment.availability_id == slot.id,
            Appointment.patient_id == patient.id,
            Appointment.status.in_(['Booked', 'Confirmed']) # Check for any active status
        )
    )

    if existing_booking:
        flash("You have already booked an appointment for this specific slot.", "warning")
        return redirect(url_for("patient_dashboard"))

    appt = Appointment(
        patient_id=patient.id,
        doctor_id=slot.doctor_id,
        date=slot.date,
        time=slot.start_time,
        availability_id=slot.id,
        status='Booked'
    )
    db.session.add(appt)
    db.session.commit()
    flash("Booked successfully", "success")
    return redirect(url_for("patient_dashboard"))

@app.route("/patient/cancel_appointment/<int:appointment_id>", methods=["POST"])
@login_required
def patient_cancel_appointment(appointment_id):
    """
    Handles the cancellation of an appointment by a patient.
    """
    appointment = db.session.get(Appointment, appointment_id)

    if not appointment:
        flash("Appointment not found.", "error")
        return redirect(url_for('patient_dashboard'))

    if current_user.patient and appointment.patient_id != current_user.patient.id:

        flash("Unauthorized action.", "error")
        return redirect(url_for('patient_dashboard'))

    if appointment.status == "Booked":
        appointment.status = "Cancelled"
        db.session.commit()
        flash(f"Appointment with Dr. {appointment.doctor.user.last_name} has been successfully cancelled.", "success")
    else:
        flash(f"Cannot cancel appointment with status: {appointment.status}.", "warning")

    return redirect(url_for('patient_dashboard'))


@app.route("/patient/view_treatment/<int:appointment_id>")
@login_required
def patient_view_treatment(appointment_id):
    """
    Handles the request for a patient to view the treatment and prescription 
    details associated with a specific appointment ID.
    """

    appointment = db.session.get(Appointment, appointment_id)

    if not appointment:
        flash("Appointment record not found.", "error")
        return redirect(url_for('patient_dashboard'))

    if not current_user.is_authenticated or \
       not hasattr(current_user, 'patient') or \
       not current_user.patient or \
       appointment.patient_id != current_user.patient.id:
        
        flash("Access denied. You are not authorized to view this record.", "error")
        return redirect(url_for('patient_dashboard'))

    treatment_record = appointment.treatment
    
    if not treatment_record:

        if not (appointment.diagnosis or appointment.prescription or appointment.treatment_notes):
            flash("Treatment details are not yet available for this appointment.", "info")
            return redirect(url_for('patient_dashboard'))

        treatment_record = appointment


    return render_template(
        "patient_view_treatment.html", 
        appointment=appointment,
        treatment=treatment_record
    )

@app.route("/doctor/view_treatment/<int:appointment_id>") 
@login_required
def doctor_view_treatment(appointment_id):
    """
    Handles the request for a patient to view the treatment and prescription 
    details associated with a specific appointment ID.
    """

    appointment = db.session.get(Appointment, appointment_id)

    if not appointment:
        flash("Appointment record not found.", "error")
        return redirect(url_for('doctor_dashboard'))


    if not current_user.is_authenticated or \
       not hasattr(current_user, 'doctor') or \
       appointment.doctor_id != current_user.doctor.id:
        
        flash("Access denied. You are not authorized to view this record.", "error")
        return redirect(url_for('doctor_dashboard'))
    
    treatment_record = appointment.treatment 
    
    if not treatment_record:
        if not (appointment.diagnosis or appointment.prescription or appointment.treatment_notes):
            flash("Treatment details are not yet available for this appointment.", "info")
            return redirect(url_for('doctor_dashboard'))
        # Use appointment's own fields
        treatment_record = appointment

    return render_template(
        "doctor_view_treatment.html", 
        appointment=appointment,
        treatment=treatment_record
    )

@app.route("/profile")
@login_required
def profile():
    return render_template("profile_view.html", user=current_user)


@app.route("/register/patient", methods=["GET", "POST"])
def register_patient():
    form = PatientRegisterForm()
    if form.validate_on_submit():
        # save user
        return redirect(url_for("login"))
    return render_template("patient_form.html", form=form, title="Patient Registration")

@app.route("/register/doctor", methods=["GET", "POST"])
def register_doctor():
    form = DoctorRegisterForm()
    if form.validate_on_submit():
        # save user
        return redirect(url_for("login"))
    return render_template("doctor_form.html", form=form, title="Doctor Registration")
