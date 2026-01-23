from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from config import Config

# Initialize extensions
db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = 'main.login'

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Initialize extensions with app
    db.init_app(app)
    login_manager.init_app(app)

    # Import models
    from app.models import Doctor

    # Define user loader inside app context
    @login_manager.user_loader
    def load_user(user_id):
        return Doctor.query.get(int(user_id))

    # Import and register routes
    from app.routes import main
    app.register_blueprint(main)

    return app