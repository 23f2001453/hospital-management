from app import app, db
from app import models
from app.models import User, Doctor, Patient, Appointment, Treatment, Department
import getpass
import sys

@app.shell_context_processor
def make_shell_context():
    return {
        'db': db, 
        'User': User, 
        'Doctor': Doctor, 
        'Patient': Patient,
        'Appointment': Appointment, 
        'Treatment': Treatment,
        'create_admin': create_admin  # Add this to shell context too
    }

def create_admin():
    """
    Interactive function to create an admin user.
    Run with: flask shell, then call create_admin()
    Or run with: python hms.py
    """
    print("\n=== Create Admin User ===\n")

    while True:
        username = input("Enter admin username: ").strip()
        if not username:
            print("Username cannot be empty!")
            continue
        
        existing = User.query.filter_by(username=username).first()
        if existing:
            print(f"Username '{username}' already exists!")
            continue
        break
    
    while True:
        email = input("Enter admin email: ").strip()
        if not email:
            print("Email cannot be empty!")
            continue
        
        existing = User.query.filter_by(email=email).first()
        if existing:
            print(f"Email '{email}' already exists!")
            continue
        break

    while True:
        password = getpass.getpass("Enter admin password: ")
        if len(password) < 6:
            print("Password must be at least 6 characters!")
            continue
        
        confirm_password = getpass.getpass("Confirm password: ")
        if password != confirm_password:
            print("Passwords do not match!")
            continue
        break
    
    first_name = input("Enter first name (optional): ").strip() or None
    last_name = input("Enter last name (optional): ").strip() or None
    phone = input("Enter phone number (optional): ").strip() or None
    
    try:
        admin = User(
            username=username,
            email=email,
            role='admin',
            first_name=first_name,
            last_name=last_name,
            phone=phone
        )
        admin.set_password(password)
        
        db.session.add(admin)
        db.session.commit()
        
        print("\nAdmin user created successfully!")
        print(f"Username: {username}")
        print(f"Email: {email}")
        print(f"Role: admin")
        
    except Exception as e:
        db.session.rollback()
        print(f"\nError creating admin: {str(e)}")
        sys.exit(1)


if __name__ == '__main__':
    with app.app_context():
        create_admin()