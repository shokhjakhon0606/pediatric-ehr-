import os
from dotenv import load_dotenv
load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key')

    # MySQL connection (works with XAMPP defaults)
    SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://root:@localhost/ehr_db'

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.path.join('static', 'uploads')