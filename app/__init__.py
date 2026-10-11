from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
from sqlalchemy import inspect, text
import os
from dotenv import load_dotenv

load_dotenv()

db = SQLAlchemy()
csrf = CSRFProtect()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    basedir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'rohit_voting.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {'pool_pre_ping': True, 'pool_recycle': 3600}
    MAX_CONTENT_LENGTH = 4 * 1024 * 1024
    SESSION_COOKIE_SECURE = False
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = 3600
    MAX_LOGIN_ATTEMPTS = 5
    LOGIN_ATTEMPT_WINDOW = 300
    WTF_CSRF_ENABLED = False

class DevelopmentConfig(Config):
    DEBUG = True
    SESSION_COOKIE_SECURE = False

class ProductionConfig(Config):
    DEBUG = False
    SESSION_COOKIE_SECURE = True
    WTF_CSRF_ENABLED = True

config = {'development': DevelopmentConfig, 'production': ProductionConfig, 'default': DevelopmentConfig}

def create_app(config_name='default', test_config=None):
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    if test_config:
        app.config.update(test_config)
    db.init_app(app)
    csrf.init_app(app)
    
    # Import routes so their models are registered with SQLAlchemy before schema creation.
    from app.routes.auth import auth_bp
    from app.routes.admin import admin_bp
    from app.routes.candidate import candidate_bp
    from app.routes.voter import voter_bp
    from app.routes.voting import voting_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(candidate_bp)
    app.register_blueprint(voter_bp)
    app.register_blueprint(voting_bp)
    
    @app.route('/')
    def index():
        return render_template('index.html')
    
    with app.app_context():
        db.create_all()
        _ensure_kyc_columns()
    
    return app


def _ensure_kyc_columns():
    """Add KYC columns for databases created before KYC support was added."""
    inspector = inspect(db.engine)
    migrations = {
        'users': {
            'password_hash': 'VARCHAR(255)',
            'kyc_status': "VARCHAR(20) NOT NULL DEFAULT 'PENDING'",
            'kyc_document_filename': 'VARCHAR(255)',
            'kyc_submitted_at': 'DATETIME',
            'kyc_verified_at': 'DATETIME',
            'kyc_rejection_reason': 'VARCHAR(500)',
            'face_image_filename': 'VARCHAR(255)',
            'face_auth_status': "VARCHAR(20) NOT NULL DEFAULT 'PENDING'",
            'face_verified_at': 'DATETIME',
        },
        'candidates': {
            'phone': 'VARCHAR(20)',
            'identity_reference': 'VARCHAR(255)',
            'kyc_status': "VARCHAR(20) NOT NULL DEFAULT 'PENDING'",
            'kyc_document_filename': 'VARCHAR(255)',
            'kyc_submitted_at': 'DATETIME',
            'kyc_verified_at': 'DATETIME',
            'kyc_rejection_reason': 'VARCHAR(500)',
            'face_image_filename': 'VARCHAR(255)',
            'face_auth_status': "VARCHAR(20) NOT NULL DEFAULT 'PENDING'",
            'face_verified_at': 'DATETIME',
        },
    }
    for table_name, columns in migrations.items():
        existing_columns = {column['name'] for column in inspector.get_columns(table_name)}
        for column_name, column_definition in columns.items():
            if column_name not in existing_columns:
                db.session.execute(text(
                    f'ALTER TABLE {table_name} ADD COLUMN {column_name} {column_definition}'
                ))
    db.session.commit()
