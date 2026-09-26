import os
import sys
sys.path.insert(0, os.getcwd())

# Direct SQLAlchemy setup with SQLite
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime, timedelta
import bcrypt

Base = declarative_base()

class Admin(Base):
    __tablename__ = 'admins'
    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime)
    
    def set_password(self, password):
        self.password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    phone = Column(String(20), nullable=False)
    identity_reference = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Election(Base):
    __tablename__ = 'elections'
    id = Column(Integer, primary_key=True)
    public_code = Column(String(50), unique=True, nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text)
    status = Column(String(20), default='DRAFT')
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(Integer, ForeignKey('admins.id'))
    candidates = relationship('Candidate', secondary='election_candidates', back_populates='elections')

class Candidate(Base):
    __tablename__ = 'candidates'
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    photo = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)
    elections = relationship('Election', secondary='election_candidates', back_populates='candidates')

class ElectionCandidate(Base):
    __tablename__ = 'election_candidates'
    id = Column(Integer, primary_key=True)
    election_id = Column(Integer, ForeignKey('elections.id'), nullable=False)
    candidate_id = Column(Integer, ForeignKey('candidates.id'), nullable=False)

class Vote(Base):
    __tablename__ = 'votes'
    id = Column(Integer, primary_key=True)
    election_id = Column(Integer, ForeignKey('elections.id'), nullable=False)
    candidate_id = Column(Integer, ForeignKey('candidates.id'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class VoterEligibility(Base):
    __tablename__ = 'voter_eligibility'
    id = Column(Integer, primary_key=True)
    election_id = Column(Integer, ForeignKey('elections.id'), nullable=False)
    voter_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    verified = Column(Boolean, default=False)
    has_voted = Column(Boolean, default=False)
    verified_at = Column(DateTime)
    voted_at = Column(DateTime)

class AuditLog(Base):
    __tablename__ = 'audit_logs'
    id = Column(Integer, primary_key=True)
    admin_id = Column(Integer, ForeignKey('admins.id'))
    action = Column(String(100), nullable=False)
    target_type = Column(String(50))
    target_id = Column(Integer)
    timestamp = Column(DateTime, default=datetime.utcnow)
    ip_hash = Column(String(255))
    details = Column(Text)

# Create SQLite database
import os
basedir = os.path.dirname(os.path.abspath(__file__))
engine = create_engine('sqlite:///' + os.path.join(basedir, 'rohit_voting.db'))
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
session = Session()

print('[OK] Database tables created')

# Create admin
admin = session.query(Admin).filter_by(username='admin').first()
if not admin:
    admin = Admin(username='admin')
    admin.set_password('admin123')
    session.add(admin)
    print('[OK] Default admin created')

# Create candidates
if session.query(Candidate).count() == 0:
    candidates = [
        Candidate(name='Rahul Sharma', description='Computer Science Department - 3rd Year'),
        Candidate(name='Priya Patel', description='Electrical Engineering Department - 2nd Year'),
        Candidate(name='Amit Kumar', description='Mechanical Engineering Department - 4th Year'),
        Candidate(name='Sneha Reddy', description='Civil Engineering Department - 3rd Year'),
        Candidate(name='Vikram Singh', description='Business Administration - 2nd Year'),
    ]
    for candidate in candidates:
        session.add(candidate)
    print('[OK] Sample candidates created')

# Create voters
if session.query(User).count() == 0:
    voters = [
        User(name='Test Voter 1', phone='9000000001', identity_reference='test-identity-0001-hash'),
        User(name='Test Voter 2', phone='9000000002', identity_reference='test-identity-0002-hash'),
        User(name='Test Voter 3', phone='9000000003', identity_reference='test-identity-0003-hash'),
        User(name='Test Voter 4', phone='9000000004', identity_reference='test-identity-0004-hash'),
        User(name='Test Voter 5', phone='9000000005', identity_reference='test-identity-0005-hash'),
    ]
    for voter in voters:
        session.add(voter)
    print('[OK] Sample test voters created')

# Create election
if session.query(Election).count() == 0:
    election = Election(
        public_code='DEMO2024',
        title='Student Council Election 2024',
        description='Vote for your student council representatives for the academic year 2024-25',
        status='DRAFT',
        start_time=datetime.utcnow() + timedelta(days=1),
        end_time=datetime.utcnow() + timedelta(days=30),
        created_by=admin.id
    )
    session.add(election)
    session.flush()
    print('[OK] Sample election created')
    
    candidates = session.query(Candidate).all()
    for candidate in candidates:
        election.candidates.append(candidate)
    print('[OK] Candidates linked to election')
    
    voters = session.query(User).all()
    for voter in voters:
        eligibility = VoterEligibility(
            election_id=election.id,
            voter_id=voter.id,
            verified=True,
            has_voted=False
        )
        session.add(eligibility)
    print('[OK] Voters made eligible for election')

# Create audit log
if session.query(AuditLog).count() == 0:
    audit_log = AuditLog(
        admin_id=admin.id,
        action='SYSTEM_INITIALIZED',
        target_type='SYSTEM',
        target_id=None,
        ip_hash='127.0.0.1',
        details='Database initialized with seed data'
    )
    session.add(audit_log)
    print('[OK] Audit log created')

session.commit()
print('[OK] Database initialization completed successfully!')
print('\nDefault admin credentials:')
print('  Username: admin')
print('  Password: admin123')
print('\nIMPORTANT: Change the default admin password in production!')
