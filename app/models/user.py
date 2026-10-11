from datetime import datetime
from app import db

class Admin(db.Model):
    """Admin model for administrator accounts."""
    __tablename__ = 'admins'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    last_login = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    elections_created = db.relationship('Election', backref='creator', lazy=True)
    audit_logs = db.relationship('AuditLog', backref='admin', lazy=True)
    
    def set_password(self, password):
        """Hash and set the admin password."""
        import bcrypt
        self.password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    def check_password(self, password):
        """Verify the admin password."""
        import bcrypt
        return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))
    
    def __repr__(self):
        return f'<Admin {self.username}>'


class User(db.Model):
    """User model for voters."""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=True)
    identity_reference = db.Column(db.String(255), unique=True, nullable=False, index=True)
    kyc_status = db.Column(db.String(20), nullable=False, default='PENDING')
    kyc_document_filename = db.Column(db.String(255), nullable=True)
    kyc_submitted_at = db.Column(db.DateTime, nullable=True)
    kyc_verified_at = db.Column(db.DateTime, nullable=True)
    kyc_rejection_reason = db.Column(db.String(500), nullable=True)
    face_image_filename = db.Column(db.String(255), nullable=True)
    face_auth_status = db.Column(db.String(20), nullable=False, default='PENDING')
    face_verified_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())
    
    # Relationships
    voter_eligibilities = db.relationship('VoterEligibility', backref='voter', lazy=True)
    
    def set_password(self, password):
        """Hash and set the voter's password."""
        import bcrypt
        self.password_hash = bcrypt.hashpw(
            password.encode('utf-8'),
            bcrypt.gensalt(),
        ).decode('utf-8')

    def check_password(self, password):
        """Verify the voter's password, returning False for legacy accounts."""
        if not self.password_hash:
            return False
        import bcrypt
        return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))

    def __repr__(self):
        return f'<User {self.name}>'
