from flask import Flask
from config import Config
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
import sqlalchemy as sa
from flask.cli import with_appcontext
import click


app = Flask(__name__)
app.config.from_object(Config)
db = SQLAlchemy(app)
migrate = Migrate(app, db)
login = LoginManager(app)

from app import routes, models

# Put this in app/__init__.py or a separate script run once
@app.cli.command("create-admin")
def create_admin():
    """Create the admin user interactively or from env vars."""
    import getpass, os
    from app.models import User 
    
    username = os.environ.get("ADMIN_USER") or input("Admin username: ")
    password = os.environ.get("ADMIN_PASS") or getpass.getpass("Admin password: ")
    email = os.environ.get("ADMIN_EMAIL") or input("Admin email: ")

    existing = db.session.scalar(sa.select(User).where(User.username == username))
    if existing:
        print("Admin user already exists.")
        return

    admin = User(username=username, email=email, role='admin')
    admin.set_password(password)
    db.session.add(admin)
    db.session.commit()
    print("Admin created.")
